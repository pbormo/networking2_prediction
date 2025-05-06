from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.node import Host, RemoteController, OVSKernelSwitch
import os
import time
import subprocess
import shlex
import random
import threading
import requests
from datetime import datetime
from scapy.all import send, IP, TCP, UDP, ICMP
import logging


def setup_docker_images():
    """
    Prepare Docker images for web servers: httpd (Apache), nginx and caddy.
    Run the Docker pull command for each image.
    """
    # Cleanup existing containers
    for container in ["h5", "h6", "h7"]:
        print(f"[INFO] Removing old container: {container} (if exists)")
        subprocess.run(f"docker rm -f {container}", shell=True, stderr=subprocess.DEVNULL)

    images = ["httpd:alpine", "nginx:alpine", "caddy:alpine"]
    for image in images:
        # Check if the image already exists
        try:
            image_name = shlex.split(image)[0]  # Account for potential arguments in the image name
            print(f"[INFO] Checking if image '{image}' is present locally...")
            result = subprocess.run(
                f"docker images -q {image_name}", 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            if result.stdout.strip():  # If stdout contains something, the image exists
                print(f"[INFO] Image '{image}' already exists locally, skipping pull.")
            else:
                print(f"[INFO] Image '{image}' not found locally, pulling...")
                subprocess.run(f"docker pull {image}", shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to check/pull image '{image}': {e}")


class MyTopo:
    def build(self, net):
        # Add switches
        s1 = net.addSwitch("s1", protocols="OpenFlow13", stp=True)
        s2 = net.addSwitch("s2", protocols="OpenFlow13", stp=True)
        s3 = net.addSwitch("s3", protocols="OpenFlow13", stp=True)
        s4 = net.addSwitch("s4", protocols="OpenFlow13", stp=True)

        # Add regular hosts
        h1 = net.addHost("h1", ip="10.0.0.1")
        h2 = net.addHost("h2", ip="10.0.0.2")
        h3 = net.addHost("h3", ip="10.0.0.3")
        h4 = net.addHost("h4", ip="10.0.0.4")
        
        # Add containerized hosts
        h5 = net.addDockerHost("h5", ip="10.0.0.5", dimage="dev_test", docker_args={"hostname": "h5"})
        h6 = net.addDockerHost("h6", ip="10.0.0.6", dimage="dev_test", docker_args={"hostname": "h6"})
        h7 = net.addDockerHost("h7", ip="10.0.0.7", dimage="dev_test", docker_args={"hostname": "h7"})

        # Add links between hosts and switches
        net.addLink(h1, s1, cls=TCLink, bw=40, delay="15ms")
        net.addLink(h2, s1, cls=TCLink, bw=40, delay="15ms")
        net.addLink(h3, s1, cls=TCLink, bw=40, delay="15ms")
        net.addLink(h4, s2, cls=TCLink, bw=40, delay="15ms")
        net.addLink(h5, s2, cls=TCLink, bw=40, delay="15ms")
        net.addLink(h6, s3, cls=TCLink, bw=40, delay="15ms")
        net.addLink(h7, s4, cls=TCLink, bw=40, delay="15ms")

        # Add links between switches
        net.addLink(s1, s3, cls=TCLink, bw=40, delay="15ms")
        net.addLink(s1, s2, cls=TCLink, bw=40, delay="15ms")
        net.addLink(s2, s3, cls=TCLink, bw=40, delay="15ms")
        net.addLink(s2, s4, cls=TCLink, bw=40, delay="15ms")
        net.addLink(s3, s4, cls=TCLink, bw=40, delay="15ms")
        
        
def start_ryu_controller():
    """
    Start the Ryu controller using ryu-manager.
    """
    try:
        print("[INFO] Starting Ryu controller...")
        process = subprocess.Popen(
            ["ryu-manager", "/usr/lib/python3/dist-packages/ryu/app/simple_switch_stp_13.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("[INFO] Ryu controller started successfully.")
        return process
    except Exception as e:
        print(f"[ERROR] Failed to start Ryu controller: {e}")
        raise

def start_iperf_udp_traffic(source_host, target_host, duration):
    """
    Start iperf to generate UDP traffic between two hosts.
    """
    print(f"[INFO] Starting iperf UDP traffic from {source_host.name} to {target_host.name} for {duration} seconds...")
    try:
        # Start iperf server on the target host
        target_host.cmd(f"iperf -s -u -D")
        # Start iperf client on the source host
        source_host.cmd(f"iperf -c {target_host} -u -t {duration} -b 10M")
        print(f"[INFO] UDP traffic generated successfully from {source_host.name} to {target_host.name}.")
    except Exception as e:
        print(f"[ERROR] Failed to generate UDP traffic: {e}")
    finally:
        # Stop iperf server on the target host
        target_host.cmd("pkill iperf")


def start_tcpdump(net, dump_dir):
    """
    Start tcpdump on all hosts and switches in the network.
    Saves output to .pcap files in the specified directory.
    """
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)  # Create the directory if it does not exist
    
    processes = {}
    container_interfaces = {
        "h5": ["h5-eth0"],
        "h6": ["h6-eth0"],
        "h7": ["h7-eth0"]
        }
    
    for container, interfaces in container_interfaces.items():
        for intf in interfaces:
            h = net.get(container)
            pcap_file = os.path.join(dump_dir, f"{intf}.pcap")
            tcpdump_cmd = f"docker exec {container} tcpdump -e -i {intf} -U -w - | tee {pcap_file} &"
            try:
                print(f"[INFO] Starting tcpdump for {container} on interface {intf}, saving to {pcap_file}...")
                processes[f"{container}-{intf}"] = subprocess.Popen(tcpdump_cmd, shell=True)
            except Exception as e:
                print(f"[ERROR] Failed to start tcpdump on {container} ({intf}): {e}")
    
    # for host in net.hosts:
    #     if host.name not in container_interfaces:
    #         # Generate the dump file path
    #         dump_file = os.path.join(dump_dir, f"{host.name}_traffic.pcap")
    #         # Define network interface for Docker hosts specifically
    #         if "Docker" in str(type(host)):
    #             interface = f"{host.name}-eth0"
    #         else:
    #             interface = host.defaultIntf().name
    #         print(f"[INFO] Using interface {interface} for {host.name}")
            
    #         # Start tcpdump for each host
    #         cmd = f"tcpdump -e -tt -vv -i {interface} -w {dump_file} -U &"
    #         try:
    #             processes[host.name] = host.popen(cmd, shell=True)
    #             print(f"[INFO] Starting tcpdump on {host.name} ({interface}), saving to {dump_file}...\n")
    #         except Exception as e:
    #             print(f"[ERROR] Failed to start tcpdump on {host.name} ({interface}): {e}")
    for host in net.hosts:
        # Skip -eth0 and -lo interfaces
        interfaces = [intf.name for intf in host.intfs.values() if "eth0" not in intf.name and "lo" not in intf.name]
        for interface in interfaces:
            dump_file = os.path.join(dump_dir, f"{host.name}_{interface}.pcap")
            cmd = f"tcpdump -i {interface} -e -tt -vv -U -w {dump_file} &"
            try:
                processes[f"{host.name}-{interface}"] = host.popen(cmd, shell=True)
                print(f"[INFO] Starting tcpdump on {host.name} ({interface}), saving to {dump_file}...")
            except Exception as e:
                print(f"[ERROR] Failed to start tcpdump on {host.name} ({interface}): {e}")
    

    # for switch in net.switches:
    #     for intf in switch.intfs.values():
    #         iface = intf.name
    #         if "eth" in iface:  # Avoid loopback interfaces
    #             pcap_file = os.path.join(dump_dir, f"{iface}.pcap")
    #             cmd = f"tcpdump -i {iface} -e -tt -vv -U -w {pcap_file} &"
    #             try:
    #                 print(f"[INFO] Starting tcpdump on {switch.name} ({iface}), saving to {pcap_file}...")
    #                 processes[f"{iface}"] = switch.popen(cmd, shell=True)
    #             except Exception as e:
    #                 print(f"[ERROR] Failed to start tcpdump on {switch.name} ({iface}): {e}")

    for switch in net.switches:
        for intf in switch.intfs.values():
            iface = intf.name
            if "eth0" not in iface and "lo" not in iface:  # Avoid -eth0 and -lo interfaces
                pcap_file = os.path.join(dump_dir, f"{iface}.pcap")
                cmd = f"tcpdump -i {iface} -e -tt -vv -U -w {pcap_file} &"
                try:
                    processes[f"{iface}"] = switch.popen(cmd, shell=True)
                    print(f"[INFO] Starting tcpdump on {switch.name} ({iface}), saving to {pcap_file}...")
                except Exception as e:
                    print(f"[ERROR] Failed to start tcpdump on {switch.name} ({iface}): {e}")


    return processes


# def start_tcpdump(net, dump_dir):
#     """
#     Start tcpdump on all hosts and switches in the network.
#     Saves output to .pcap files in the specified directory.
#     """
#     if not os.path.exists(dump_dir):
#         os.makedirs(dump_dir)  # Create the directory if it does not exist
    
#     processes = {}
#     container_interfaces = {
#         "h5": ["h5-eth0"],
#         "h6": ["h6-eth0"],
#         "h7": ["h7-eth0"]
#     }
    
#     tcpdump_filter = 'tcp or udp or port 80 or port 443'
    
#     for container, interfaces in container_interfaces.items():
#         for intf in interfaces:
#             h = net.get(container)
#             pcap_file = os.path.join(dump_dir, f"{intf}.pcap")
#             tcpdump_cmd = f"docker exec {container} tcpdump -e -i {intf} -U '{tcpdump_filter}' -w - | tee {pcap_file} &"
#             try:
#                 print(f"[INFO] Starting tcpdump for {container} on interface {intf}, saving to {pcap_file}...")
#                 processes[f"{container}-{intf}"] = subprocess.Popen(tcpdump_cmd, shell=True)
#             except Exception as e:
#                 print(f"[ERROR] Failed to start tcpdump on {container} ({intf}): {e}")
    
#     for host in net.hosts + net.switches:
#         if host.name not in container_interfaces:
#             # Generate the dump file path
#             dump_file = os.path.join(dump_dir, f"{host.name}_traffic.pcap")
#             # Define network interface for Docker hosts specifically
#             if "Docker" in str(type(host)):
#                 interface = f"{host.name}-eth0"
#             else:
#                 interface = host.defaultIntf().name
#             print(f"[INFO] Using interface {interface} for {host.name}")
            
#             # Start tcpdump for each host
#             cmd = f"tcpdump -e -tt -vv -i {interface} -w {dump_file} -U '{tcpdump_filter}' &"
#             try:
#                 processes[host.name] = host.popen(cmd, shell=True)
#                 print(f"[INFO] Starting tcpdump on {host.name} ({interface}), saving to {dump_file}...\n")
#             except Exception as e:
#                 print(f"[ERROR] Failed to start tcpdump on {host.name} ({interface}): {e}")
    
#     return processes

def stop_tcpdump(processes):
    """
    Stop all tcpdump processes and verify pcap files
    """
    print("[INFO] Stopping tcpdump processes...\n")
    for name, process in processes.items():
        try:
            process.terminate()
            process.wait()
            print(f"[INFO] Tcpdump process for {name} terminated.")
        except Exception as e:
            print(f"[ERROR] Failed to terminate tcpdump process for {name}: {e}")


def generate_traffic(source_ips, target_ips, duration):
    start_time = time.time()
    protocols = ['TCP', 'UDP', 'ICMP']
    ports = [80, 443, 8080, 53]  # Common ports

    while time.time() - start_time < duration:
        for protocol in protocols:
            sport = random.choice([1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216, 10240]) 
            dport = random.choice(ports)  # Random destination port
            size = random.randint(64, 1500)  # Random payload size
            payload = "X" * size

            source_ip = random.choice(source_ips)
            target_ip = random.choice(target_ips)

            if protocol == 'TCP':
                pkt = IP(src=source_ip, dst=target_ip)/TCP(sport=sport, dport=dport, flags="S")/payload
                logging.debug(f"Sending TCP packet from {source_ip}:{sport} to {target_ip}:{dport}")
            elif protocol == 'UDP':
                pkt = IP(src=source_ip, dst=target_ip)/UDP(sport=sport, dport=dport)/payload
                logging.debug(f"Sending UDP packet from {source_ip}:{sport} to {target_ip}:{dport}")
            elif protocol == 'ICMP':
                pkt = IP(src=source_ip, dst=target_ip)/ICMP()/payload
                logging.debug(f"Sending ICMP packet from {source_ip} to {target_ip}")

            send(pkt, verbose=False)
            logging.info(f"Packet sent: {pkt.summary()}")
            time.sleep(random.uniform(0.01, 0.2))  # Random sleep between packets

def http_traffic(source_ips, target_urls, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            source_ip = random.choice(source_ips)
            target_url = random.choice(target_urls)
            container_name = random.choice(["nginx_srv", "apache_srv", "caddy_srv"])
            cmd = f"docker exec {container_name} curl -s -o /dev/null -H 'X-Forwarded-For: {source_ip}' http://{target_url}"
            result = subprocess.run(cmd, shell=True)
            logging.debug(f"HTTP GET request to {target_url} from {source_ip} with return code {result.returncode}")
        except Exception as e:
            logging.error(f"HTTP traffic generation error: {e}")
        time.sleep(random.uniform(0.5, 2))  # Random interval between requests

def curl_traffic(source_ips, target_urls, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            source_ip = random.choice(source_ips)
            target_url = random.choice(target_urls)
            result = subprocess.run(f"curl -s -o /dev/null -H 'X-Forwarded-For: {source_ip}' http://{target_url}", shell=True)
            logging.debug(f"Curl request to {target_url} from {source_ip} with return code {result.returncode}")
        except Exception as e:
            logging.error(f"Curl traffic generation error: {e}")
        time.sleep(random.uniform(0.5, 2))  # Random interval between requests

def wget_traffic(source_ips, target_urls, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            source_ip = random.choice(source_ips)
            target_url = random.choice(target_urls)
            result = subprocess.run(f"wget -qO- --header='X-Forwarded-For: {source_ip}' http://{target_url}", shell=True)
            logging.debug(f"Wget request to {target_url} from {source_ip} with return code {result.returncode}")
        except Exception as e:
            logging.error(f"Wget traffic generation error: {e}")
        time.sleep(random.uniform(0.5, 2))  # Random interval between requests

def start_traffic(hosts, web_servers, duration):
    threads = []

    print("[INFO] Generating UDP traffic using iperf for all host pairs...")
    for i in range(len(hosts)):
        for j in range(len(hosts)):
            if i != j:  # Avoid self-traffic
                source_host = hosts[i]
                target_host = hosts[j]
                t = threading.Thread(target=start_iperf_udp_traffic, args=(source_host, target_host, duration))
                threads.append(t)
                
    # Generate random traffic between all hosts
    for i in range(len(hosts)):
        for j in range(len(hosts)):
            if i != j:
                t = threading.Thread(target=generate_traffic, args=([hosts[i]], [hosts[j]], duration))
                threads.append(t)

    # Generate HTTP traffic to web servers
    for host in hosts:
        t = threading.Thread(target=http_traffic, args=([host], web_servers, duration))
        threads.append(t)
        
        # Generate curl traffic to web servers
        t = threading.Thread(target=curl_traffic, args=([host], web_servers, duration))
        threads.append(t)

        # Generate wget traffic to web servers
        t = threading.Thread(target=wget_traffic, args=([host], web_servers, duration))
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    print("Traffic generation completed.")


def start():
    setLogLevel("info")
    logging.basicConfig(level=logging.DEBUG)
    setup_docker_images()
    ryu_process = start_ryu_controller()
    tcpdump_processes = {}

    try:
        time.sleep(5)
        controller = RemoteController("c1", ip="127.0.0.1", port=6633)
        net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink, build=False)
        mgr = VNFManager(net)
        topo = MyTopo()
        topo.build(net)
        net.addController(controller)
        info("[INFO] Starting network...\n")
        net.start()
        info("[INFO] Network started...\n")

        info("[INFO] Adding containers to the network...\n")
        mgr.addContainer("nginx_srv", "h5", "nginx:alpine", "nginx -g 'daemon off;'", docker_args={})
        mgr.addContainer("apache_srv", "h6", "httpd:alpine", "httpd-foreground", docker_args={})
        mgr.addContainer("caddy_srv", "h7", "caddy:alpine", "caddy run --config /etc/caddy/Caddyfile", docker_args={})
        
        time.sleep(25)  # Allow some time for services to start
        
        # Check if containers are available
        containers = {
            "nginx_srv": "10.0.0.5",
            "apache_srv": "10.0.0.6",
            "caddy_srv": "10.0.0.7"
        }
        
        hosts = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5', '10.0.0.6', '10.0.0.7']
        duration = random.randint(30, 90)  # Run for 1 minute
        iterations = 50
        pause_duration = random.randint(30, 60)  # Pause for 1 minutes
        
        for i in range(iterations):
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            dump_dir = f"/home/vagrant/comnetsemu/Networking2_prediction/traffic_records/{current_time}/"
            info("[INFO] Tcpdump started...\n")
            tcpdump_processes = start_tcpdump(net, dump_dir)
            info(f"[INFO] Traffic generation iteration {i+1} started...\n")
            start_traffic(hosts, hosts, duration)
            info(f"[INFO] Traffic generation iteration {i+1} completed. Pausing for {pause_duration / 60} minutes...\n")
            print("[INFO] Stopping tcpdump process...")
            stop_tcpdump(tcpdump_processes)
            time.sleep(pause_duration)
        
        # CLI for user interaction
        # CLI(net)
        
        # Cleanup containers and network
        mgr.removeContainer("nginx_srv")
        mgr.removeContainer("apache_srv")
        mgr.removeContainer("caddy_srv")
        
    finally:
        # Close tcpdump process
        # print("[INFO] Stopping tcpdump process...")
        # stop_tcpdump(tcpdump_processes)
        # Cleanup after test
        print("[INFO] Stopping the network...")
        net.stop()
        print("[INFO] Stopping the manager...")
        mgr.stop()
        os.system("sudo mn -c")

        print("[INFO] Stopping the Ryu controller...")
        if ryu_process:
            ryu_process.terminate()
            stdout, stderr = ryu_process.communicate()
            print("[RYU CONTROLLER OUTPUT]")
            print(stdout)
            print("[RYU CONTROLLER ERROR]")
            print(stderr)

if __name__ == "__main__":
    start()
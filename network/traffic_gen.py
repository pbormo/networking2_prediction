import os
import time
import threading
import random
import subprocess
import logging
from datetime import datetime
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.node import RemoteController, OVSKernelSwitch

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

cmd_lock = threading.Lock()

# --- Port Ranges for ML Consistency ---
TCP_SRC_PORTS = [50020, 50021, 50022]#, 50023, 50024]
TCP_DST_PORTS = [8080, 9001, 9002]
UDP_SRC_PORTS = [50010, 50011, 50012]
UDP_DST_PORTS = [8000, 8001, 8002]

class MyTopo:
    def build(self, net):
        s1 = net.addSwitch("s1", protocols="OpenFlow13")
        s2 = net.addSwitch("s2", protocols="OpenFlow13")
        s3 = net.addSwitch("s3", protocols="OpenFlow13")
        s4 = net.addSwitch("s4", protocols="OpenFlow13")
        hosts = [net.addHost(f"h{i}", ip=f"10.0.0.{i}") for i in range(1, 8)]
        for i in range(2):
            net.addLink(hosts[i], s1, cls=TCLink, bw=40, delay="10ms")
            net.addLink(hosts[i + 2], s2, cls=TCLink, bw=40, delay="10ms")
            net.addLink(hosts[i + 4], s3, cls=TCLink, bw=40, delay="10ms")
        net.addLink(hosts[6], s4, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s1, s2, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s2, s3, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s3, s4, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s4, s1, cls=TCLink, bw=40, delay="10ms")

def start_ryu_controller():
    try:
        logging.info("Starting Ryu controller...")
        process = subprocess.Popen(
            ["ryu-manager", "/usr/lib/python3/dist-packages/ryu/app/simple_switch_stp_13.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logging.info("Ryu controller started successfully.")
        return process
    except Exception as e:
        logging.error(f"Failed to start Ryu controller: {e}")
        raise

def start_tcpdump(net, dump_dir):
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)
    processes = {}
    for host in net.hosts:
        interface = host.defaultIntf().name
        dump_file = os.path.join(dump_dir, f"{host.name}_traffic.pcap")
        cmd = f"tcpdump -i {interface} -w {dump_file} -U &"
        processes[host.name] = host.popen(cmd, shell=True)
    for switch in net.switches:
        for intf in switch.intfList():
            if intf.name != "lo":
                dump_file = os.path.join(dump_dir, f"{switch.name}_{intf.name}_traffic.pcap")
                cmd = f"tcpdump -i {intf.name} -w {dump_file} -U &"
                processes[f"{switch.name}_{intf.name}"] = switch.popen(cmd, shell=True)
    return processes

def stop_tcpdump(processes):
    for name, process in processes.items():
        process.terminate()
        process.wait()

def generate_tcp_traffic(source_host, target_host, payload_size, num_packets, stats):
    packets = 0
    bytes_sent = 0
    for _ in range(num_packets):
        src_port = random.choice(TCP_SRC_PORTS)
        dest_port = random.choice(TCP_DST_PORTS)
        #pkt = random.randint(1, 15)
        cmd = (
            f"dd if=/dev/urandom bs={payload_size} count=1 2>/dev/null | "
            f"socat - TCP:{target_host.IP()}:{dest_port},sourceport={src_port} > /dev/null 2>&1"
        )
        with cmd_lock:
            source_host.cmd(cmd)
        packets += 1
        bytes_sent += payload_size
        time.sleep(random.uniform(0.2, 1))
    stats['tcp'][(source_host.name, target_host.name)] = (packets, bytes_sent)
    logging.info(f"TCP stats: {source_host.name} -> {target_host.name}: {packets} packets, {bytes_sent} bytes")

def generate_udp_traffic(source_host, target_host, payload_size, num_packets, stats):
    packets = 0
    bytes_sent = 0
    for _ in range(num_packets):
        src_port = random.choice(UDP_SRC_PORTS)
        dest_port = random.choice(UDP_DST_PORTS)
        #pkt = random.randint(1, 15)
        cmd = f"hping3 --udp -s {src_port} -p {dest_port} -c 1 -d {payload_size} {target_host.IP()} > /dev/null 2>&1"
        with cmd_lock:
            source_host.cmd(cmd)
        packets += 1
        bytes_sent += payload_size
        time.sleep(random.uniform(0.2, 1))
    stats['udp'][(source_host.name, target_host.name)] = (packets, bytes_sent)
    logging.info(f"UDP traffic: {source_host.name}:{src_port} -> {target_host.name}:{dest_port}")
    logging.info(f"UDP stats: {source_host.name} -> {target_host.name}: {packets} packets, {bytes_sent} bytes")

def generate_http_traffic(source_host, target_host, num_requests, stats):
    packets = 0
    # Use a range of unpredictable source ports for HTTP
    HTTP_SRC_PORTS = [51000, 51001, 51002]#, 51003, 51004]
    for _ in range(num_requests):
        source_port = random.choice(HTTP_SRC_PORTS)
        # Use --local-port to set the source port for curl
        cmd = f"curl --local-port {source_port} -s http://{target_host.IP()}:80 > /dev/null"
        with cmd_lock:
            source_host.cmd(cmd)
        packets += 1
        time.sleep(random.uniform(0.5, 2))
    stats['http'][(source_host.name, target_host.name)] = packets
    logging.info(f"HTTP stats: {source_host.name} -> {target_host.name}: {packets} requests")

def start_web_servers(net):
    web_hosts = ["h5", "h6", "h7"]
    for host_name in web_hosts:
        host = net.get(host_name)
        cmd = "python3 -m http.server 80 &"
        host.cmd(cmd)
        logging.info(f"Started HTTP server on {host_name} (IP: {host.IP()})")

def start_tcp_servers(net):
    for host in net.hosts:
        for port in TCP_DST_PORTS:
            # Start a TCP server in the background that discards all input
            cmd = f"nohup nc -lk -p {port} > /dev/null 2>&1 &"
            host.cmd(cmd)
            logging.info(f"Started TCP server on {host.name}:{port}")

def start_traffic(net, duration):
    hosts = net.hosts
    web_hosts = ["h5", "h6", "h7"]
    start_time = time.time()
    stats = {"tcp": {}, "udp": {}, "http": {}}

    while time.time() - start_time < duration:
        src, dst = random.sample(hosts, 2)
        proto = random.choice(["tcp", "udp", "http"])
        payload_size = random.randint(90, 200)
        num_packets = random.choice([1, 5, 10, 20, 35])
        num_requests = random.choice([1, 3, 5])
        if proto == "tcp":
            generate_tcp_traffic(src, dst, payload_size, num_packets, stats)
        elif proto == "udp":
            generate_udp_traffic(src, dst, payload_size, num_packets, stats)
        elif proto == "http" and dst.name in web_hosts:
            generate_http_traffic(src, dst, num_requests, stats)

        time.sleep(random.uniform(0.05, 0.2))

    logging.info(f"Traffic generation finished. Stats: {stats}")

def repeat_experiment(net, iterations, dump_base_dir):
    for i in range(iterations):
        duration = random.randint(90, 300)  # Generate a new random duration for each iteration
        logging.info(f"Starting iteration {i + 1}/{iterations} (duration: {duration}s)...")
        dump_dir = os.path.join(dump_base_dir, f"iteration_{i + 1}")
        tcpdump_processes = start_tcpdump(net, dump_dir)
        time.sleep(2)
        try:
            logging.info(f"Generating traffic for iteration {i + 1} (duration: {duration}s)...")
            start_traffic(net, duration)
        except Exception as e:
            logging.error(f"Traffic generation failed in iteration {i + 1}: {e}")
        finally:
            stop_tcpdump(tcpdump_processes)
            logging.info(f"Tcpdump processes for iteration {i + 1} stopped.")
        time.sleep(5)
    logging.info("All iterations completed.")

def check_hping3_installed(net):
    for host in net.hosts:
        result = host.cmd("which hping3")
        if not result.strip():
            raise RuntimeError(f"hping3 is not installed on {host.name}. Please install it before proceeding.")
        logging.info(f"hping3 is installed on {host.name}.")

def start():
    setLogLevel("info")
    os.system("sudo mn -c")
    ryu_process = start_ryu_controller()
    controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink)
    topo = MyTopo()
    topo.build(net)
    net.addController(controller)
    time.sleep(5)
    try:
        logging.info("Starting network...")
        net.start()
        logging.info("Network started.")
        time.sleep(5)
        check_hping3_installed(net)
        start_web_servers(net)
        start_tcp_servers(net)  # Start TCP servers on all hosts
        iterations = 40
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dump_base_dir = f"/home/vagrant/comnetsemu/Networking2_prediction/traffic_records/{current_time}/"
        repeat_experiment(net, iterations, dump_base_dir)  
    finally:
        net.stop()
        logging.info("Network stopped and cleaned up.")
        if ryu_process:
            ryu_process.terminate()

if __name__ == "__main__":
    start()
    
    

from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.node import RemoteController, OVSKernelSwitch
from scapy.all import send, IP, TCP, UDP
from datetime import datetime
import os
import time
import threading
import random
import subprocess


class MyTopo:
    def build(self, net):
        # Add switches
        s1 = net.addSwitch("s1", protocols="OpenFlow13")
        s2 = net.addSwitch("s2", protocols="OpenFlow13")
        s3 = net.addSwitch("s3", protocols="OpenFlow13")
        s4 = net.addSwitch("s4", protocols="OpenFlow13")

        # Add 7 hosts
        h1 = net.addHost("h1", ip="10.0.0.1")
        h2 = net.addHost("h2", ip="10.0.0.2")
        h3 = net.addHost("h3", ip="10.0.0.3")
        h4 = net.addHost("h4", ip="10.0.0.4")
        h5 = net.addHost("h5", ip="10.0.0.5")
        h6 = net.addHost("h6", ip="10.0.0.6")
        h7 = net.addHost("h7", ip="10.0.0.7")

        # Add links between hosts and switches
        net.addLink(h1, s1, cls=TCLink, bw=40, delay="10ms")
        net.addLink(h2, s1, cls=TCLink, bw=40, delay="10ms")
        net.addLink(h3, s2, cls=TCLink, bw=40, delay="10ms")
        net.addLink(h4, s2, cls=TCLink, bw=40, delay="10ms")
        net.addLink(h5, s3, cls=TCLink, bw=40, delay="10ms")
        net.addLink(h6, s3, cls=TCLink, bw=40, delay="10ms")
        net.addLink(h7, s4, cls=TCLink, bw=40, delay="10ms")

        # Add links between switches
        net.addLink(s1, s2, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s2, s3, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s3, s4, cls=TCLink, bw=40, delay="10ms")
        net.addLink(s4, s1, cls=TCLink, bw=40, delay="10ms")  # Optional: Create a loop

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

def start_tcpdump(net, dump_dir):
    """
    Start tcpdump on all hosts and switches in the network.
    Saves output to .pcap files in the specified directory.
    """
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)

    processes = {}
    for host in net.hosts:
        interface = host.defaultIntf().name
        dump_file = os.path.join(dump_dir, f"{host.name}_traffic.pcap")
        cmd = f"tcpdump -i {interface} -w {dump_file} -U &"
        processes[host.name] = host.popen(cmd, shell=True)
        
    # Start tcpdump on switches
    for switch in net.switches:
        for intf in switch.intfList():
            if intf.name != "lo":  # Exclude loopback interface
                dump_file = os.path.join(dump_dir, f"{switch.name}_{intf.name}_traffic.pcap")
                cmd = f"tcpdump -i {intf.name} -w {dump_file} -U &"
                processes[f"{switch.name}_{intf.name}"] = switch.popen(cmd, shell=True)

    return processes


def stop_tcpdump(processes):
    """
    Stop all tcpdump processes.
    """
    for name, process in processes.items():
        process.terminate()
        process.wait()


def start_web_servers(net):
    """
    Start simple HTTP servers on some hosts.
    """
    web_hosts = ["h5", "h6", "h7"]
    for host_name in web_hosts:
        host = net.get(host_name)
        cmd = "python3 -m http.server 80 &"
        host.cmd(cmd)
        info(f"[INFO] Started HTTP server on {host_name} (IP: {host.IP()})\n")


cmd_lock = threading.Lock()

def generate_traffic(source_host, target_host, duration, udp_port):
    """
    Generate TCP and UDP traffic between two hosts.
    """
    start_time = time.time()
    while time.time() - start_time < duration:
        # Generate TCP traffic
        pkt = IP(src=source_host.IP(), dst=target_host.IP()) / TCP(dport=80) / "TCP Packet"
        send(pkt, verbose=False)

        # Generate UDP traffic using hping3
        cmd = f"hping3 --udp -c 1 -d 90 -p 53 {target_host.IP()} > /dev/null 2>&1"
        with cmd_lock:
            source_host.cmd(cmd)

        time.sleep(random.uniform(0.1, 0.5))


import threading

# Create a global lock for thread safety
cmd_lock = threading.Lock()

def generate_http_traffic(source_host, target_host, duration):
    """
    Simulate HTTP traffic using curl.
    """
    start_time = time.time()
    while time.time() - start_time < duration:
        cmd = f"curl -s http://{target_host.IP()} > /dev/null"
        with cmd_lock:  # Ensure only one thread executes cmd() at a time
            source_host.cmd(cmd)
        time.sleep(random.uniform(0.5, 2))


def start_traffic(net, duration, udp_port):
    """
    Start traffic generation between all host pairs.
    """
    threads = []
    for i, source_host in enumerate(net.hosts):
        for j, target_host in enumerate(net.hosts):
            if i != j:
                # Generate TCP/UDP traffic
                t = threading.Thread(target=generate_traffic, args=(source_host, target_host, duration, udp_port))
                threads.append(t)
                t.start()

                # Generate HTTP traffic if the target is a web server
                if target_host.name in ["h5", "h6", "h7"]:
                    t_http = threading.Thread(target=generate_http_traffic, args=(source_host, target_host, duration))
                    threads.append(t_http)
                    t_http.start()

    for t in threads:
        t.join()


def repeat_experiment(net, iterations, duration, dump_base_dir, udp_port):
    """
    Repeat the traffic generation and capture process multiple times.
    """
    for i in range(iterations):
        info(f"[INFO] Starting iteration {i + 1}/{iterations}...\n")

        # Create a unique directory for each iteration's captures
        dump_dir = os.path.join(dump_base_dir, f"iteration_{i + 1}")
        tcpdump_processes = start_tcpdump(net, dump_dir)

        # Generate traffic
        info(f"[INFO] Generating traffic for iteration {i + 1}...\n")
        start_traffic(net, duration, udp_port)
        info(f"[INFO] Traffic generation for iteration {i + 1} completed.\n")

        # Stop tcpdump
        stop_tcpdump(tcpdump_processes)
        info(f"[INFO] Tcpdump processes for iteration {i + 1} stopped.\n")

        # Pause between iterations (optional)
        time.sleep(5)  # Adjust pause duration as needed

    info("[INFO] All iterations completed.\n")


def start_udp_listeners(net, port=53):
    """
    Start UDP listeners on all hosts using netcat (nc) and verify they are running.
    """
    for host in net.hosts:
        cmd = f"nohup nc -u -l {port} > /dev/null 2>&1 & echo $!"
        pid = host.cmd(cmd).strip()
        if pid:
            info(f"[INFO] Started UDP listener on {host.name} (IP: {host.IP()}) with PID {pid}\n")
        else:
            info(f"[ERROR] Failed to start UDP listener on {host.name} (IP: {host.IP()})\n")


def stop_udp_listeners(net):
    """
    Stop all UDP listeners started with netcat and verify they are stopped.
    """
    for host in net.hosts:
        host.cmd("pkill -f 'nc -u -l'")
        result = host.cmd("pgrep -f 'nc -u -l'")
        if result.strip():
            info(f"[ERROR] Failed to stop UDP listener on {host.name}.\n")
        else:
            info(f"[INFO] Stopped UDP listener on {host.name}.\n")


def check_hping3_installed(net):
    """
    Check if hping3 is installed on all hosts.
    """
    for host in net.hosts:
        result = host.cmd("which hping3")
        if not result.strip():
            raise RuntimeError(f"[ERROR] hping3 is not installed on {host.name}. Please install it before proceeding.")
        info(f"[INFO] hping3 is installed on {host.name}.\n")


def analyze_pcap_files(dump_dir):
    """
    Analyze .pcap files.
    """
    try:
        for file in os.listdir(dump_dir):
            if file.endswith(".pcap"):
                pcap_path = os.path.join(dump_dir, file)
                info(f"[INFO] Analyzing {pcap_path}...\n")
                cmd = f"tshark -r {pcap_path} -q -z io,phs"
                os.system(cmd)
    except Exception as e:
        info(f"[ERROR] Failed to analyze .pcap files: {e}\n")

def check_port_availability(net, port=53):
    """
    Check if the specified port is available on all hosts.
    If the port is in use, choose another random port and check again.
    """
    for host in net.hosts:
        while True:
            result = host.cmd(f"netstat -an | grep ':{port}'")
            if result.strip():
                info(f"[WARNING] Port {port} is in use on {host.name}. Choosing another port...\n")
                port = random.randint(1024, 65535)
            else:
                info(f"[INFO] Port {port} is available on {host.name}.\n")
                break
    return port


def start():
    setLogLevel("info")
    os.system("sudo mn -c")
    ryu_process = start_ryu_controller()
    controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink)
    topo = MyTopo()
    topo.build(net)
    net.addController(controller)

    try:
        info("[INFO] Starting network...\n")
        net.start()
        info("[INFO] Network started.\n")
        time.sleep(5)

        # Check for hping3
        check_hping3_installed(net)

        # Start web servers
        start_web_servers(net)

        # Check port availability
        udp_port = random.randint(1024, 65535)
        check_port_availability(net, port=udp_port)

        # Start UDP listeners
        start_udp_listeners(net, port=udp_port)

        # Repeat the experiment
        iterations = 20  # Number of repetitions
        # duration = 60  # Traffic generation duration per iteration (in seconds)
        duration = random.randint(30, 90)  # Traffic generation duration per iteration (random between 30 and 90 seconds)
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dump_base_dir = f"/home/vagrant/comnetsemu/Networking2_prediction/traffic_records/{current_time}/"
        repeat_experiment(net, iterations, duration, dump_base_dir, udp_port)

    finally:
        # Stop UDP listeners
        stop_udp_listeners(net)
        # Stop the network
        net.stop()
        info("[INFO] Network stopped and cleaned up.\n")
        # Stop the Ryu controller
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
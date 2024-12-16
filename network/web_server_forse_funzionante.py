from comnetsemu.net import Containernet, VNFManager
from comnetsemu.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.node import Host, RemoteController, OVSKernelSwitch
import os
import time
import subprocess

def setup_webserver_image():
    """
    Prepare Docker images for web servers.
    """
    os.system("docker pull httpd:alpine")  # Apache
    os.system("docker pull nginx:alpine")  # Nginx
    os.system("docker pull caddy:alpine")  # Caddy

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
    

def start():
    setLogLevel("INFO")
    setup_webserver_image()
    # Start the Ryu controller
    ryu_process = start_ryu_controller()

    try:
        # Set up remote controller
        controller = RemoteController("c1", ip="*********", port=6633)

        # Initialize the network
        net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink, build=False)
        mgr = VNFManager(net)
        # Set up the topology
        topo = MyTopo()
        topo.build(net)

        # Add controller to the network
        net.addController(controller)
        # Start the network
        info("[INFO] Starting network...\n")
        net.start()
        info("[INFO] Network started...\n")

        
        # Dynamically add containers with specific configurations
        mgr.addContainer("nginx_srv", "h5", "nginx:alpine", "nginx -g 'daemon off;'", docker_args={})
        mgr.addContainer("apache_srv", "h6", "httpd:alpine", "httpd-foreground", docker_args={})
        mgr.addContainer("caddy_srv", "h7", "caddy:alpine", "caddy run --config /etc/caddy/Caddyfile", docker_args={})
        
        # Allow some time for services to start
        time.sleep(60)
        
        # Verify web servers from h1
        h1 = net.get("h1")
        info(h1.cmd("curl http://10.0.0.5"))  # Test Nginx at h5
        info(h1.cmd("curl http://10.0.0.6"))  # Test apache at h6
        info(h1.cmd("curl http://10.0.0.7"))  # Test caddy at h7

        # CLI for user interaction
        CLI(net)
        
        # Cleanup containers and network
        mgr.removeContainer("nginx_srv")
        mgr.removeContainer("apache_srv")
        mgr.removeContainer("caddy_srv")
        
        
    finally:
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
    
    
    # controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    
    # # Create Containernet instance
    # net = Containernet(controller=controller, switch=OVSKernelSwitch, link=TCLink, build=False)
    # mgr = VNFManager(net)
    # topo = MyTopo()
    # topo.build(net)
    # net.addController(controller)
    
    # # Start the network
    # info("Starting network...\n")
    # net.start()
    # info("Network started...\n")

    # # Dynamically add containers with specific configurations
    # mgr.addContainer("nginx_srv", "h5", "nginx:alpine", "nginx -g 'daemon off;'", docker_args={})
    # mgr.addContainer("apache_srv", "h6", "httpd:alpine", "httpd-foreground", docker_args={})
    # mgr.addContainer("caddy_srv", "h7", "caddy:alpine", "caddy run --config /etc/caddy/Caddyfile", docker_args={})
    
    # # Allow some time for services to start
    # time.sleep(60)
    
    # # Verify web servers from h1
    # h1 = net.get("h1")
    # info(h1.cmd("curl http://10.0.0.5"))  # Test Nginx at h5
    # info(h1.cmd("curl http://10.0.0.6"))  # Test apache at h6
    # info(h1.cmd("curl http://10.0.0.7"))  # Test caddy at h7

    # # CLI for user interaction
    # CLI(net)
    
    # # Cleanup containers and network
    # mgr.removeContainer("nginx_srv")
    # mgr.removeContainer("apache_srv")
    # mgr.removeContainer("caddy_srv")
    # net.stop()
    # mgr.stop()
    # os.system("sudo mn -c")

if __name__ == "__main__":
    start()

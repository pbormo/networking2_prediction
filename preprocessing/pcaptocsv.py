import pyshark
import csv
import os
import sys
from collections import defaultdict

def analyze_pcap_folder(input_folder, output_folder, window_size=1):
    os.makedirs(output_folder, exist_ok=True)
    
    # Scan the input folder, including subfolders
    for root, _, files in os.walk(input_folder):
        # Get the relative path of the subfolder
        folder_id = os.path.relpath(root, input_folder).replace(os.sep, "-")
        
        # If the subfolder is the main folder, ignore the "empty" part
        if folder_id == ".":
            folder_id = "root"  # Use "root" if it's the main folder
        
        print(f"\nExploring folder: {root}")
        
        for filename in files:
            if filename.endswith('.pcap'):
                input_file = os.path.join(root, filename)
                
                # Create the output filename reflecting the subfolder structure
                output_file = os.path.join(output_folder, f"{folder_id}_{os.path.splitext(filename)[0]}_features.csv")
                
                print(f"Analyzing file: {input_file}")
                
                # Check if the file actually exists
                if not os.path.exists(input_file):
                    print(f"Error: file {input_file} does not exist.")
                    continue

                analyze_pcap(input_file, output_file, window_size)

def analyze_pcap(pcap_file, output_csv, window_size=1):
    try:
        print(f"Opening pcap file: {pcap_file}")
        capture = pyshark.FileCapture(pcap_file)
        print(f"Pcap file opened successfully: {pcap_file}")
    except Exception as e:
        print(f"Error opening file {pcap_file}: {e}")
        return

    data = []
    byte_count = 0
    packet_count = 0
    packet_sizes = []
    timestamps = []
    protocol_counts = defaultdict(int)
    current_window = None
    last_timestamp = None
    delay_list = []

    for packet in capture:
        try:
            timestamp = float(packet.sniff_timestamp)
            length = int(packet.length)
            protocol = packet.highest_layer
            src_ip = packet.ip.src if hasattr(packet, 'ip') else None
            dst_ip = packet.ip.dst if hasattr(packet, 'ip') else None
            src_mac = packet.eth.src if hasattr(packet, 'eth') else None
            dst_mac = packet.eth.dst if hasattr(packet, 'eth') else None
            ingress_port = packet.openflow.in_port if hasattr(packet, 'openflow') and hasattr(packet.openflow, 'in_port') else None
            egress_port = packet.openflow.out_port if hasattr(packet, 'openflow') and hasattr(packet.openflow, 'out_port') else None
            
            # Check if packet is UDP
            src_port = None
            dst_port = None
            if hasattr(packet, 'udp'):
                src_port = packet.udp.srcport
                dst_port = packet.udp.dstport
                protocol = 'UDP'
                # print(f"UDP Packet found: {src_ip}:{src_port} -> {dst_ip}:{dst_port}")  # Additional debug log
            elif hasattr(packet, 'tcp'):
                src_port = packet.tcp.srcport
                dst_port = packet.tcp.dstport

            delay = (timestamp - last_timestamp) if last_timestamp is not None else 0
            last_timestamp = timestamp

            if current_window is None:
                current_window = int(timestamp)

            if int(timestamp) == current_window:
                byte_count += length
                packet_count += 1
                packet_sizes.append(length)
                timestamps.append(timestamp)
                protocol_counts[protocol] += 1
                delay_list.append(delay)
            else:
                # Compute and store window metrics
                throughput = byte_count / window_size
                avg_packet_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0
                jitter = calculate_jitter(timestamps)
                protocol_distribution = {k: v / packet_count for k, v in protocol_counts.items()}

                data.append([current_window, throughput, jitter, avg_packet_size, packet_count, protocol_distribution, delay_list[-1],
                             src_ip, dst_ip, src_mac, dst_mac, ingress_port, egress_port, src_port, dst_port, protocol])

                # Reset variables for the next window
                byte_count = length
                packet_count = 1
                packet_sizes = [length]
                timestamps = [timestamp]
                protocol_counts = defaultdict(int)
                protocol_counts[protocol] += 1
                delay_list = [delay]
                current_window = int(timestamp)

        except AttributeError:
            print(f"Packet skipped due to missing or corrupted data in file {pcap_file}.")
            continue
        except Exception as e:
            print(f"Error analyzing a packet in {pcap_file}: {e}")
            continue

    # Process any remaining data after the loop
    if packet_count > 0:
        throughput = byte_count / window_size
        avg_packet_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0
        jitter = calculate_jitter(timestamps)
        protocol_distribution = {k: v / packet_count for k, v in protocol_counts.items()}
        data.append([current_window, throughput, jitter, avg_packet_size, packet_count, protocol_distribution, delay_list[-1],
                     src_ip, dst_ip, src_mac, dst_mac, ingress_port, egress_port, src_port, dst_port, protocol])
    capture.close()
    save_to_csv(data, output_csv)

def calculate_jitter(timestamps):
    if len(timestamps) < 2:
        return 0
    diffs = [abs(timestamps[i] - timestamps[i - 1]) for i in range(1, len(timestamps))]
    return sum(diffs) / len(diffs)

def save_to_csv(data, output_csv):
    columns = ['Timestamp', 'Throughput (Bps)', 'Jitter (s)', 'Avg Packet Size (bytes)', 'Packet Count', 'Protocol Distribution',
               'Delay (s)', 'Source IP', 'Destination IP', 'Source MAC', 'Destination MAC', 'Ingress Port', 'Egress Port',
               'Source Port', 'Destination Port', 'Protocol']
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        for row in data:
            row[5] = str(row[5])  # Convert protocol distribution dictionary to string
            writer.writerow(row)
    print(f"Data saved to '{output_csv}'")

if __name__ == "__main__":
    # Get the directory where this script is located
    # Run the function on the provided dataset
    current_dir = os.path.dirname(__file__)

    input_base = os.path.join(current_dir, '..', 'traffic_records')
    output_folder = os.path.join(current_dir, '..', 'prediction')
    
    if len(sys.argv) > 1:
        subfolder = sys.argv[1]
        input_folder = os.path.join(input_base, subfolder)
        if not os.path.exists(input_folder):
            print(f"Specified folder '{input_folder}' does not exist. Exiting.")
            sys.exit(1)
        print(f"Processing only folder: {input_folder}")
    else:
        input_folder = input_base
        print(f"Processing all folders in: {input_folder}")
    
    analyze_pcap_folder(input_folder, output_folder)

import pyshark
import csv
import os
from collections import defaultdict

def analyze_pcap_folder(input_folder, output_folder, window_size=1):
    os.makedirs(output_folder, exist_ok=True)
    
    # Scandisci la cartella di input, comprese le sottocartelle
    for root, _, files in os.walk(input_folder):
        # Ottieni il percorso relativo della sottocartella
        folder_id = os.path.relpath(root, input_folder).replace(os.sep, "-")
        
        # Se la sottocartella è la cartella principale, ignora la parte "vuota"
        if folder_id == ".":
            folder_id = "root"  # Usa un nome "root" se la cartella principale è quella vuota
        
        print(f"\nEsplorando la cartella: {root}")
        
        for filename in files:
            if filename.endswith('.pcap'):
                input_file = os.path.join(root, filename)
                
                # Crea il nome del file di output con la struttura della sottocartella
                output_file = os.path.join(output_folder, f"{folder_id}_{os.path.splitext(filename)[0]}_features.csv")
                
                print(f"Analizzando il file: {input_file}")
                
                # Controlla se il file esiste effettivamente
                if not os.path.exists(input_file):
                    print(f"Errore: il file {input_file} non esiste.")
                    continue

                analyze_pcap(input_file, output_file, window_size)

def analyze_pcap(pcap_file, output_csv, window_size=1):
    try:
        print(f"Apertura del file pcap: {pcap_file}")
        capture = pyshark.FileCapture(pcap_file)
        print(f"File pcap aperto con successo: {pcap_file}")
    except Exception as e:
        print(f"Errore nell'aprire il file {pcap_file}: {e}")
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
            
            # Estrazione Source e Destination Port
            src_port = None
            dst_port = None
            if hasattr(packet, 'tcp'):
                src_port = packet.tcp.srcport
                dst_port = packet.tcp.dstport
            elif hasattr(packet, 'udp'):
                src_port = packet.udp.srcport
                dst_port = packet.udp.dstport
            
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
                throughput = byte_count / window_size
                avg_packet_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0
                jitter = calculate_jitter(timestamps)
                protocol_distribution = {k: v / packet_count for k, v in protocol_counts.items()}
                
                data.append([current_window, throughput, jitter, avg_packet_size, packet_count, protocol_distribution, delay_list[-1],
                             src_ip, dst_ip, src_mac, dst_mac, ingress_port, egress_port, src_port, dst_port, protocol])
                
                byte_count = length
                packet_count = 1
                packet_sizes = [length]
                timestamps = [timestamp]
                protocol_counts = defaultdict(int)
                protocol_counts[protocol] += 1
                delay_list = [delay]
                current_window = int(timestamp)
        
        except AttributeError:
            print(f"Pacchetto ignorato per dati mancanti o corrotti nel file {pcap_file}.")
            continue
        except Exception as e:
            print(f"Errore nell'analisi di un pacchetto in {pcap_file}: {e}")
            continue
    
    if packet_count > 0:
        throughput = byte_count / window_size
        avg_packet_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0
        jitter = calculate_jitter(timestamps)
        protocol_distribution = {k: v / packet_count for k, v in protocol_counts.items()}
        data.append([current_window, throughput, jitter, avg_packet_size, packet_count, protocol_distribution, delay_list[-1],
                     src_ip, dst_ip, src_mac, dst_mac, ingress_port, egress_port, src_port, dst_port, protocol])
    
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
            row[5] = str(row[5])  # Convertiamo il dizionario della distribuzione dei protocolli in stringa
            writer.writerow(row)
    print(f"Dati salvati in '{output_csv}'")

# Esempio di utilizzo
input_folder = r"C:\Users\ACER\Documents\netmod2\ultimi_test_fatti"
output_folder = r"C:\Users\ACER\Documents\netmod2\ultimi_test_fatti_csv"
analyze_pcap_folder(input_folder, output_folder)
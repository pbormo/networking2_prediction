import pyshark
import csv
import os
from collections import defaultdict

def analyze_pcap_folder(input_folder, output_folder, window_size=1):
    """
    Analizza tutti i file PCAP in una cartella e salva i risultati in file CSV distinti.

    Args:
        input_folder (str): Percorso della cartella contenente i file PCAP.
        output_folder (str): Percorso della cartella dove salvare i file CSV.
        window_size (int): Dimensione della finestra temporale in secondi per calcolare metriche aggregate.
    """
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.endswith('.pcap'):
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_features.csv")
            print(f"Analizzando: {input_file}")
            analyze_pcap(input_file, output_file, window_size)

def analyze_pcap(pcap_file, output_csv, window_size=1):
    """
    Analizza un file PCAP per estrarre feature utili all'addestramento di un modello LSTM.

    Args:
        pcap_file (str): Percorso del file PCAP.
        output_csv (str): Percorso del file CSV di output.
        window_size (int): Dimensione della finestra temporale in secondi per calcolare metriche aggregate.
    """
    capture = pyshark.FileCapture(pcap_file)
    data = []
    byte_count = 0
    packet_count = 0
    packet_sizes = []
    timestamps = []
    protocol_counts = defaultdict(int)
    current_window = None
    last_timestamp = None  # Variabile per memorizzare il timestamp del pacchetto precedente
    delay_list = []  # Lista per memorizzare i delay tra pacchetti

    for packet in capture:
        try:
            timestamp = float(packet.sniff_timestamp)  # Tempo in secondi
            length = int(packet.length)  # Dimensione del pacchetto in byte
            protocol = packet.highest_layer  # Protocollo (es. TCP, UDP)
            src_ip = packet.ip.src if hasattr(packet, 'ip') else None
            dst_ip = packet.ip.dst if hasattr(packet, 'ip') else None

            # Calcolare il delay tra pacchetti successivi (solo se il pacchetto precedente esiste)
            if last_timestamp is not None:
                delay = timestamp - last_timestamp
            else:
                delay = 0  # Impostare il primo pacchetto a delay 0

            last_timestamp = timestamp  # Aggiorna il timestamp dell'ultimo pacchetto

            # Inizializza la finestra temporale
            if current_window is None:
                current_window = int(timestamp)

            if int(timestamp) == current_window:
                byte_count += length
                packet_count += 1
                packet_sizes.append(length)
                timestamps.append(timestamp)
                protocol_counts[protocol] += 1
                delay_list.append(delay)  # Aggiungi il delay alla lista
            else:
                throughput = byte_count / window_size  # Bps
                avg_packet_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0
                jitter = calculate_jitter(timestamps)
                protocol_distribution = {
                    k: v / packet_count for k, v in protocol_counts.items()
                }

                data.append([current_window, throughput, jitter, avg_packet_size, packet_count, protocol_distribution, delay_list[-1], src_ip, dst_ip])

                byte_count = length
                packet_count = 1
                packet_sizes = [length]
                timestamps = [timestamp]
                protocol_counts = defaultdict(int)
                protocol_counts[protocol] += 1
                delay_list = [delay]  # Reset del delay per la nuova finestra temporale
                current_window = int(timestamp)

        except AttributeError:
            continue

    # Salva l'ultima finestra
    if packet_count > 0:
        throughput = byte_count / window_size
        avg_packet_size = sum(packet_sizes) / len(packet_sizes) if packet_sizes else 0
        jitter = calculate_jitter(timestamps)
        protocol_distribution = {k: v / packet_count for k, v in protocol_counts.items()}
        data.append([current_window, throughput, jitter, avg_packet_size, packet_count, protocol_distribution, delay_list[-1], src_ip, dst_ip])

    # Salva i dati in un file CSV
    save_to_csv(data, output_csv)

def calculate_jitter(timestamps):
    if len(timestamps) < 2:
        return 0
    diffs = [abs(timestamps[i] - timestamps[i - 1]) for i in range(1, len(timestamps))]
    return sum(diffs) / len(diffs)

def save_to_csv(data, output_csv):
    columns = [
        'Timestamp', 'Throughput (Bps)', 'Jitter (s)', 'Avg Packet Size (bytes)',
        'Packet Count', 'Protocol Distribution', 'Delay (s)', 'Source IP', 'Destination IP'
    ]
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        for row in data:
            row[5] = str(row[5])  # Protocol Distribution (dictionary to string)
            writer.writerow(row)
    print(f"Dati salvati in '{output_csv}'")

# Esempio di utilizzo
input_folder = r"C:\Users\ACER\Documents\netmod2\pcapfinali\traffic_records"
output_folder = r"C:\Users\ACER\Documents\netmod2\daanalizzarefinali"
analyze_pcap_folder(input_folder, output_folder)
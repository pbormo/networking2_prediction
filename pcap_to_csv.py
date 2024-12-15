import pyshark
import csv

# Funzione per analizzare i pcap e raccogliere le informazioni
def analyze_pcap(pcap_file):
    capture = pyshark.FileCapture(pcap_file)
    data = []

    # Itera sui pacchetti
    for packet in capture:
        # Aggiungi qui la logica per estrarre le informazioni che ti servono.
        # Ad esempio, puoi raccogliere informazioni come il tempo di arrivo del pacchetto (timestamp),
        # il tipo di protocollo, la dimensione del pacchetto, ecc.
        
        try:
            timestamp = packet.sniff_time.timestamp()  # Tempo del pacchetto
            length = packet.length  # Lunghezza del pacchetto
            protocol = packet.highest_layer  # Protocollo (es. TCP, UDP)
            
            # Aggiungi altre informazioni che ti interessano (es. throughput, jitter, etc.)
            data.append([timestamp, length, protocol])
        
        except AttributeError:
            continue  # Se il pacchetto non ha i campi che stai cercando, ignoralelo

    # Salva i dati in un file CSV
    save_to_csv(data)

# Funzione per salvare i dati in un CSV
def save_to_csv(data):
    # Definisci i nomi delle colonne (puoi modificarli a seconda delle tue necessità)
    columns = ['Timestamp', 'Length', 'Protocol']

    # Crea e scrivi nel file CSV
    with open(r"C:\Users\ACER\Documents\netmod2\output_pcap_data_h2.csv", mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)  # Scrivi l'intestazione
        writer.writerows(data)  # Scrivi i dati

    print("Dati salvati in 'output_pcap_data_h2.csv'")

# Percorso del file pcap
pcap_file = r"C:\Users\ACER\Documents\netmod2\pcapfile\h2.pcap"

# Esegui l'analisi
analyze_pcap(pcap_file)
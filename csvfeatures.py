import pandas as pd

# Carica il CSV che hai ottenuto
df = pd.read_csv(r"C:\Users\ACER\Documents\netmod2\output_pcap_data_h2.csv")  # Sostituisci 'data.csv' con il nome del tuo file CSV

# Assicurati che il campo 'time' sia in formato datetime
df['time'] = pd.to_datetime(df['Timestamp'], unit='s')

# Calcola la differenza di tempo tra pacchetti successivi (delay)
df['time_diff'] = df['time'].diff().dt.total_seconds()

# Calcola il throughput come i byte trasmessi per secondo per ogni pacchetto
df['throughput'] = df['Length'] / df['time_diff']

# Calcola il delay tra pacchetti successivi (in secondi)
df['delay'] = df['time_diff']

# Calcola il jitter come la differenza tra il delay di pacchetti successivi
df['jitter'] = df['delay'].diff()

# Rimuovi eventuali righe con valori nulli
df = df.dropna()

# Salva il nuovo CSV con le nuove colonne
df.to_csv(r"C:\Users\ACER\Documents\netmod2\data_with_features_h2.csv", index=False)

print("File CSV trasformato e salvato come 'data_with_features.csv'")
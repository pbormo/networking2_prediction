import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import ipaddress
import ast  # Per convertire la stringa del dizionario in un dizionario Python
from tensorflow.keras.optimizers import Adam
# Step 1: Load CSV files from the directory
def load_csv_files(folder_path):
    data_frames = []
    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            file_path = os.path.join(folder_path, file)
            df = pd.read_csv(file_path)
            if 'Timestamp' not in df.columns:
                raise KeyError(f"The file {file} does not contain a 'Timestamp' column.")
            data_frames.append(df)
    return pd.concat(data_frames, ignore_index=True)

# Step 2: Preprocess the data

def preprocess_data(df):
    # Convert Timestamp to datetime and sort by time
    df['Time'] = pd.to_datetime(df['Timestamp'], unit='s', errors='coerce')
    
    # Impostare 'Time' come indice
    df.set_index('Time', inplace=True)
    
    # Ordinare i dati in base all'indice (Time)
    df.sort_index(inplace=True)

    # Features selection
    features = ['Jitter (s)', 'Avg Packet Size (bytes)', 'Packet Count', 'Delay (s)', 'Source IP', 'Destination IP']
    target = 'Throughput (Bps)'

    # Estrai tutte le colonne che contengono la distribuzione dei protocolli
    protocol_columns = [col for col in df.columns if col.startswith('Protocol_')]
    
    # Convertire le colonne di distribuzione dei protocolli da stringhe a dizionari e poi estrarre i valori
    for col in protocol_columns:
        # Convertire la stringa in un dizionario (se la colonna è una stringa)
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

        # Estrai il dizionario in colonne separate per ciascun protocollo
        protocol_df = pd.json_normalize(df[col])  # Normalizza ogni dizionario in colonne separate
        protocol_df.columns = [f'{col}_{key}' for key in protocol_df.columns]  # Rinomina le colonne con il prefisso del nome originale

        # Aggiungi le nuove colonne al DataFrame originale
        df = pd.concat([df, protocol_df], axis=1)
    
    # Rimuovere la colonna originale che contiene il dizionario
    df.drop(columns=protocol_columns, inplace=True)

    # Gestire gli IP mancanti
    df['Source IP'].fillna('0.0.0.0', inplace=True)
    df['Destination IP'].fillna('0.0.0.0', inplace=True)

    # Convertire gli indirizzi IP in interi
    df['Source IP'] = df['Source IP'].apply(lambda x: int(ipaddress.ip_address(x)))
    df['Destination IP'] = df['Destination IP'].apply(lambda x: int(ipaddress.ip_address(x)))

    # Convertire le feature numeriche
    for feature in features:
        if feature not in protocol_columns + ['Source IP', 'Destination IP']:
            df[feature] = pd.to_numeric(df[feature], errors='coerce')

    df[target] = pd.to_numeric(df[target], errors='coerce')

    # Rimuovere le righe con valori NaN
    df.dropna(inplace=True)

    # Separare le caratteristiche dai target
    X = df.drop(columns=[target])
    y = df[target]

    # Selezionare solo le colonne numeriche per la normalizzazione
    numeric_columns = X.select_dtypes(include=['number']).columns
    X_numeric = X[numeric_columns]

    # Normalizzare i dati
    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(X_numeric)
    scaled_target = scaler.fit_transform(y.values.reshape(-1, 1))

    return scaled_features, scaled_target, scaler, df

# Step 3: Create sequences for LSTM
def create_sequences(features, target, sequence_length):
    X, y = [], []
    for i in range(len(features) - sequence_length):
        X.append(features[i:i + sequence_length])
        y.append(target[i + sequence_length])
    return np.array(X), np.array(y)

# Step 4: Build the LSTM model con un learning rate personalizzato
def build_lstm_model(input_shape, learning_rate=0.001):
    # Creare l'ottimizzatore Adam con un learning rate personalizzato
    optimizer = Adam(learning_rate=learning_rate)
    
    model = Sequential([
        LSTM(128, activation='relu', return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(64, activation='relu'),
        Dropout(0.2),
        Dense(1)
    ])
    
    # Compilare il modello con l'ottimizzatore Adam e il learning rate
    model.compile(optimizer=optimizer, loss='mean_squared_error')
    return model

# Step 5: Train and evaluate the model (modificato per grafico con tre sezioni separate)
def train_and_predict(folder_path, train_ratio=0.75, sequence_length=15, epochs=30, batch_size=32, learning_rate=0.001):
    # Carica i dati
    df = load_csv_files(folder_path)
    
    # Preprocessing dei dati
    features, target, scaler, df = preprocess_data(df)

    # Calcolare il tempo totale per separare i dati in training e testing
    total_time = (df.index[-1] - df.index[0]).total_seconds()
    split_time = total_time * train_ratio

    # Separare i dati in base al tempo
    train_data = df[df.index <= df.index[0] + pd.Timedelta(seconds=split_time)]
    test_data = df[df.index > df.index[0] + pd.Timedelta(seconds=split_time)]

    # Preprocessing per i dati di training e testing
    train_features, train_target, _, _ = preprocess_data(train_data)
    X_train, y_train = create_sequences(train_features, train_target, sequence_length)
    
    test_features, test_target, _, _ = preprocess_data(test_data)
    X_test, y_test = create_sequences(test_features, test_target, sequence_length)

    # Creazione e allenamento del modello con il learning rate personalizzato
    model = build_lstm_model(X_train.shape[1:], learning_rate=learning_rate)
    model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, validation_data=(X_test, y_test))

    # Previsione sui dati di test
    predictions = model.predict(X_test)
    
    # Calcolare l'errore quadratico medio (MSE)
    mse = mean_squared_error(y_test, predictions)
    print(f"Mean Squared Error: {mse}")

    # Ripristinare la scala delle previsioni e dei valori reali
    predictions_rescaled = scaler.inverse_transform(predictions)
    y_test_rescaled = scaler.inverse_transform(y_test)

    # Grafico 1: Throughput di allenamento (zoomato sull'inizio)
    plt.figure(figsize=(12, 6))

    # Zoom sul throughput di allenamento (fino alla fine dei dati di training)
    train_throughput_rescaled = scaler.inverse_transform(train_target.reshape(-1, 1))
    plt.plot(df.index[:len(train_throughput_rescaled)], train_throughput_rescaled, label='Training Throughput', color='blue')

    plt.legend()
    plt.title("Training Throughput (Zoomed In)")
    plt.xlabel("Time")
    plt.ylabel("Throughput (Bps)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # Grafico 2: Throughput di test vs Previsione del test
    plt.figure(figsize=(12, 6))

    # Dati di test reali
    test_throughput_rescaled = scaler.inverse_transform(test_target.reshape(-1, 1))
    plt.plot(df.index[len(train_throughput_rescaled):len(train_throughput_rescaled)+len(test_throughput_rescaled)], 
             test_throughput_rescaled, label='Test Throughput', color='green')

    # Dati previsti per il test
    plt.plot(df.index[len(train_throughput_rescaled):len(train_throughput_rescaled)+len(predictions_rescaled)],
             predictions_rescaled, label='Predicted Throughput', color='red', alpha=0.7)

    plt.legend()
    plt.title("Test Throughput vs Predicted Throughput")
    plt.xlabel("Time")
    plt.ylabel("Throughput (Bps)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    return model

# Path to your data directory
folder_path = r"C:\Users\ACER\Documents\netmod2\daanalizzarefinali"
lstm_model = train_and_predict(folder_path, train_ratio=0.8, sequence_length=3, learning_rate=0.0001)
# Run the training and evaluation pipeline
#lstm_model = train_and_evaluate(folder_path)
import pandas as pd
import numpy as np
import tensorflow as tf
import keras_tuner as kt
import os
import re
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.model_selection import TimeSeriesSplit
from tensorflow.keras.layers import Bidirectional
from tensorflow.keras.regularizers import l2
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt

# Caricamento e preprocessamento dei dati
def load_and_preprocess_data(folder_path, host_mapping, host_folder_path):
    all_data = []
    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            match = re.search(r'_(s\d+)_', file)
            switch_id = match.group(1) if match else "unknown"
            
            df = pd.read_csv(os.path.join(folder_path, file))
            df = df[['Timestamp', 'Throughput (Bps)', 'Source Port', 'Destination Port', 'Protocol', 'Jitter (s)',	'Avg Packet Size (bytes)',	'Packet Count',	'Protocol Distribution', 'Delay (s)'
]]
            df.dropna(inplace=True)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.sort_values('Timestamp', inplace=True)
            df['Switch ID'] = switch_id
            
            all_data.append(df)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# Creazione delle sequenze per l'input della rete LSTM
def create_sequences(data, sequence_length):
    sequences, labels = [], []
    for i in range(len(data) - sequence_length):
        sequences.append(data[i:i + sequence_length])
        labels.append(data[i + sequence_length])
    return np.array(sequences), np.array(labels)
# Funzione per ridurre il learning rate ogni 10 epoche
def step_decay(epoch, lr):
    if epoch % 5 == 0 and epoch > 0:  # Ogni 10 epoche
        return lr * 0.5  # Riduce il learning rate del 50%
    return lr

# Definizione del modello LSTM
def build_lstm_model(input_shape):
    model = Sequential([
        Bidirectional(LSTM(128, return_sequences=True), input_shape=input_shape),
        Dropout(0.1),
        Bidirectional(LSTM(64, return_sequences=True)),
        Dropout(0.1),
        Bidirectional(LSTM(32, return_sequences=False)),
        Dropout(0.1),
        Dense(16, activation='relu', kernel_regularizer=l2(0.01)),
        Dense(1)
    ])
    optimizer = Adam(learning_rate=0.01, beta_1=0.9, beta_2=0.99, epsilon=1e-8)
    model.compile(optimizer=optimizer, loss='mse')
    return model
# Creazione del modello LSTM tradizionale
def build_lstm_model_2(input_shape):
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dense(64, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def build_bidirectional_lstm_model(input_shape):
    model = Sequential([
        Bidirectional(LSTM(128, return_sequences=True), input_shape=input_shape),
        Dropout(0.2),
        Bidirectional(LSTM(64, return_sequences=False)),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model
# Funzione di ricerca degli iperparametri con EarlyStopping
def build_model_hp(hp):
    model = Sequential([
        LSTM(hp.Int('units', min_value=32, max_value=128, step=16), return_sequences=True, input_shape=(10, 1)),
        Dropout(hp.Float('dropout_rate', min_value=0.1, max_value=0.4, step=0.1)),
        LSTM(hp.Int('units', min_value=16, max_value=64, step=16)),
        Dropout(hp.Float('dropout_rate', min_value=0.1, max_value=0.4, step=0.1)),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer=hp.Choice('optimizer', values=['adam', 'rmsprop']),
                  loss='mse')
    return model

# Allenamento e valutazione del modello
def train_and_evaluate_per_group(data_folder, host_folder, host_mapping, sequence_length=10, epochs=25, batch_size=16, output_folder="prediction"):
    df = load_and_preprocess_data(data_folder, host_mapping, host_folder)
    results = {}
    os.makedirs(output_folder, exist_ok=True)
    
    for (switch, source_port, dest_port, protocol), group in df.groupby(['Switch ID', 'Source Port', 'Destination Port', 'Protocol']):
        if len(group) < 15:
            print(f"Skipping ({switch}, {source_port}, {dest_port}, {protocol}) - Insufficient data")
            continue
        
        scaler = MinMaxScaler()
        group_scaled = scaler.fit_transform(group[['Throughput (Bps)']])
        
        if len(group_scaled) < sequence_length:
            print(f"Skipping ({switch}, {source_port}, {dest_port}, {protocol}) - Not enough sequences")
            continue
        
        # Creazione delle sequenze
        sequences, labels = create_sequences(group_scaled, sequence_length)

        # Divisione training/test 80-20 dopo la creazione delle sequenze
        #split_index = int(0.8 * len(sequences))  # Ora è basato sulle sequenze
        #tscv = TimeSeriesSplit(n_splits=5)
        #for train_idx, test_idx in tscv.split(sequences):
        #    X_train, X_test = sequences[train_idx], sequences[test_idx]
        #    y_train, y_test = labels[train_idx], labels[test_idx]
        
        # Aggiungi time_train come l'indice del dataset di allenamento
        #time_train = group.iloc[train_idx[0]:train_idx[-1]+1]['Timestamp']
        #time_test = group.iloc[test_idx[0]:test_idx[-1]+1]['Timestamp']

        # Configurazione della ricerca degli iperparametri
        #tuner = kt.Hyperband(
        #    build_model_hp,
        #    objective='val_loss',
        #    max_epochs=20,
        #    hyperband_iterations=4,
        #    directory='my_dir',
        #    project_name='lstm_tuning'
        #)

        # Ricerca degli iperparametri
        #tuner.search(X_train, y_train, epochs=10, validation_data=(X_test, y_test))

        # Modello migliore trovato dal Keras Tuner
        #best_model = tuner.get_best_models(num_models=1)[0]

        # Allena il miglior modello trovato
        #best_model.fit(X_train, y_train, epochs=10, validation_data=(X_test, y_test))

        # Previsioni con il miglior modello
        #y_pred_best = best_model.predict(X_test)

        # Dati di training e test
        X_train, X_test, y_train, y_test = train_test_split(sequences, labels, test_size=0.2, random_state=42, shuffle=False)

        # Costruzione e addestramento del modello
        model = build_lstm_model((sequence_length, 1))
        # Callback per la riduzione del learning rate
        lr_callback = tf.keras.callbacks.LearningRateScheduler(step_decay)

        # Addestramento del modello con la callback
        model.fit(X_train, y_train, 
                epochs=epochs, 
                batch_size=batch_size, 
                validation_data=(X_test, y_test),
                callbacks=[lr_callback])

        y_pred = model.predict(X_test)

        results[(switch, source_port, dest_port, protocol)] = (y_test, y_pred)

        output_file = os.path.join(output_folder, f'prediction_{switch}_{source_port}_{dest_port}_{protocol}.csv')
        pd.DataFrame({'Real': y_test.flatten(), 'Predicted': y_pred.flatten()}).to_csv(output_file, index=False)

        # Creiamo un asse temporale coerente rispetto ai dati effettivi
        time_train = range(len(y_train))  # Indici per il training
        time_test = range(len(y_train), len(y_train) + len(y_test))  # Indici per il test e la predizione

        # Creazione del plot
        plt.figure(figsize=(10, 5))

        # Plot del throughput reale
        plt.plot(time_train, y_train.flatten(), label='Real Throughput (Train)', linestyle='dashed', color='blue')
        plt.plot(time_test, y_test.flatten(), label='Real Throughput (Test)', linestyle='dashed', color='green')

        # Plot della predizione (sovrapposta alla fase di test)
        plt.plot(time_test, y_pred.flatten(), label='Predicted Throughput', color='red')

        # Linea di separazione tra training e test
        plt.axvline(x=len(y_train), color='r', linestyle='--', label='Prediction Start')

        # Titolo e legenda
        plt.title(f'Switch: {switch}, Source Port: {source_port}, Destination Port: {dest_port}, Protocol: {protocol}')
        plt.legend()

        # Debug: verifica il percorso di salvataggio
        output_path = os.path.join(output_folder, f'plot_{switch}_{source_port}_{dest_port}_{protocol}.png')
        print(f"Saving plot to: {output_path}")

        # Salvataggio del grafico
        plt.savefig(output_path)
        plt.close()

    return results

# Esempio di utilizzo
host_mapping = {
    "s1": ["h1", "h2", "h3"],
    "s2": ["h4", "h5"],
    "s3": ["h6"],
    "s4": ["h7"]
}

results = train_and_evaluate_per_group(
    r"C:\Users\ACER\Documents\netmod2\ultimi_test_fatti_csv\switch",
    r"C:\Users\ACER\Documents\netmod2\ultimi_test_fatti_csv\host",
    host_mapping
)
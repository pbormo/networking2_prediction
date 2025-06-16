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
from tensorflow.keras.layers import BatchNormalization
import matplotlib.pyplot as plt

# Loading and preprocessing data
def load_and_preprocess_data(folder_path):
    all_data = []
    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            # Extract Switch ID from filename
            match = re.search(r'_(s\d+)-([a-z0-9]+)', file)
            if match:
                switch_id = match.group(1)
            else:
                switch_id = "unknown"

            # Load CSV data
            df = pd.read_csv(os.path.join(folder_path, file))
            df = df[['Timestamp', 'Throughput (Bps)', 'Source Port', 'Destination Port', 'Protocol', 'Jitter (s)', 'Avg Packet Size (bytes)', 'Packet Count', 'Protocol Distribution', 'Delay (s)']]
            df.dropna(inplace=True)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.sort_values('Timestamp', inplace=True)
            df['Switch ID'] = switch_id
            all_data.append(df)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# Step decay function to reduce learning rate every 10 epochs
def step_decay(epoch, lr):
    if epoch % 10 == 0 and epoch > 0:  
        return lr * 0.5  # Reduce learning rate by 50% every 10 epochs
    return lr

# Bidirectional LSTM model definition
def build_lstm_model_bidirectional(input_shape):
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

# Classic LSTM model
def build_lstm_model_classic(input_shape):
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        BatchNormalization(),
        Dropout(0.1),
        LSTM(64, return_sequences=True),
        BatchNormalization(),
        Dropout(0.1),
        LSTM(32, return_sequences=False),
        BatchNormalization(),
        Dense(16, activation='relu'),
        BatchNormalization(),
        Dense(1)
    ])
    optimizer = Adam(learning_rate=0.005)
    model.compile(optimizer=optimizer, loss='mse')
    return model

# Simpler bidirectional model
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

# Hyperparameter tuning model builder
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

# Training and evaluation function for each group
def train_and_evaluate_per_group(data_folder, output_folder, sequence_length=5, epochs=10, batch_size=16):
    df = load_and_preprocess_data(data_folder)
    results = {}
    os.makedirs(output_folder, exist_ok=True)
    
    for (switch, source_port, dest_port, protocol), group in df.groupby(['Switch ID', 'Source Port', 'Destination Port', 'Protocol']):
    #for (switch, source_port, dest_port, protocol), group in df.groupby(['Switch ID', 'Source IP', 'Destination IP', 'Protocol']):
        min_required_length = sequence_length + 2  # o altro valore minimo

        if len(group) < min_required_length:
            print(f"Skipping ({switch}, {source_port}, {dest_port}, {protocol}) - Not enough data to generate sequences")
            continue

        scaler = MinMaxScaler()
        selected_features = ['Throughput (Bps)', 'Jitter (s)', 'Delay (s)', 'Avg Packet Size (bytes)', 'Packet Count']
        group_scaled = scaler.fit_transform(group[selected_features])

        # Create sequences
        sequences = []
        labels = []
        for i in range(len(group_scaled) - sequence_length):
            sequences.append(group_scaled[i:i + sequence_length])
            labels.append(group_scaled[i + sequence_length][0])  # predict only throughput
        #to use time series and tuner
        #split_index = int(0.8 * len(sequences)) 
        #tscv = TimeSeriesSplit(n_splits=5)
        #for train_idx, test_idx in tscv.split(sequences):
        #    X_train, X_test = sequences[train_idx], sequences[test_idx]
        #    y_train, y_test = labels[train_idx], labels[test_idx]
        
        #time_train = group.iloc[train_idx[0]:train_idx[-1]+1]['Timestamp']
        #time_test = group.iloc[test_idx[0]:test_idx[-1]+1]['Timestamp']

        #tuner = kt.Hyperband(
        #    build_model_hp,
        #    objective='val_loss',
        #    max_epochs=20,
        #    hyperband_iterations=4,
        #    directory='my_dir',
        #    project_name='lstm_tuning'
        #)

        #tuner.search(X_train, y_train, epochs=10, validation_data=(X_test, y_test))

        #best_model = tuner.get_best_models(num_models=1)[0]

        #best_model.fit(X_train, y_train, epochs=10, validation_data=(X_test, y_test))

        #y_pred_best = best_model.predict(X_test)

        # Convert to NumPy arrays and split into train/test (80/20)
        sequences = np.array(sequences)
        labels = np.array(labels)
        X_train, X_test, y_train, y_test = train_test_split(sequences, labels, test_size=0.2, random_state=42, shuffle=False)

        # Build and train the model
        model = build_lstm_model_classic((sequence_length, len(selected_features)))
        lr_callback = tf.keras.callbacks.LearningRateScheduler(step_decay)

        model.fit(X_train, y_train, 
                epochs=epochs, 
                batch_size=batch_size, 
                validation_data=(X_test, y_test),
                callbacks=[lr_callback])

        y_pred = model.predict(X_test)

        results[(switch, source_port, dest_port, protocol)] = (y_test, y_pred)

        # Save predictions to CSV
        output_file = os.path.join(output_folder, f'prediction_{switch}_{source_port}_{dest_port}_{protocol}.csv')
        pd.DataFrame({'Real': y_test.flatten(), 'Predicted': y_pred.flatten()}).to_csv(output_file, index=False)

        # Create a coherent time axis
        time_train = range(len(y_train)) # Indexes for training
        time_test = range(len(y_train), len(y_train) + len(y_test))  # Indexes for test/prediction

        # Plot results
        plt.figure(figsize=(10, 5))

        plt.plot(time_train, y_train.flatten(), label='Real Throughput (Train)', linestyle='dashed', color='blue')
        plt.plot(time_test, y_test.flatten(), label='Real Throughput (Test)', linestyle='dashed', color='green')

        plt.plot(time_test, y_pred.flatten(), label='Predicted Throughput', color='red')

        plt.axvline(x=len(y_train), color='r', linestyle='--', label='Prediction Start')

        plt.title(f'Switch: {switch}, Source Port: {source_port}, Destination Port: {dest_port}, Protocol: {protocol}')
        plt.legend()

        output_path = os.path.join(output_folder, f'plot_{switch}_{source_port}_{dest_port}_{protocol}.png')
        print(f"Saving plot to: {output_path}")

        plt.savefig(output_path)
        plt.close()

    return results

# Run the function on the provided dataset
current_dir = os.path.dirname(__file__)

# Go up one directory and into 'preprocessing/prediction'
data_folder = os.path.join(current_dir, '..', 'prediction')
output_folder = os.path.join(current_dir, '..', 'results')
results = train_and_evaluate_per_group(
    data_folder
)

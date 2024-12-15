import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt

# 1. Carica il file CSV
df = pd.read_csv(r"C:\Users\ACER\Documents\netmod2\data_with_features_h2.csv")

# 2. Seleziona le colonne di interesse
data = df[['throughput', 'delay', 'jitter']]  # Usa le colonne che ti servono

# 3. Controlla e gestisci i valori NaN e inf
# Verifica la presenza di NaN o infini
print(f"Contains NaN: {data.isna().sum()}")
print(f"Contains Inf: {np.isinf(data).sum()}")

# Sostituire NaN con la media delle colonne e rimuovere infini
data = data.replace([np.inf, -np.inf], np.nan)  # Sostituisci inf con NaN
data = data.fillna(data.mean())  # Sostituisci NaN con la media di ciascuna colonna

# 4. Normalizza i dati
scaler = MinMaxScaler(feature_range=(0, 1))  # Normalizza tra 0 e 1
scaled_data = scaler.fit_transform(data)

# 5. Funzione per creare sequenze di dati
def create_sequences(data, time_step=30):
    X, y = [], []
    for i in range(len(data) - time_step):
        X.append(data[i:i + time_step])
        y.append(data[i + time_step, 0])  # Predici il throughput (colonna 0)
    return np.array(X), np.array(y)

# 6. Crea le sequenze di input per l'addestramento
time_step = 30  # Numero di punti temporali da usare come input
X, y = create_sequences(scaled_data, time_step)

# 7. Dividi i dati in train e test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# 8. Reshape dei dati per l'input LSTM [samples, time steps, features]
X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], X_train.shape[2])
X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], X_test.shape[2])

# 9. Crea il modello LSTM
model = Sequential()
model.add(LSTM(units=50, return_sequences=False, input_shape=(X_train.shape[1], X_train.shape[2])))
model.add(Dense(units=1))  # Una sola previsione (output) per il throughput

# 10. Compila il modello
model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')

# 11. Allena il modello
model.fit(X_train, y_train, epochs=50, batch_size=32, validation_data=(X_test, y_test))

# 12. Previsioni sul test set
predictions = model.predict(X_test)

# 13. Inverti la normalizzazione per ottenere i valori originali
predictions = scaler.inverse_transform(np.concatenate((predictions, np.zeros((predictions.shape[0], data.shape[1] - 1))), axis=1))[:, 0]
y_test = scaler.inverse_transform(np.concatenate((y_test.reshape(-1, 1), np.zeros((y_test.shape[0], data.shape[1] - 1))), axis=1))[:, 0]

# 14. Visualizza le prime 10 previsioni vs. valori reali
for i in range(10):
    print(f"Predicted: {predictions[i]}, Actual: {y_test[i]}")

# 15. Aggiungere la parte per predire i valori futuri
future_steps = 10
last_sequence = scaled_data[-time_step:]  # Ultima sequenza
future_predictions = []

for _ in range(future_steps):
    # Reshaping dell'input
    last_sequence = last_sequence.reshape(1, time_step, data.shape[1])
    
    # Previsione per il prossimo passo temporale
    next_prediction = model.predict(last_sequence)
    future_predictions.append(next_prediction[0][0])
    
    # Aggiorna la sequenza
    last_sequence = np.roll(last_sequence, -1, axis=0)
    last_sequence[-1] = np.concatenate((next_prediction, np.zeros((1, data.shape[1] - 1))), axis=1)

# 16. Inverti la normalizzazione per ottenere i valori originali
future_predictions = scaler.inverse_transform(np.concatenate((np.array(future_predictions).reshape(-1, 1), np.zeros((len(future_predictions), data.shape[1] - 1))), axis=1))[:, 0]

# 17. Visualizza le previsioni future
print(f"Future predictions: {future_predictions}")

# 18. Salva il modello
model.save('lstm_model_h2.h5')

# 19. Salva le previsioni in un file CSV
prediction_df = pd.DataFrame({'predicted_throughput': predictions, 'actual_throughput': y_test})
prediction_df.to_csv('predictions_h2.csv', index=False)

# 20. (Opzionale) Visualizzazione dei risultati
plt.figure(figsize=(10, 6))
plt.plot(y_test, label='Real Throughput')
plt.plot(predictions, label='Predicted Throughput')
plt.title('Real vs Predicted Throughput')
plt.xlabel('Time Steps')
plt.ylabel('Throughput')
plt.legend()
plt.show()
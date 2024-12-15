# networking2_prediction
project networking 2 on SDN prediction
# Network Throughput Prediction with LSTM

This project aims to predict network throughput in Software-Defined Networks (SDN) using machine learning techniques. It includes automated packet capturing, preprocessing of pcap files, and an LSTM-based prediction model.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Project Structure](#project-structure)
4. [Running the Project](#running-the-project)
5. [Contributing](#contributing)
6. [License](#license)
7. [Contact](#contact)

## Prerequisites

Make sure you have the following installed on your system:
- **Python**: Version >= 3.8
- **Git**: Version >= 2.30
- **VirtualBox**: To run the Comnetsemu environment
- **Mininet**: For SDN simulation
- **Git LFS**: For managing large files like `.pcap`
- Additional Python libraries (see [requirements.txt](requirements.txt))

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/networking2_prediction.git
   cd networking2_prediction
   ```

2. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up VirtualBox and Comnetsemu:
   Follow the instructions from the [Comnetsemu documentation](https://www.comnetsemu.com) to configure the environment.

4. Set up Git LFS:
   ```bash
   git lfs install
   ```

## Project Structure

```plaintext
networking2_prediction/
|
|-- network/             # Scripts to set up and manage the SDN simulation
|   |-- network_simulation.py
|
|-- preprocessing/       # Scripts to preprocess `.pcap` files
|   |-- preprocess_pcap.py
|
|-- lstm/                # Scripts to train and evaluate the LSTM model
|   |-- train_lstm.py
|   |-- evaluate_model.py
|
|-- file_da_predirre/    # Folder containing `.pcap` files for prediction
|
|-- README.md            # Project documentation (this file)
|-- requirements.txt     # Python dependencies
```

## Running the Project

### Step 1: Start the Network Simulation
Navigate to the `network` folder and run the network script:
```bash
cd network
python3 network_simulation.py
```

### Step 2: Generate Traffic
Use tools like `iperf` to generate random traffic. The captured data will be saved as `.pcap` files in the `file_da_predirre` directory.

### Step 3: Preprocess the Data
Preprocess the `.pcap` files by running:
```bash
cd preprocessing
python3 preprocess_pcap.py
```

### Step 4: Train and Test the LSTM Model
Train the model using the preprocessed data:
```bash
cd lstm
python3 train_lstm.py
```
Evaluate the predictions:
```bash
python3 evaluate_model.py
```

## Contributing

We welcome contributions to this project! To contribute:
1. Fork the repository.
2. Create a branch for your feature:
   ```bash
   git checkout -b feature-name
   ```
3. Push your changes:
   ```bash
   git push origin feature-name
   ```
4. Submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, contact:
- **Your Name**: your.email@example.com
- **Teammate's Name**: teammate.email@example.com


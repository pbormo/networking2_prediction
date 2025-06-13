
# Network Throughput Prediction with LSTM

This project aims to predict network throughput in Software-Defined Networks (SDN) using machine learning techniques. It includes automated packet capturing, preprocessing of pcap files and an LSTM-based prediction model.

## Table of Contents
1. [Pre-requisites](#prerequisites)
2. [Installation](#installation)
3. [Project Structure](#project-structure)
4. [Topology](#topology)
5. [Running the Project](#running-the-project)
6. [Models](#models)
7. [Contact](#contact)

## Pre-requisites

Before you begin, make sure you have the following installed:

- **Python**: Version >= 3.8
- **Git**: Version >= 2.30
- **VirtualBox**: For running the Comnetsemu environment
- **Mininet**: For SDN simulation
- **Required Python libraries**: These can be found in the `requirements.txt` file.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/networking2_prediction.git
   cd networking2_prediction
   ```

2. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up VirtualBox and Comnetsemu:
   Follow the instructions in the [Comnetsemu documentation](https://www.comnetsemu.com) to configure the environment.

## Project Structure

```plaintext
networking2_prediction/
│
├── network/                # SDN simulation setup and management
│   └── traffic_gen.py
│
├── preprocessing/          # Scripts to preprocess `.pcap` files
│   ├── pcaptocsv.py
│
├── lstm/                   # LSTM model training and evaluation
│   ├── lstm.py
│
├── prediction/             # Folder containing `.csv` files for prediction and testing
│   ├── test_short
│      ├── host
│      ├── switch
│   ├── test_complete
│      ├── host
│      ├── switch
│
├── results                 # Folder containing result graphs of prediction
├── README.md               # Project documentation (this file)
├── requirements.txt        # Python dependencies
```

## Topology
![topology]()<img width="523" alt="Screenshot 2025-06-13 at 18 19 32" src="https://github.com/user-attachments/assets/0a01d3e5-53e9-42ae-b7b4-ba0ed0f58cb1" />

## Running the Project

### Step 1: Start the Network Simulation
Run the Comnetsemu VM in VirtualBox. Before starting the VM, set up port forwarding via SSH to use the terminal for running simulations. Once the VM is open, connect via SSH with the following command:
```bash
ssh -X -p 3022 comnetsemu@localhost
```
After logging in, configure the display for network visualization:
```bash
export DISPLAY=192.168.1.177:0.0
xclock
```

Make sure no previous Docker containers are running:
```bash
docker ps
docker stop $(docker ps -q)
ps aux | grep docker
sudo kill -9 <process_id>
```

Ensure there are no networks in the VM:
```bash
sudo mn -c
```

Once everything is ready, navigate to the `network` folder and start the simulation:
```bash
cd network
sudo python3 traffic_gen.py
```

### Step 2: Generate Traffic
The network traffic is generated and captured in a Mininet/Containernet emulated environment. It sets up a custom network topology, starts web and TCP servers, and uses tools like `hping3`, `curl` and `socat` to generate TCP, UDP and HTTP traffic between hosts. The script also captures all traffic using `tcpdump`, saving the results as .pcap files for later analysis. This process is repeated for multiple iterations to create diverse traffic datasets.

### Step 3: Preprocess the Data
Preprocess the `.pcap` files by running:
```bash
cd preprocessing
python3 preprocess_pcap.py
```

### Step 4: Train and Test the LSTM Model
Use the LSTM model with the preprocessed data to train LSTM and take a prediction:
```bash
cd lstm
python3 lstm.py
```

## LSTM Model used
Explaination on models used

## Contact

For questions or support, contact:
- **Paolo Bormolini**: paolo.bormolini@studenti.unitn.it
- **Carolina Sopranzetti**: carolina.sopranzetti@studenti.unitn.it


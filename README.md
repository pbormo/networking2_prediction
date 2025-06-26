
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
1. Set up VirtualBox and Comnetsemu:
   Follow the instructions in the [Comnetsemu documentation](https://www.comnetsemu.com) to configure the environment.

2. Clone the repository:
   ```bash
   git clone https://github.com/pbormo/networking2_prediction.git
   cd networking2_prediction
   ```

3. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

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
├── prediction/         # Folder containing `.csv` files for prediction and testing
│
├── traffic_records/        # Folder containing `.pcap` files for preprocessing
│
├── lstm/                   # LSTM model training and evaluation
│   ├── lstm.py
│
├── results/                 # Folder containing result graphs of prediction
│   ├── multiple_prediction
│   ├── single_prediction
│
├── README.md               # Project documentation (this file)
├── requirements.txt        # Python dependencies
```

## Topology
![topology](https://github.com/user-attachments/assets/b78213d1-1163-4db4-8ecd-9e10a604a90c)

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

or use Vagrant to access the Comnetsemu environment:
```bash
vagrant up comnetsemu
vagrant ssh comnetsemu
```

Once everything is ready, navigate to the `network` folder and start the simulation:
```bash
cd network
sudo python3 traffic_gen.py
```

### Step 2: Generate Traffic
The network traffic is generated and captured in a Mininet/Containernet emulated environment. It sets up a custom network topology, starts web and TCP servers, and uses tools like `hping3`, `curl` and `socat` to generate TCP, UDP and HTTP traffic between hosts. All traffic is captured using `tcpdump`, saving the results as .pcap files for later analysis. This process is repeated for multiple iterations to create diverse traffic datasets.

### Step 3: Preprocess the Data
Starting from the data contained in the `.pcap` files generated in the 2nd step we want to extract the most important features (e.g. Throughput, Jitter, Delay, Protocol...) and put them inside a `.csv` files. 
Preprocess all `.pcap` files in the `traffic_records` directory, or specify a particular subfolder to process only its contents.  
- To process **all** `.pcap` files:
  ```bash
  cd preprocessing
  python3 pcaptocsv.py
  ```
- To process a **specific subfolder** (e.g., `folder_name`):
  ```bash
  cd preprocessing
  python3 pcaptocsv.py <folder_name>
  ```

### Step 4: Train and Test the LSTM Model
Using the LSTM model with the preprocessed data to train LSTM and take a prediction of thoughput over the diffent switches inside the network:
```bash
cd lstm
python3 lstm.py
```

## LSTM Model used
Inside the code it can be possible to find different configuration of LSTM algorithm, for the data that we have we choose to use the classical LSTM algorithm with 3 layers, dropout (0.2) and BatchNormalization().
![LSTM_classic](https://github.com/user-attachments/assets/96c2fce7-8a58-4c88-b198-f1c68a62dc2a)
## Contact

For questions or support, contact:
- **Paolo Bormolini**: paolo.bormolini@studenti.unitn.it
- **Carolina Sopranzetti**: carolina.sopranzetti@studenti.unitn.it


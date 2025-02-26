
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

Before you begin, make sure you have the following installed:

- **Python**: Version >= 3.8
- **Git**: Version >= 2.30
- **VirtualBox**: For running the Comnetsemu environment
- **Mininet**: For SDN simulation
- **Git LFS**: For managing large files (e.g., `.pcap` files)
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
│   └── web_server.py
│
├── preprocessing/          # Scripts to preprocess `.pcap` files
│   ├── pcaptocsv_buono.py
│
├── lstm/                   # LSTM model training and evaluation
│   ├── lstm.py
│
├── prediction/             # Folder containing `.csv` files for prediction and testing
│   ├── test_prova_2
│      ├── host
│      ├── switch
│   ├── test_singolo_finale
│      ├── host
│      ├── switch
│
├── README.md               # Project documentation (this file)
├── requirements.txt        # Python dependencies
```

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
sudo python3 web_server.py
```

### Step 2: Generate Traffic
Use `iperf` or similar tools to generate traffic. The captured data will be saved as `.pcap` files in the `file_da_predirre` directory. This directory can't be uploaded here due to the big size but you can recreate that easily. But in `prediction` directory you can find some preprocessed data that they are saved as `.csv` using the following step.

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, contact:
- **Paolo Bormolini**: paolo.bormolini@studenti.unitn.it
- **Carolina Sopranzetti**: carolina.sopranzetti@studenti.unitn.it


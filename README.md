# Python Blockchain Simulation (Controller + 3 Independent Servers)

A classroom-friendly blockchain simulation with:
- Controller Server (UI): orchestrates actions and shows logs
- Server A node
- Server B node
- Server C node

Each node runs as an independent Flask server and maintains its own chain and validation logic.

## Features

- Proof-of-Work mining (nonce + SHA-256, hash prefix `0000`)
- Mining race among nodes with winner broadcast
- Consensus mechanism (longest valid chain)
- Invalid block attack simulation
- 51% attack simulation
- Performance analysis:
  - block creation time
  - network delay
  - throughput
  - scalability projection when node count increases

## Run

1. Create and activate a Python environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start everything (controller + 3 nodes + open pages):
   ```bash
   python start_all.py
   ```

This opens:
- Controller UI: http://127.0.0.1:5000
- Server A: http://127.0.0.1:5001
- Server B: http://127.0.0.1:5002
- Server C: http://127.0.0.1:5003

## Manual Start (optional)

In separate terminals:

```bash
python node_server.py --name "Server A" --port 5001
python node_server.py --name "Server B" --port 5002
python node_server.py --name "Server C" --port 5003
python app.py --port 5000
```

## Demo Flow

1. Click **Start Mining (All Servers)**
2. Observe winner and broadcast validation
3. Click **Apply Consensus**
4. Run **Simulate Invalid Block Attack**
5. Run **Simulate 51% Attack**
6. Click **Show Performance Metrics**

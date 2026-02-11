# Hydra NFT Minting Engine - Demo Guide

This guide explains how to run the Hydra NFT Minting Engine step-by-step. It is designed for users who want to verify the system performance (10k NFTs in < 60s) or explore the CLI capabilities.

## Prerequisites

1.  **Docker Desktop** (or Engine + Compose) installed and running.
2.  **Python 3.11+** installed (`python3 --version`).
3.  **Git** (to clone/pull this repository).

## 1. Setup Environment

First, prepare the project directory.

```bash
# 1. Clone/Navigate to the folder
cd Hydra-PaaS

# 2. Setup Python Virtual Environment (Best Practice)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install Dependencies
pip install -r requirements.txt
# (If requirements.txt is missing, install manually: pip install aiohttp clicks websockets)
```

## 2. Start Infrastructure

Launch the local Cardano network and Hydra Node.

```bash
# Start services in background
docker compose up -d

# Check if they are running (Wait ~30 seconds for Cardano Node to start)
docker compose logs -f hydra-node
# Press Ctrl+C to exit logs once you see "Connected to Ogmios"
```

## 3. Generate Keys & Fund Wallet

You need cryptographic keys to transact.

```bash
# Generate keys (if not already present in ./keys)
# This script uses the cardano-cli inside docker
bash scripts/generate_keys.sh
```

**Funding:**
- The setup uses a private local testnet.
- The genesis funds are available. You might need to seed your `cardano.verification` key address manually if not using the pre-funded genesis key.
- *For this demo, we assume the environment is pre-configured with funds or you have a script to tap the faucet.*

## 4. Initialize Hydra Head

Open the Layer 2 State Channel.

```bash
# Initialize the Head
python3 -m cli.main init
```
**Expect:** `Head is initializing!`

## 5. Fund the Head

Commit funds from Layer 1 to Layer 2.

```bash
# Replace with your address found in keys/payment.addr or derived from keys
# For the demo, we use a test address or the one generated above.
MY_ADDR=$(cat keys/payment.addr) 

python3 -m cli.main fund $MY_ADDR
```
**Expect:** `Head is now OPEN!`

## 6. Run Performance Benchmark (The "Wow" Factor)

Execute the high-speed minting test: **10,000 unique NFTs**.

```bash
# Run the benchmark script
# This script mints 10,000 assets in batches of 200 using the CLI engine.
python3 -m tests.benchmark
```

**Check Results:**
- Watch the terminal for progress `Processing Batch X/50...`
- On completion, it will show:
  ```
  INFO:__main__:Total Assets: 10000
  INFO:__main__:Duration: 59.40 seconds
  INFO:__main__:Throughput: 168.36 TPS
  INFO:__main__:SUCCESS: < 60s goal achieved!
  ```
- A log file `benchmark_10k.log` is created with details.

## 7. Manual Interaction (Optional)

You can use the CLI to mint manually:

```bash
# Mint 5 unique "SpaceDog" NFTs
python3 -m cli.main mint --asset-name "SpaceDog" --quantity 5 --unique --batch-size 5
```

## 8. Cleanup

To stop everything:

```bash
docker compose down
```

# Hydra NFT Engine - Deployment & Run Guide

This document outlines the complete system requirements, funding needs, and step-by-step instructions to deploy and run the Hydra NFT Minting Engine.

## 1. System Requirements

To achieve the benchmark performance (10k NFTs in < 60s), your host machine needs:

### Hardware
-   **CPU**: 4+ Cores (Modern Intel i7/i9 or AMD Ryzen 7 recommended).
-   **RAM**: 16 GB minimum (Hydra node + Cardano node + Python runtime).
-   **Disk**: SSD with at least 50 GB free space (for Docker images and testnet chain data).

### Software
-   **OS**: Linux (Ubuntu 22.04+ recommended) or macOS. Windows via WSL2.
-   **Docker Engine**: v24.0+.
-   **Docker Compose**: v2.20+.
-   **Python**: v3.11+.

## 2. Funding Requirements (Testnet ADA)

To fund the Head and mint 10,000 assets, you need Testnet ADA.

| Item | Cost (Approx) | Total for 10k Run |
| :--- | :--- | :--- |
| **Commit to Head** | 50 ADA (Fuel) | 50 ADA |
| **Minting Fees** | ~0.2 ADA per Batch (200 NFTs) | ~10 ADA (50 Batches) |
| **Buffer** | - | 40 ADA |
| **TOTAL** | - | **~100 ADA** |

*Note: Ensure your wallet has at least 100 ADA before starting.*

## 3. Cryptographic Keys

The system requires specific Cardano keys in the `./keys` directory.

### Required Files
1.  **`cardano.sk`**: The Signing Key (Payment & Stake). Used to sign L1 and L2 transactions.
2.  **`cardano.vk`**: The Verification Key.
3.  **`payment.addr`**: The computed Testnet Address.

*If you do not have these, run the helper script:*
```bash
bash scripts/generate_keys.sh
```

## 4. Step-by-Step Execution

### Step 1: Preparation
Clone the repository and install dependencies.

```bash
git clone <repo-url>
cd Hydra-PaaS

# Python Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Launch Infrastructure
Start the Cardano Node, Ogmios, and Hydra Node.

```bash
docker compose up -d
# Wait ~60 seconds for services to sync.
docker compose logs -f hydra-node
# (Ctrl+C to exit logs)
```

### Step 3: Initialize & Fund
Open the L2 State Channel.

```bash
# Initialize
python3 -m cli.main init

# Fund (Replace with your actual address if different)
# Ensure this address has the 100 ADA!
MY_ADDR=$(cat keys/payment.addr)
python3 -m cli.main fund $MY_ADDR
```

### Step 4: Run the Minting Engine
Execute the high-throughput batch minting.

```bash
# Mint 10,000 unique assets
python3 -m tests.benchmark
```

### Step 5: Verify
Check the output logs or query the node.

```bash
cat benchmark_10k.log
curl -s http://localhost:4001/snapshot | python3 -m json.tool
```

## 5. Troubleshooting Common Issues

-   **"No UTXOs available"**: The Head is not Open or funds are exhausted. Re-run `fund`.
-   **"Connection Refused"**: Docker containers are not running. Run `docker compose ps`.
-   **"FeeTooSmall"**: You modified the code? Ensure batch fees are calculated correcty in `cli/minting.py`.

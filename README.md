# Hydra NFT Minting Engine

High-throughput NFT minting mechanism for Cardano Hydra Heads, capable of interacting with the Hydra Node API to mint assets on L2.

**Performance:** Verified ~168 TPS (10k assets in < 60s).

## Quick Start

### 1. Prerequisites
- Docker & Compose
- Python 3.11+

### 2. Setup
```bash
git clone <repo>
cd Hydra-PaaS

# Setup venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start Infrastructure
docker compose up -d
```

### 3. Usage
**Generate Keys:**
```bash
bash scripts/generate_keys.sh
```

**Init & Fund Head:**
```bash
python3 -m cli.main init
python3 -m cli.main fund $(cat keys/payment.addr)
```

**Run Benchmark (10k Mints):**
```bash
python3 -m tests.benchmark
```

### 4. Manual Minting
```bash
# Mint 5 unique assets
python3 -m cli.main mint --asset-name "SpaceDog" --quantity 5 --unique --batch-size 5
```

## Structure
- `cli/`: Core Python client and minting logic.
- `keys/`: Crypto keys (generated).
- `scripts/`: Helpers.
- `tests/`: Benchmarks and unit tests.

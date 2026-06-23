# Setup Guide

This guide will walk you through deploying the HydraLite Micro-PaaS Engine on your local machine for testing and development.

## Prerequisites

Before beginning, ensure your system meets the following requirements:
- **Operating System:** Linux (Ubuntu 20.04+) or macOS. Windows users must use WSL2.
- **Docker:** Docker and Docker Compose installed and running.
- **Python:** Python 3.10 or higher.
- **Hardware:** At least 16GB of RAM (Cardano nodes require significant memory).

---

## 1. Clone the Repository

Clone the latest release of the HydraLite repository and navigate into the directory:

```bash
git clone https://github.com/Kwired/Hydra-Powered-Micro-PaaS.git
cd Hydra-Powered-Micro-PaaS
git checkout release/v0.9.0
```

## 2. Environment Setup

Copy the environment template and install the required Python dependencies into a virtual environment:

```bash
cp .env.template .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

*(Note: Review the `.env` file to ensure the `CARDANO_NETWORK` is set to `preprod` for local testing).*

## 3. Generate Cryptographic Keys

HydraLite requires cryptographic keys to sign Layer-2 transactions. We have provided an automated script to generate these safely:

```bash
chmod +x scripts/generate_keys.sh
./scripts/generate_keys.sh
```

This will populate your `keys/` directory with the necessary `.skey` and `.vkey` files.

## 4. Launch the Infrastructure

Use Docker Compose to spin up the Cardano Node, the Hydra Node, and the Ogmios WebSocket server:

```bash
docker compose up -d
```

> [!WARNING]
> If this is your first time running the stack, the Cardano node must synchronize with the Preprod network using Mithril. This process is fully automated but may take 15–30 minutes depending on your internet connection. You can monitor the sync status by running: `docker compose logs -f hydra-node`.

## 5. Start the FastAPI Engine

Once your Docker containers are synchronized and running, start the HydraLite FastAPI middleware engine:

```bash
uvicorn api.main:app --reload --port 8000
```

Your API is now live at `http://127.0.0.1:8000`. You can visit `http://127.0.0.1:8000/docs` to view the interactive Swagger API interface.

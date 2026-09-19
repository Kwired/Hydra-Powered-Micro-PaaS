# HydraLite Production Release (v1.0.0)

HydraLite is a high-performance NFT Minting Engine built on Cardano's Hydra L2 scaling solution. It enables ultra-fast, low-cost parallel batch minting by leveraging state channels.

## Architecture
See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for a complete system overview.

## Components
- **Hydra Infrastructure**: Managed via Docker (Cardano Node, Hydra Node, Mithril, Ogmios).
- **CLI / Minting Engine**: High-throughput parallel Python client for building, signing, and submitting transactions to the Hydra Head.
- **REST API**: FastAPI integration for application interactions.
- **Dashboard**: React-based frontend.

## Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Docker & Docker Compose**: v2.0+
- **Python**: 3.11+

## Installation
1. Clone the repository and configure the environment:
   ```bash
   cp .env.example .env
   # Update .env with your specific configuration
   ```

2. Generate or place your signing keys in the `keys/` directory.

3. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Configuration
All application settings are managed via the `.env` file. Do not commit actual secrets to the repository.
- `CARDANO_NETWORK`: e.g., `preprod`
- `ALLOWED_ORIGINS`: CORS origins for the API
- `HYDRA_API_URL`: Websocket/HTTP endpoint for the Hydra Node

## Deployment
Start the production infrastructure using Docker Compose:
```bash
docker compose -f docker-compose.prod.yml up -d
```
Ensure that the node is fully synced before initiating any Hydra transactions.

## Testing
Run the automated test suite to ensure the environment is correctly configured:
```bash
pytest tests/
```

## Security
See [SECURITY.md](SECURITY.md) for vulnerability reporting and our security model.

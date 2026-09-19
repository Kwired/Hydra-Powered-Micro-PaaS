# HydraLite Production Release (v1.0.0)

HydraLite is a high-performance NFT Minting Engine built on Cardano's Hydra L2 scaling solution. It enables ultra-fast, low-cost parallel batch minting by leveraging state channels.

## Architecture
See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for a complete system overview.

## Components
- **Hydra Infrastructure**: Managed via Docker (Cardano Node, Hydra Node, Mithril, Ogmios).
- **CLI / Minting Engine**: High-throughput parallel Python client for building, signing, and submitting transactions to the Hydra Head.
- **REST API**: FastAPI integration for application interactions.
- **Dashboard**: React-based frontend.

## Production System Requirements
The HydraLite stack utilizes full Cardano Nodes, Hydra Nodes, Ogmios, and Mithril. These requirements reflect the resources needed to run the complete production stack (mainnet/preprod).

**Hardware**
- **CPU**: 
  - Minimum: 4 cores
  - Recommended: 8 cores
  - Architecture: amd64 / arm64
- **RAM**: 
  - Minimum: 16 GB (required for Cardano node operations)
  - Recommended: 32 GB
- **Storage**: 
  - Minimum: 150 GB (testnet/preprod)
  - Recommended: 500 GB NVMe (mainnet chain data + Hydra state)
  - Expected blockchain/node data requirements: ~100GB+ for Cardano db, ~10GB for Mithril, ~10GB for Docker images.
- **Network**:
  - Minimum bandwidth: 100 Mbps
  - Recommended bandwidth: 1 Gbps
  - Required inbound ports: 5001 (Hydra P2P), 4001 (Hydra API - optional if proxied), 6001 (Metrics - optional)
  - Required outbound connectivity: Standard internet ports (TCP 80, 443, Cardano network ports)

**Software**
- OS: Linux (Ubuntu 22.04+ recommended)
- Docker: v24.0+
- Docker Compose: v2.20+
- Python: 3.11+
- Cardano Node: 10.5.4
- Ogmios: latest (v6.x)
- Hydra Node: 1.2.0
- Mithril Client: latest

## Development Requirements
For development or lightweight testing (e.g., connecting to a remote node or running a partial stack):

- **CPU**: 2 cores minimum
- **RAM**: 8 GB minimum
- **Storage**: 50 GB minimum
- **OS**: Linux, macOS, or Windows (via WSL2)
- **Docker**: v24.0+
- **Other dependencies**: Python 3.11, Git

## Docker Deployment

The project utilizes a multi-container Docker architecture leveraging official upstream images alongside our custom application image.

- **Upstream Images**: Cardano Node, Ogmios, Hydra, Mithril.
- **Application Image**: `hydralite`

**Application Image Details**
- **Image name**: `hydralite`
- **Image version**: `v1.0.0`
- **Base image**: `python:3.11-slim`
- **Architecture**: `amd64` / `arm64`
- **Build command**: `docker build -t hydralite:v1.0.0 .`
- **Run command**: `docker run --rm -it hydralite:v1.0.0 bash`
- **Required environment variables**: `HYDRA_API_URL`, `CARDANO_NETWORK`
- **Required volumes**: None for the base CLI, though `keys/` must be mapped for transaction signing.
- **Required ports**: None exposed by default (CLI tool).

*Note: For the security audit, we recommend a **Build-only** strategy where the TxPipe team can deterministically reproduce the image from the audited source repository rather than relying on a pre-published public image.*

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

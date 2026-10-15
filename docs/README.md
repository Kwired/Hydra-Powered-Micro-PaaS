# HydraLite Documentation

HydraLite is an open-source Layer 2 Micro-PaaS middleware built for the Cardano blockchain. It packages `cardano-node`, `hydra-node`, `ogmios`, and an automated scaling daemon into a coordinated Docker Compose topology, exposing standard REST and WebSocket interfaces for off-chain state channel execution.

The goal of the project is simple: let developers run low-latency micro-transactions, bulk NFT mints, and state channel operations without having to manage Haskell dependencies, raw Plutus scripts, or manual UTXO balance tracking.

---

## Documentation Index

| Topic | Description | File |
|:---|:---|:---|
| **Architecture** | Component topology, L1/L2 message flow, UTXO fuel model, and autoscaler mechanics | [GitBook_Architecture.md](GitBook_Architecture.md) |
| **Setup & Installation** | Step-by-step local and server deployment using Docker Compose and Mithril snapshots | [GitBook_Setup_Guide.md](GitBook_Setup_Guide.md) |
| **API Reference** | Full specification of `/pay`, `/verify`, metrics streams, and persistent gaming WebSockets | [GitBook_API_Reference.md](GitBook_API_Reference.md) |
| **Mainnet Playbook** | Pre-flight security checklists, BYOK key generation, firewall rules, and head lifecycle management | [Mainnet_Deployment_Playbook.md](Mainnet_Deployment_Playbook.md) |
| **Contributor Guidelines** | Template folder structure, asynchronous coding standards, pytest test suite requirements | [CONTRIBUTING_TEMPLATES.md](CONTRIBUTING_TEMPLATES.md) |
| **Mainnet Showcase** | 15 verified third-party templates and deployments maintaining 30-day uptime records (≥ 98%) | [Mainnet_Showcase.md](Mainnet_Showcase.md) |
| **Security & Audit** | Formal container security assessment and verification attestation by Kush Innovation Labs | [Security_Audit.md](Security_Audit.md) |

---

## System Requirements

Before running the stack, verify that your host system meets the minimum hardware allocations. Running a full Cardano relay alongside a Hydra state channel node requires dedicated RAM:

- **OS**: Ubuntu 22.04 LTS (recommended) or any modern Linux x86_64 distribution.
- **Memory**: Minimum 16 GB RAM (32 GB recommended). If you have less than 16 GB, the Linux OOM killer will terminate `cardano-node` during ledger replay (exit code 137).
- **Disk**: 150 GB for Preprod testnet, 500 GB NVMe SSD for Mainnet. High I/O throughput is mandatory for slot synchronization.
- **Docker**: Engine version 24.0 or newer with Docker Compose plugin v2.20+.

---

## Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/Kwired/Hydra-Powered-Micro-PaaS.git
cd Hydra-Powered-Micro-PaaS
git checkout v1.0.0
```

### 2. Configure environment variables
```bash
cp .env.example .env
```

Review `.env` and verify the network target:
```ini
CARDANO_NETWORK=preprod
ALLOWED_ORIGINS=http://localhost:3000
HYDRA_API_URL=ws://hydra-node:4001
```

### 3. Launch the stack
```bash
# Optional: bootstrap blockchain data with Mithril (saves ~20 hours of L1 sync)
docker compose --profile init run --rm mithril-client

# Start core services in background
docker compose up -d
```

### 4. Verify system health
```bash
curl -s http://localhost:8000/health | jq .
```
Expected output:
```json
{
  "status": "ok",
  "service": "hydra-micro-paas",
  "version": "1.0.0"
}
```

---

## Documentation Feedback & Test User Survey

We actively collect feedback from Cardano developers to keep these guides accurate, clear, and easy to follow.

If you deployed HydraLite or reviewed these guides, please take two minutes to complete our feedback questionnaire:  
👉 **[HydraLite Documentation Clarity Survey](https://forms.gle/hydralite-docs-feedback)**

---

## Source & Maintenance

- **Source Code**: [https://github.com/Kwired/Hydra-Powered-Micro-PaaS](https://github.com/Kwired/Hydra-Powered-Micro-PaaS)
- **Container Registry**: `ghcr.io/kwired/hydralite:v1.0.0`
- **Security Audit**: Zero open vulnerabilities confirmed by Kush Innovation Labs.

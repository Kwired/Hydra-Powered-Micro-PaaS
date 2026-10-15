# Setup & Installation Guide

This guide covers provisioning a fresh host and running the HydraLite v1.0.0 stack using Docker Compose.

---

## Hardware & Environment Prerequisites

Running a Cardano relay node alongside the Hydra Layer 2 daemon requires sufficient memory and sustained disk I/O.

| Resource | Minimum | Recommended Production | Notes |
|:---|:---|:---|:---|
| **CPU** | 4 cores (x86_64 or arm64) | 8 cores | High clock speed preferred for cryptographic validation |
| **RAM** | 16 GB | 32 GB | The Cardano ledger cache consumes ~12 GB during replay |
| **Disk** | 150 GB | 500 GB NVMe | Must be SSD or NVMe; HDD cannot keep up with slot sync |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 22.04 / Debian 12 | Kernel 5.15+ |
| **Docker** | Engine 24.0+ | Engine 26.0+ | Docker Compose plugin v2.20+ |

Verify available memory and disk space before starting:
```bash
free -h
df -h /var/lib/docker
```

---

## 1. Clone the Codebase

```bash
git clone https://github.com/Kwired/Hydra-Powered-Micro-PaaS.git
cd Hydra-Powered-Micro-PaaS
git checkout v1.0.0
```

---

## 2. Environment Configuration

Create your `.env` configuration file from the template:

```bash
cp .env.example .env
```

Open `.env` in your text editor:

```ini
# Target Cardano network: "preprod" for testing, "mainnet" for production
CARDANO_NETWORK=preprod

# Restrict CORS to your front-end domain (do not use * in production)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Hydra WebSocket URL (internal Docker network bridge)
HYDRA_API_URL=ws://hydra-node:4001
```

---

## 3. Key Generation (BYOK Model)

HydraLite follows a Bring Your Own Keys (BYOK) architecture. You generate the cryptographic keys on the host machine; the API middleware never has access to the private signing keys.

Create the key directory on the host:
```bash
mkdir -p keys
chmod 700 keys
```

Generate Cardano Layer 1 payment keys:
```bash
docker run --rm -v $(pwd)/keys:/keys \
  ghcr.io/intersectmbo/cardano-node:10.5.4 \
  cardano-cli address key-gen \
  --verification-key-file /keys/cardano.vk \
  --signing-key-file /keys/cardano.sk
```

Generate Hydra protocol signing keys:
```bash
docker run --rm -v $(pwd)/keys:/keys \
  ghcr.io/cardano-scaling/hydra-node:1.2.0 \
  gen-hydra-key --output-file /keys/hydra
```

Verify that ownership and file permissions are hardened:
```bash
chmod 400 keys/*.sk
ls -la keys/
```

Expected output:
```
-r-------- 1 user user ... cardano.sk
-rw-r--r-- 1 user user ... cardano.vk
-r-------- 1 user user ... hydra.sk
-rw-r--r-- 1 user user ... hydra.vk
```

---

## 4. Pull the Audited Release Image

In production environments, always pull by image digest rather than mutable floating tags (`:latest`) to guarantee supply chain integrity:

```bash
docker pull ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2
```

Tag it locally for Docker Compose resolution:
```bash
docker tag ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2 ghcr.io/kwired/hydralite:v1.0.0
```

---

## 5. Bootstrap Blockchain Data via Mithril

Syncing the Cardano blockchain from genesis block 0 can take several days. To bootstrap in under 30 minutes, download a certified snapshot using the Mithril client container:

```bash
docker compose --profile init run --rm mithril-client
```

This populates `./node-db` with verified immutable ledger chunks. Once the download completes, the `mithril-client` container exits.

---

## 6. Start the Service Stack

Start all background containers:

```bash
docker compose up -d
```

Verify the status of all services:
```bash
docker compose ps
```

Expected container table:
```
NAME                    IMAGE                               COMMAND                  SERVICE                 STATUS
hydralite-cardano-node  intersectmbo/cardano-node:10.5.4    "run"                    cardano-node            Up (healthy)
hydralite-ogmios        cardanosolutions/ogmios:latest      "--host 0.0.0.0 ..."     ogmios                  Up
hydralite-hydra-node    cardano-scaling/hydra-node:1.2.0    "--node-id 314 ..."      hydra-node              Up (healthy)
hydralite-api           kwired/hydralite:v1.0.0             "uvicorn api.main:app"   hydralite-api           Up (healthy)
hydralite-autoscaler    kwired/hydralite:v1.0.0             "python autoscaler/m…"   hydralite-autoscaler    Up
```

---

## 7. Health Verification

Test the FastAPI healthcheck endpoint:
```bash
curl -i http://localhost:8000/health
```

Expected response:
```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok","service":"hydra-micro-paas","version":"1.0.0"}
```

Check the node sync progress:
```bash
docker compose exec cardano-node cardano-cli query tip --testnet-magic 1
```

Once `syncProgress` reports `"100.00"`, the node is fully synchronized and ready to open a Hydra Head.

---

## Operational Notes & Troubleshooting

### Node Exits with Code 137 (OOM Killer)
If `cardano-node` terminates suddenly during startup, check the host kernel ring buffer:
```bash
sudo dmesg -T | grep -i -E "oom|killed process"
```
If you see `Out of memory: Killed process ... (cardano-node)`, increase system swap space or allocate more RAM to the Docker daemon.

### Node Socket Not Found
If `ogmios` or `hydra-node` log `Network.Socket.connect: does not exist (/ipc/node.socket)`, `cardano-node` has not completed its initial database validation. Wait 60–90 seconds for the socket file to be created.

### Inspecting Service Logs
```bash
# View API requests and WebSocket events
docker compose logs -f hydralite-api

# View Hydra consensus and snapshot logs
docker compose logs -f hydra-node
```

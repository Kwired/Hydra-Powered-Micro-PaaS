# Mainnet Deployment Playbook

This playbook outlines the operational procedures, security controls, and verification steps required to deploy HydraLite v1.0.0 on Cardano Mainnet.

---

## Pre-Deployment Checklist

Before committing funds to a Mainnet Hydra Head, verify each item:

- [ ] **Dedicated Host**: Bare-metal or dedicated cloud instance with at least 8 vCPUs, 32 GB RAM, and 500 GB NVMe storage.
- [ ] **Firewall**: Default deny on all ingress traffic. Only SSH (`22/tcp`), Hydra P2P (`5001/tcp`), and HTTPS/API (`8000/tcp` or `443` via reverse proxy) are exposed.
- [ ] **Port Isolation**: Ports `4001` (Hydra Admin API) and `1338` (Ogmios) must remain completely blocked from external networks.
- [ ] **Image Digest Enforcement**: The deployment configuration references the verified image digest `ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2`.
- [ ] **CORS Restrictions**: `ALLOWED_ORIGINS` in `.env` is explicitly set to production domains. Never leave wildcard `*` active on mainnet.
- [ ] **TLS/SSL Proxy**: Production API endpoints terminate SSL through Nginx, Caddy, or Cloudflare before forwarding to the container.

---

## 1. Host Hardening & Firewall Setup

On your Ubuntu 22.04 LTS host:

```bash
# Update base system
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl ufw jq git

# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 5001/tcp comment 'Hydra P2P'
sudo ufw allow 8000/tcp comment 'HydraLite API Gateway'
sudo ufw enable
```

Confirm rule table:
```bash
sudo ufw status verbose
```

---

## 2. Docker & Compose Installation

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

---

## 3. Cryptographic Key Generation (BYOK)

Generate production Cardano and Hydra keys on the server. Store keys outside of version control:

```bash
mkdir -p ~/hydralite-mainnet/keys
cd ~/hydralite-mainnet
chmod 700 keys

# Generate Cardano L1 payment credentials
docker run --rm -v $(pwd)/keys:/keys \
  ghcr.io/intersectmbo/cardano-node:10.5.4 \
  cardano-cli address key-gen \
  --verification-key-file /keys/cardano.vk \
  --signing-key-file /keys/cardano.sk

# Derive the payment address
docker run --rm -v $(pwd)/keys:/keys \
  ghcr.io/intersectmbo/cardano-node:10.5.4 \
  cardano-cli address build \
  --payment-verification-key-file /keys/cardano.vk \
  --mainnet \
  --out-file /keys/cardano.addr

# Generate Hydra protocol credentials
docker run --rm -v $(pwd)/keys:/keys \
  ghcr.io/cardano-scaling/hydra-node:1.2.0 \
  gen-hydra-key --output-file /keys/hydra

# Enforce least-privilege permissions
chmod 400 keys/*.sk
```

Print and verify the payment address:
```bash
cat keys/cardano.addr
```

---

## 4. Mainnet Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Set the production variables:
```ini
CARDANO_NETWORK=mainnet
ALLOWED_ORIGINS=https://app.yourdomain.com
HYDRA_API_URL=ws://hydra-node:4001
LOG_LEVEL=INFO
```

---

## 5. Mainnet Ledger Synchronization

To avoid multi-day historical chain synchronization, bootstrap using the Mithril mainnet client:

```bash
docker compose --profile init run --rm mithril-client
```

Once Mithril completes, boot the background services:

```bash
docker compose up -d
```

Monitor sync progress until fully caught up to tip:
```bash
docker compose exec cardano-node cardano-cli query tip --mainnet
```

Wait until `"syncProgress": "100.00"` before proceeding to head initialization.

---

## 6. Head Lifecycle Management

### Initializing the Head
Fund the payment address with sufficient ADA for the commit transaction and gas fees, then execute:

```bash
docker compose run --rm hydralite-cli python -m cli.main init-head
```

The CLI constructs and signs the `InitTx` on Layer 1 to open the state channel.

### Committing Funds to the Head
Commit the desired UTXO batch into the state channel:

```bash
docker compose run --rm hydralite-cli python -m cli.main commit --amount-ada 100
```

Once all participants commit, the head state changes to `Open`. Off-chain transactions can now be submitted through `POST /api/v1/pay`.

---

## 7. Head Closure & Contestation Window

Closing a Hydra Head moves final balances back to Layer 1. This process requires strict attention to the on-chain contestation period.

### Close Command
```bash
docker compose run --rm hydralite-cli python -m cli.main close
```

### Contestation Window Requirement
When a head is closed, an on-chain contestation timer begins (configured in protocol parameters, typically several hours on mainnet).

> **Critical Notice**: The `cardano-node` and `hydra-node` containers must remain running and connected to the network throughout the entire contestation period. If a counterparty submits an invalid or outdated snapshot, your node must be online to post a contestation transaction.

### Finalizing (Fanout)
Once the contestation period has elapsed:

```bash
docker compose run --rm hydralite-cli python -m cli.main fanout
```

The node will broadcast `FanoutTx` to Layer 1, distributing final funds back to participant wallet addresses. Once confirmed on-chain, the head lifecycle is complete.

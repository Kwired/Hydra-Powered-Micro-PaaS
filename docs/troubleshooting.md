# Hydra PaaS Troubleshooting Guide

This guide covers common issues encountered when setting up or running the Hydra NFT Minting Engine.

## 1. Connection Refused `[Errno 111]`

**Error Message:**
```
ERROR:cli.hydra_client:Failed to connect to Hydra API: [Errno 111] Connect call failed ('127.0.0.1', 4001)
ERROR:__main__:Error initializing head: [Errno 111] Connect call failed ('127.0.0.1', 4001)
```

**Cause:**
This typically happens immediately after running `docker compose up -d` (especially after a `down -v` reset). The Hydra Node depends on the Cardano Node, which can take **1-2 minutes** to initialize, verify the database, and create the communication socket (`node.socket`). Until the socket exists, the Hydra Node will crash loop and fail to open its API port (4001).

**Solution:**
Wait for the Cardano Node to fully start.

1.  Check the logs:
    ```bash
    docker compose logs -f cardano-node
    ```
2.  Wait until you see messages indicating the node is syncing or extending the chain (e.g., `Chain extended, new tip...`).
3.  Once the logs stabilize, retry your command:
    ```bash
    python -m cli.main init
    ```

---

## 2. "Socket does not exist" in Logs

**Error Message (in `docker compose logs hydra-node`):**
```
Network.Socket.connect: <socket: 24>: does not exist (No such file or directory)
```

**Cause:**
The Hydra Node container cannot find the `node.socket` file shared by the Cardano Node. This confirms the Cardano Node is still starting up or the volume mount failed.

**Solution:**
Same as above. Wait for the Cardano Node to finish startup.

---

## 3. "No funds found" when Funding

**Error Message:**
```
No funds found at addr_test1...
```

**Cause:**
The local Ogmios instance hasn't seen the transaction from the L1 testnet yet, or the address is incorrect.

**Solution:**
1.  Verify you sent **Testnet ADA** (Preprod network) to the address in `keys/payment.addr`.
2.  Wait 1-2 minutes. Block propagation takes time.
3.  Ensure your local node is synced. Check `docker compose logs -f cardano-node` and compare the slot number/tip with a public explorer like [Preprod Cardanoscan](https://preprod.cardanoscan.io/).

## Mithril Fast-Sync Failures

### Invalid Genesis Verification Key
**Symptom:** `mithril-client` fails with "Invalid genesis verification key" or "Cannot decompress Edwards point".
**Cause:** The preprod network genesis key in `docker-compose.yml` may be outdated or incorrect.
**Solution:**
Use the `scripts/fast_sync.py` script, which dynamically fetches the latest keys from the IOG repository.
```bash
python scripts/fast_sync.py
```
Ensure you have `python3` installed. This script also handles Docker volume permission fixes automatically.

---

## 4. Interpreting Cardano Node Logs

If you are waiting for the node to start, check `docker compose logs -f cardano-node`.

### ⏳ Still Loading (Do NOT run init yet)
If you see these messages, the node is still initializing:
- `Topology: Peer snapshot ... loaded.`
- `Bootstrap peers ... are not compatible ...`
- `Opened db with immutable tip ...`

**Wait** until you see:
- `Opened socket: /ipc/node.socket`
- `Chain extended, new tip ...`

> **Note**: A full reset (`down -v`) deletes the database. Re-syncing the Preprod network can take **15–30 minutes**.

### ⚡ Fix: Fast Sync with Mithril (Recommended)
If the node is stuck syncing from Genesis, manually download a snapshot using the verified Hex Key:

```bash
# 1. Stop the node
docker compose down

# 2. Fix Permissions (Required for Docker Volume)
docker run --rm -v hydra-paas_node-db:/db alpine chmod -R 777 /db

# 3. Download Snapshot (Copy-paste this entire block)
docker compose run --rm mithril-client cardano-db download \
  --download-dir /db \
  --aggregator-endpoint https://aggregator.release-preprod.api.mithril.network/aggregator \
  --genesis-verification-key 7f497ca1068983d5cf75c655b0c7a2f1447b77910de8f331e502f9cdcd27eb2c \
  latest

# 4. Fix Directory Structure (Mithril nests the DB in 'db/')
docker run --rm -v hydra-paas_node-db:/data alpine sh -c "mv /data/db/* /data/ && rmdir /data/db"

# 5. Fix Socket Permissions (Prevent "Permission denied" error)
# Change ownership to the cardano-node user (1000)
docker run --rm -v hydra-paas_node-ipc:/ipc alpine sh -c "chown -R 1000:1000 /ipc && chmod -R 777 /ipc && rm -f /ipc/node.socket"

# 6. Fix Persistence Permissions (Prevent Hydra Node crash)
docker run --rm -v hydra-paas_hydra-persistence:/persistence alpine chown -R 1000:1000 /persistence

# 7. Restart
docker compose up -d
```

## 5. Minting Fails with "Fee too small"

**Cause:**
The protocol parameters on the network might have changed, or the hardcoded fee estimation (0.2 ADA) is insufficient for the current complex script execution.

**Solution:**
1.  Check `cli/minting.py`.
2.  Increase the `fee` variable in `mint_batch_unique` or `mint_nft`.

---

## 6. Docker Containers Keep Restarting

**Cause:**
Corrupted database state or configuration mismatch.

**Solution: Factory Reset**
Wipe everything and start fresh.
```bash
docker compose down -v
docker compose up -d
```
*Note: This deletes the Head state and requires you to re-initialize and re-fund.*

# Comprehensive Hydra Node Troubleshooting Guide

This guide documents the thorough troubleshooting steps required to resolve connection, permission, and state issues when setting up the Hydra Head on a local Preprod network.

## 1. Connection Refused `[Errno 111]`

**Symptoms:**
- `Failed to connect to Hydra API: [Errno 111] Connect call failed`
- Hydra node logs show: `Network.Socket.connect: <socket: 24>: does not exist`

**Cause:**
The Cardano Node has not finished initializing, so the `/ipc/node.socket` file does not exist yet. The Hydra node cannot start without it.

**Solution:**
1.  **Check Cardano Logs:**
    ```bash
    docker compose logs -f cardano-node
    ```
2.  **Wait for Sync:** Look for "Chain extended, new tip" messages.
3.  **Wait for Socket:** Ensure the log says `Opened socket: /ipc/node.socket`.

---

## 2. Socket Permission Denied

**Symptoms:**
- Cardano Node crashes with `Network.Socket.bind: permission denied`
- Hydra Node crashes with `Permission denied` accessing `/ipc/node.socket`

**Cause:**
Docker named volumes (`node-ipc`) are often owned by `root`, while the `cardano-node` container runs as user `1000`.

**Solution:**
We switched to using a **host-mounted directory** (`./ipc`) instead of a named volume to control permissions more easily.

1.  **Update `docker-compose.yml`:**
    ```yaml
    volumes:
      - ./ipc:/ipc
    ```
2.  **Fix Host Permissions:**
    ```bash
    mkdir -p ipc
    chmod 777 ipc
    ```
3.  **Restart Containers:**
    ```bash
    docker compose up -d
    ```

---

## 3. Persistence Permission Errors

**Symptoms:**
- Hydra Node crashes immediately.
- Logs show: `hydra-node: /persistence/state: openFile: permission denied`

**Cause:**
The `hydra-persistence` volume was created by `root` (likely during a previous run) and cannot be written to by the `hydra-node` user.

**Solution:**
Reset ownership of the volume to user `1000`:
```bash
docker run --rm -v hydra-paas_hydra-persistence:/persistence alpine chown -R 1000:1000 /persistence
```

---

## 4. Mithril Fast Sync Issues

**Symptoms:**
- Node starts syncing from Genesis (0%) despite running Mithril download.
- `node-db` volume is empty or contains a nested `db/` folder.

**Cause:**
Mithril Client downloads files into a `db/` subdirectory, but the Cardano Node expects them in the root of `/data`.

**Solution:**
1.  **Download Snapshot:**
    (Run standard `mithril-client` command)
2.  **Fix Directory Structure:**
    Move files from `/data/db/` to `/data/`:
    ```bash
    docker run --rm -v hydra-paas_node-db:/data alpine sh -c "mv /data/db/* /data/ && rmdir /data/db"
    ```
3.  **Fix DB Permissions:**
    ```bash
    docker run --rm -v hydra-paas_node-db:/data alpine chmod -R 777 /data
    ```

---

## 5. "CommandFailed: Initial" (Head Already Initialized)

**Symptoms:**
- Running `init` fails with a timeout.
- Logs show: `CommandFailed` tag with `Initial` state.
- `fund` command fails with `FailedToDraftTxNotInitializing`.

**Cause:**
The Hydra Node has a stale state in `/persistence` from a previous failed run. It thinks it's already initializing, but the on-chain state doesn't match.

**Solution:**
Wipe the persistence directory to force a clean start:
```bash
docker compose stop hydra-node
docker run --rm -v hydra-paas_hydra-persistence:/persistence alpine sh -c "rm -rf /persistence/*"
docker compose start hydra-node
```

---

## 6. "NotEnoughFuel" (Collateral Issue)

**Symptoms:**
- `fund` command fails.
- Logs show: `NotEnoughFuel { failingTx = ... }`.

**Cause:**
The Hydra Node requires **two separate UTXOs**:
1.  One to commit to the Head (the funds you want to use).
2.  One to pay for the transaction fees (Collateral/Fuel).

If you have all your funds in a single UTXO, the node tries to commit it and has nothing left for fees.

**Solution:**
Split your funds into multiple UTXOs.

1.  **Check UTXOs:**
    ```bash
    cardano-cli query utxo --address $(cat keys/payment.addr) ...
    ```
2.  **Send Funds to Yourself:**
    Use `cardano-cli transaction build` to send 5000 ADA to yourself. This creates a main output (5000 ADA) and a change output (remainder).
3.  **Retry Fund:**
    Now `hydra-node` will pick the 5000 ADA UTXO to commit and use the change UTXO for fuel.

---

## 7. Docker Restart Loop

**Symptoms:**
- `hydra-node` keeps restarting every few seconds.

**Solution:**
1.  Check logs: `docker compose logs hydra-node`
2.  Most likely a permission error (See #2 or #3).
3.  If "Handshake failed", the Cardano Node isn't ready (See #1).

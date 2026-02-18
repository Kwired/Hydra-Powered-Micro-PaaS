# Comprehensive Hydra Node Troubleshooting Guide

So, Hydra is acting up. It happens. This guide covers the common issues we hit when setting up the Head on a local Preprod network and how to fix them without pulling your hair out.

## 1. Connection Refused `[Errno 111]`

**Symptoms:**
- `Failed to connect to Hydra API: [Errno 111] Connect call failed`
- Hydra node logs show: `Network.Socket.connect: <socket: 24>: does not exist`

**Cause:**
The Cardano Node is still booting up. It hasn't created the `/ipc/node.socket` file yet, and the Hydra node is waiting for it.

**Solution:**
1.  **Check Cardano Logs:**
    ```bash
    docker compose logs -f cardano-node
    ```
2.  **Wait for Sync:** Look for "Chain extended, new tip" messages.
3.  **Wait for Socket:** Keep an eye out for `Opened socket: /ipc/node.socket`. Once you see that, you're good.

---

## 2. Socket Permission Denied

**Symptoms:**
- Cardano Node crashes with `Network.Socket.bind: permission denied`
- Hydra Node crashes with `Permission denied` accessing `/ipc/node.socket`

**Cause:**
Docker permissions are annoying. The named volume `node-ipc` is often owned by `root`, but the `cardano-node` container runs as user `1000`. They don't get along.

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
The `hydra-persistence` volume was probably created by `root` (maybe from an earlier run with different settings), so now the `hydra-node` user can't write to it.

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
The Hydra Node has some stale junk in `/persistence` from a previous failed run. It thinks it's already initializing, but the blockchain says otherwise.

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
The Hydra Node needs **two separate UTXOs**:
1.  One to commit to the Head (your actual funds).
2.  One to pay for the transaction fees (Fuel).

If you have one giant UTXO, the node tries to commit it and realizes it has zero change left to pay for the network fee.

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
3.  If "Handshake failed", the Cardano Node isn't ready (See #1).

---

## 8. "BadInputsUTxO" during Batch Minting

**Symptoms:**
- Batch minting starts fine but fails halfway through.
- Logs show: `ApplyTxError (BadInputsUTxO ...)`

**Cause:**
You're going too fast. If you submit transactions faster than the Hydra Head can confirm them, you end up trying to spend an output that doesn't exist yet (because the previous tx hasn't confirmed).

**Solution:**
Use **Sequential Confirmation** (Turbo Mode).
- Don't just spray and pray.
- Wait for `TxValid` for Transaction N before sending Transaction N+1.
- Our `mint_10k_turbo` engine does this for you.

---

## 9. "OutputTooSmallUTxO" (MinUTXO Limits)

**Symptoms:**
- Transaction build fails with `OutputTooSmallUTxO`.

**Cause:**
Cardano requires every UTXO to hold a minimum amount of ADA (lovelace) based on its size (bytes).
- A simple UTXO needs ~1 ADA.
- A UTXO holding **50-100 native assets** requires significant storage.
- A batch of 50 assets with 3 ADA was found to trigger `BabbageOutputTooSmallUTxO` on Preprod.

**Solution:**
- Ensure your "Fuel" or "change" outputs have at least **10 ADA** when carrying large asset bundles.
- We updated our minting logic to allocate **10,000,000 lovelace** for the asset-carrying output.

---

## 10. "NotEnoughFuel" (Fragmentation)

**Symptoms:**
- You have 100 ADA in the Head, but cannot mint.

**Cause:**
Hydra needs to *spend* a UTXO to drive a transaction. If you have one giant 100 ADA UTXO, it can only drive one transaction at a time. Parallel workers will fight over it.

**Solution:**
**UTXO Fragmentation.**
- Split your large UTXO into many smaller UTXOs (e.g., 10 UTXOs of 10 ADA each).
- This allows 10 transactions to proceed in parallel.
- Our `manual_e2e.py` script includes a fragmentation step before minting.

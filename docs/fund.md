# Manual Funding Guide

This guide documents the manual process for funding the Hydra Head's internal wallet (the "L1" wallet used for commits). This is necessary when the automated `fund` command fails, typically due to having only a single large UTXO that cannot be simultaneously committed and used for fees.

## Prerequisites

- **Docker Services Running**: Ensure `cardano-node` is up.
- **Keys**: Ensure `keys/payment.addr` and `keys/cardano.sk` exist.

## The Problem: "NotEnoughFuel"

The Hydra Head requires:
1.  **Commitment UTXO**: A specific UTXO to lock into the Head (e.g., 4000 ADA).
2.  **Fee UTXO**: A *separate* UTXO to pay for the L1 commit transaction fees (e.g., 5-10 ADA).

If your wallet has only **one** large UTXO (e.g., 5000 ADA), you cannot use it for *both* commitment and fees in the same transaction easily without advanced coin selection. The solution is to **split** the large UTXO into two.

---

## Step-by-Step Instructions

All commands are run from the project root.

### 1. set Variables
Set the address variable for easier copy-pasting:
```bash
export PAYMENT_ADDR=$(cat keys/payment.addr)
echo "Address: $PAYMENT_ADDR"
```

### 2. Query Current UTXOs
Find your available funds:
```bash
docker compose exec cardano-node cardano-cli query utxo \
    --address $PAYMENT_ADDR \
    --testnet-magic 1 \
    --socket-path /ipc/node.socket
```
**Example Output:**
```
                           TxHash                                 TxIx        Amount
--------------------------------------------------------------------------------------
07487fc4feaa692ed1506263db8005998b900ffeaccdf8e005bc841eda13526c     1        4886809932 lovelace + TxOutDatumNone
```
*Note the `TxHash` and `TxIx` (index) of your large UTXO.*

### 3. Build "Split" Transaction
We will take the input UTXO and create two outputs:
- **Output 1**: 4000 ADA (For future commitment).
- **Change**: The remainder (automatically calculated) will serve as "Fuel" for fees.

Replace `YOUR_TX_HASH` and `YOUR_TX_IX` with the values from Step 2.

```bash
docker compose exec cardano-node cardano-cli conway transaction build \
    --testnet-magic 1 \
    --socket-path /ipc/node.socket \
    --change-address $PAYMENT_ADDR \
    --tx-in "YOUR_TX_HASH#YOUR_TX_IX" \
    --tx-out "$PAYMENT_ADDR+4000000000" \
    --out-file /tmp/split.raw
```

### 4. Sign the Transaction
Sign the raw transaction using your secret key (`cardano.sk` mounted at `/keys/cardano.sk`).

```bash
docker compose exec cardano-node cardano-cli conway transaction sign \
    --tx-body-file /tmp/split.raw \
    --signing-key-file /keys/cardano.sk \
    --testnet-magic 1 \
    --out-file /tmp/split.signed
```

### 5. Submit the Transaction
Broadcast the signed transaction to the network.

```bash
docker compose exec cardano-node cardano-cli conway transaction submit \
    --tx-file /tmp/split.signed \
    --testnet-magic 1 \
    --socket-path /ipc/node.socket
```

### 6. Verify New UTXOs
Wait for the next block (approx 1-20 seconds) and query again.

```bash
docker compose exec cardano-node cardano-cli query utxo \
    --address $PAYMENT_ADDR \
    --testnet-magic 1 \
    --socket-path /ipc/node.socket
```

**Expected Result:**
You should now see **two** UTXOs:
1.  One with `4000000000` lovelace (The Commitment).
2.  One with `~886000000` lovelace (The Fuel).

### 7. Run Fund Command
Now the automated tool can safely select the largest UTXO for commitment, leaving the other for fees.

```bash
PYTHONPATH=. .venv/bin/python -m cli.main fund $PAYMENT_ADDR
```

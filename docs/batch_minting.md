# Batch Minting Guide: Turbo Mode

This guide explains how to efficiently mint large collections (up to 10k+) using the **Hydra Head Turbo Minting Engine**.

## Overview

Traditional "fire-and-forget" batching usually fails because the network gets congested or state gets messy. Our **Turbo Mode** (Parallel Minting) uses **Concurrent Transaction Chaining**. Basically, we run multiple distinct chains at once so they don't step on each other's toes. This gets us massive throughput (~700+ TPS potential) with zero failed transactions.

### The Pipeline (Parallel Mode)

1.  **Phase 1: Split Funds**: We take your big input UTXO and split it into 4 equal chunks. One for each worker.
2.  **Phase 2: Parallel Build**:
    *   4 workers run at the same time.
    *   Each worker builds its own chain of transactions (e.g., 25 txs each).
    *   This quadruples the build speed, which is usually the slow part.
3.  **Phase 3: Submit**: All chains get fired at the Hydra Head. Since they spend different UTXOs, they process in parallel without fighting for resources.

## Prerequisites

*   A running Hydra Head (initialized and open).
*   **Fuel:** At least 10-20 ADA committed to the head.
*   **Fragmentation:** Ideally split your funds into a few UTXOs if you plan to run multiple independent chains (though Turbo Mode runs a single high-speed chain).

## Usage

### via CLI (Automated)

The easiest way is to use the `manual_e2e.py` script, which handles the entire lifecycle:

```bash
# Run the full benchmark
python manual_e2e.py
```

### via Library

```python
from cli.hydra_client import HydraClient
from cli.minting import MintingEngine

async def run():
    client = HydraClient()
    await client.connect()
    
    engine = MintingEngine(client)
    
    # Mint 10,000 NFTs in batches of 100
    valid, time = await engine.mint_10k_turbo(
        prefix="MyCollection", 
        count=10000, 
        batch_size=100
    )
    
    print(f"Done! {valid} batches confirmed in {time}s")
```

## Performance Tuning

*   **Batch Size:** We found **50 NFTs per tx** to be the sweet spot.
    *   *Too small (10)* = Too much overhead per tx.
    *   *Too large (100+)* = Hits `maxValueSize` limits or `OutputTooSmall` errors if UTXO is small.
*   **MinUTXO:** Ensure you allocate **10 ADA** for outputs carrying 50 assets (to satisfy ledger rules).

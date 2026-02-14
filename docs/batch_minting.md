# Batch Minting Guide: Turbo Mode

This guide explains how to efficiently mint large collections (up to 10k+) using the **Hydra Head Turbo Minting Engine**.

## Overview

Traditional "fire-and-forget" batching often fails due to network congestion or state contention. Our **Turbo Mode** uses **Transaction Chaining** with **Sequential Confirmation** to achieve high throughput (~180 TPS) with 100% reliability.

### The Pipeline

1.  **Phase 1: Build (Offline)**
    *   Constructs a chain of 100+ transactions offline.
    *   Each transaction consumes the "fuel" output of the previous one.
    *   Each transaction mints a batch of 100 NFTs.
    *   This happens instantly without network interaction.

2.  **Phase 2: Submit (Online)**
    *   Submits Transaction 1 to Hydra.
    *   Waits for `TxValid` confirmation (milliseconds).
    *   Submits Transaction 2 (which depends on Tx 1).
    *   Repeats until finished.

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

*   **Batch Size:** We found **100 NFTs per tx** to be the sweet spot.
    *   *Too small (10)* = Too much overhead per tx.
    *   *Too large (500)* = Hits `maxValueSize` limits (Cardano L1 protocol limit, which Hydra respects).
*   **MinUTXO:** Ensure you allocate ~7 ADA for outputs carrying 100 assets.

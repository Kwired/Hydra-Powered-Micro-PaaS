# Batch Minting Guide

This guide explains how to efficiently mint large collections (up to 100k) using the Hydra Head.

## Prerequisites
- A running Hydra Head (initialized and open).
- Sufficient funds committed to the Head.
- A prepared metadata set.

## Process
1.  **Initialize Head**:
    ```bash
    python cli/main.py init --network preview
    ```
2.  **Fund Head**:
    ```bash
    python cli/main.py fund 100000000 # 100 ADA
    ```
3.  **Batch Mint**:
    Use the `mint` command with the `--count` argument. The engine automatically batches transactions to maximize throughput.
    ```bash
    python cli/main.py mint --count 10000
    ```

## Performance Tuning
- **Parallelism**: The engine uses default concurrency. Adjust `MINTING_WORKERS` env var to increase parallelism.
- **Batch Size**: Default transaction batch size is 100. Adjust `BATCH_SIZE` env var.

## verifying Results
Logs are written to `minting.log`. Check this file for detailed status of each batch.

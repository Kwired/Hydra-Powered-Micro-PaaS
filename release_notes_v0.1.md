# Milestone 1: NFT Drop Engine Core Components

This release marks the completion of Milestone 1 for the **Hydra-Powered Micro-PaaS**.

## 🚀 Highlights

-   **Throughput**: **1095 transactions per second** (TPS) achieved during verification.
-   **Performance**: Minted **10,000 unique NFTs** in **9.13 seconds**.
-   **Features**:
    -   Full CLI for Hydra lifecycle (`init`, `fund`, `mint`, `close`).
    -   Dockerized environment with Ogmios integration.
    -   Batch minting support with dynamic fee handling.
    -   CIP-25 metadata generation.

## 📦 What's Included

-   `cli/`: Core Python tools.
-   `tests/`: Comprehensive test suite & benchmark scripts.
-   `docs/`: Full documentation (Asset Policy, Batch Minting, Troubleshooting).
-   `docker-compose.yml`: Infrastructure template.

## ✅ Verification Evidence

The following files serve as proof of verification for this milestone:
-   `benchmark_10k.log`: Raw execution log showing 10,000 assets minted in <10s.
-   `docs/performance_report.md`: Detailed performance analysis.

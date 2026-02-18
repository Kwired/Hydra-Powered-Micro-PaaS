# Hydra Powered Micro-PaaS: High-Performance NFT Minting Engine

Welcome to the **Hydra-Powered Micro-PaaS**. We built this to show exactly how fast **Cardano Hydra** state channels can be when you take the gloves off.

The goal was simple: mint **10,000 unique NFTs** without melting the network. The result? **19.3 seconds**. That’s **518 TPS** with 100% success rate.

This repo isn't just a demo—it's a full toolkit. Docker templates, CLI tools, and the exact scripts we used to hit those numbers are all here for you to use.

---

## 🚀 Why This Matters

Cardano L1 is solid, but waiting 20 seconds for a block kills the vibe for high-volume drops. We moved the heavy lifting to a Hydra Head (L2), and here is what happened:

-   **Throughput**: **518 effective TPS**. We minted 10k NFTs across 200 chained transactions.
-   **Speed**: The whole 10k batch finished in **19.3 seconds**.
-   **Cost**: Dirt cheap. We're talking ~0.2 ADA per batch of 50 NFTs.
-   **Tech**: We used **Parallel Transaction Chaining** (4 workers) to saturate the Head without breaking it.

---

## 📦 Release v0.1

This is the first major release, Milestone 1. It packs:

1.  **Docker Setup**: A plug-and-play `docker-compose.yml` that spins up a local Cardano Node, Hydra Node, and Ogmios.
2.  **CLI Tool**: A Python-based CLI (`cli/main.py`) to manage the Hydra lifecycle without touching raw Haskell scripts.
3.  **Test Suite**: 62 passing tests with comprehensive coverage.
4.  **Docs**: Guides on [Asset Policies](docs/asset_policy.md), [Batch Minting](docs/batch_minting.md), and [Troubleshooting](docs/troubleshooting_thorough.md).

---

## 📋 Getting Started

Grab a Linux machine (Ubuntu 20.04+ is solid) or a Mac. If you're on Windows, stick to WSL2 or you're gonna have a bad time.

**Prerequisites:**
-   **Docker** & **Docker Compose** (Crucial).
-   **Python 3.10+**.
-   At least **16GB RAM** (Cardano nodes get hungry).

### 1. Installation

Clone the repo and set up your Python environment:

```bash
git clone <repository-url>
cd Hydra-PaaS

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Keys & Crypto

You need keys to sign stuff. We included a helper script to generate them for you:

```bash
chmod +x scripts/generate_keys.sh
bash scripts/generate_keys.sh
```

### 3. Spin it Up

Launch the infrastructure. This starts a local **Preprod** node.

```bash
docker compose up -d
```

> **Heads up:** ⏳ If this is your first time running a node, it needs to sync. This can take 15–30 minutes using Mithril (which we configured automatically). Grab a coffee. You can watch the progress with `docker compose logs -f hydra-node`.

---

## ⚡ Seeing is Believing (The Benchmark)

Once your node is synced, here's how to run the full benchmark.

### 1. Initialize the Head
Tell the Hydra node to get ready.

```bash
python -m cli.main init
```

### 2. Fund It
You need **Testnet ADA** (Preprod). Send some to the address in `keys/payment.addr`. Once verified on-chain, move it into the Head:

```bash
python -m cli.main fund $(cat keys/payment.addr)
```

*(We recommend funding at least 50 ADA to be safe).*

### 3. Mint 10,000 NFTs
This is the big one. We use the turbo minting pipeline with batches of 100 NFTs per transaction.

```bash
python -m cli.main mint --unique --quantity 10000 --batch-size 50
```

Or run the full automated E2E script:

```bash
python manual_e2e.py
```

If all goes well, you'll see something like this:

```text
  ═══ PARALLEL MINT RESULTS ═══
    Phase 1 (Build):  15.2s (200 txs)
    Phase 2 (Submit): 4.1s
    Total Time:       19.3s
    Valid Txs:        200/200
    Invalid Txs:      0
    NFTs Minted:      10000
    Effective TPS:    518.7

╔════════════════════════════════════════════════════════╗
║                  E2E COMPLETE!                        ║
╚════════════════════════════════════════════════════════╝
  Minted:       10000 NFTs
  Mint Time:    19.3s
  Overall Time: 120.5s
```

---

## 🔧 Troubleshooting (The Real Stuff)

Hydra is complex software. Here are the common gotchas we hit so you don't have to:

-   **"No funds found"**: Did you just send the ADA? The local node needs a minute to catch up. Give it a second.
-   **"Socket does not exist"**: The Cardano node is still booting. Be patient.
-   **"NotEnoughFuel"**: This is the classic Hydra error. The node needs *two* UTXOs—one to commit, and one for fees. If you have one giant UTXO, it fails. See the [Extended Troubleshooting Guide](docs/troubleshooting_thorough.md#6-notenoughfuel-collateral-issue) for the fix.

---

## 🧠 Under the Hood

We use **Parallel Transaction Chaining** with 4 concurrent workers.

**Phase 1 (Pre-build):** All 200 transactions are built offline using `cardano-cli` by 4 parallel workers. Each transaction mints 50 NFTs.

**Phase 2 (Submit & Confirm):** Transactions are submitted sequentially to the Hydra Head, waiting for `TxValid` confirmation before submitting the next one. This ensures chained inputs are available.

```mermaid
graph LR
    subgraph Worker 1
        A1[Build Tx 1] --> B1[Build Tx 2] --> C1[...]
    end
    subgraph Worker 2
        A2[Build Tx 1] --> B2[Build Tx 2] --> C2[...]
    end
    Worker 1 -->|Submit| E[Hydra Head]
    Worker 2 -->|Submit| E
```

Check out `cli/minting.py` (`mint_10k_turbo`) for the implementation.

---

## � Performance Report

Verified on **February 18, 2026** — Cardano Preprod testnet, local Docker environment.

| Metric | Target | Actual Result | Status |
| :--- | :--- | :--- | :--- |
| **Total Mint Time** | < 60s | **19.3s** | ✅ **PASS** |
| **Phase 1 (Build)** | — | 15.2s (200 txs) | — |
| **Phase 2 (Submit)** | — | 4.1s | — |
| **Effective TPS** | > 400 | **518 TPS** | ✅ **PASS** |
| **Valid Transactions** | 200/200 | **200/200** | ✅ **PASS** |
| **Invalid Transactions** | 0 | **0** | ✅ **PASS** |
| **Overall E2E Time** | — | 120.5s | — |

**Key observations:**
-   **Zero failures** — all 200 chained transactions accepted without a single `TxInvalid`.
-   **Parallel submission** (4 workers) significantly contributed to the speedup.
-   **Batch Size Optimization** — Reduced to 50 NFTs/tx to avoid `OutputTooSmall` errors.
-   **Fuel management** — Min UTXO increased to 10 ADA per batch.

> 📄 Full report: [performance_report.md](performance_report.md) ・ Full terminal log: [e2e_10k_single_round.log](e2e_10k_single_round.log) ・ Results JSON: [e2e_results.json](e2e_results.json)

---

## 🧪 Test Report

**62 tests passing** (90 total checks including parameterization) across 10 test files.
**Code Coverage:** **96%** (677 lines covered, 29 missed).

```
======================== 90 passed, 2 warnings in 1.66s ========================
```

> 📄 Full test log: [test_suite_log.txt](docs/test_suite_log.txt)
> 📊 Coverage report: [coverage_report.txt](docs/coverage_report.txt)

| Test File | Tests | What It Covers |
| :--- | :---: | :--- |
| `tests/test_cli.py` | 4 | CLI commands: `init`, `fund`, `mint`, `close` |
| `tests/test_cli_extended.py` | 14 | UTXO transforms, fund edge cases, abort, mint scenarios |
| `tests/test_hydra_client.py` | 6 | WebSocket connect, send, receive, commit |
| `tests/test_hydra_client_advanced.py` | 11 | **[NEW]** Wait logic, drain loops, fire-and-forget strategies |
| `tests/test_hydra_error_handling.py` | 11 | Timeouts, HTTP failures, disconnects, UTXO formats |
| `tests/test_minting.py` | 1 | Batch minting call counts with chaining |
| `tests/test_minting_extended.py` | 15 | TxId parsing, metadata, insufficient funds, subprocess errors |
| `tests/test_minting_logic.py` | 1 | 500-asset fragmentation with 2-output chaining model |
| `tests/test_turbo_mint.py` | 8 | **[NEW]** Full 10k turbo pipeline, build/sign/submit failures |
| `tests/test_balance_fund.py` | 8 | **[NEW]** Balance logic, fee calculation, CBOR parsing |
| `tests/test_ogmios_error_handling.py` | 6 | Ogmios connect, query UTXOs, protocol params |
| `test_ogmios.py` | 4 | Ogmios client integration |

### Running the Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
PYTHONPATH=. python -m pytest tests/ test_ogmios.py -v

# Run a specific test file
PYTHONPATH=. python -m pytest tests/test_minting.py -v

# Run with short traceback on failure
PYTHONPATH=. python -m pytest tests/ test_ogmios.py -v --tb=short
```

---

## �📝 License

MIT License. Go wild.

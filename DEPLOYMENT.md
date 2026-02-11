# Deployment Notes

## Requirements
*   **Hardware**: 4+ Cores, 16GB RAM, SSD.
*   **OS**: Linux/macOS (or WSL2).
*   **Network**: Allow outbound traffic to Hydra/Cardano nodes.

## Funding (Testnet)
To run the full 10k benchmark, your wallet needs approximately **100 ADA**:
*   **50 ADA**: Fuel (Locked in Head).
*   **~10 ADA**: Fees (0.2 ADA * 50 batches).
*   **Buffer**: 40 ADA.

## Key Management
The system expects standard cardano-cli keys in `./keys`:
*   `cardano.sk` / `cardano.vk`
*   `payment.addr`
*   `policy.script` (Generated automatically if missing)

## Troubleshooting
*   **"No UTXOs available"**: Head ran out of funds or is not Open.
*   **Log Files**: Check `benchmark_10k.log` for run details.
*   **Node Logs**: `docker compose logs -f hydra-node`

## Rapid Node Sync (Mithril)

To avoid waiting days for the node to sync, use the provided `fast_sync.py` script which utilizes Mithril to download a certified snapshot of the blockchain **including the ledger state**.

```bash
docker compose stop cardano-node
python3 scripts/fast_sync.py
docker compose start cardano-node
```

**Note**: This script automatically handles:
- Fetching correct genesis and ancillary keys.
- Downloading the latest snapshot.
- Fixing volume permissions and structure.

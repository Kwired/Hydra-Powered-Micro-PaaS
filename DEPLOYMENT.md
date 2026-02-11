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

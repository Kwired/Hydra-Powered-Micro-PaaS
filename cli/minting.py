import subprocess
import json
import logging
import asyncio
from typing import Dict, Any, List
from .hydra_client import HydraClient

logger = logging.getLogger(__name__)

POLICY_ID = "b7d525b149829894aa5fa73087d7758c2163c55520c8715652cb8515"
SCRIPT_FILE = "/keys/policy.script"
SK_FILE = "/keys/cardano.sk"
MAGIC = 1

class MintingEngine:
    def __init__(self, hydra_client: HydraClient):
        self.client = hydra_client

    async def mint_nft(self, asset_name: str = "HydraNFT", quantity: int = 1):
        """
        Constructs and submits a transaction to mint an NFT inside the Hydra Head.
        """
        logger.info(f"Attempting to mint {quantity} of {asset_name} ({POLICY_ID})...")
        
        # 1. Fetch current Head UTXOs
        utxos = await self.client.get_utxos()
        if not utxos:
            logger.error("No UTXOs available in the Head to pay for minting fees/collateral.")
            return False

        # 2. Select a UTXO to spend
        # For simplicity, pick the first available UTXO
        tx_in = list(utxos.keys())[0]
        utxo_info = utxos[tx_in]
        
        # Handle value structure which might be simple int or dict
        val = utxo_info['value']
        if isinstance(val, dict):
             lovelace = val.get('lovelace', 0)
        else:
             lovelace = val
             
        address = utxo_info['address']
        logger.info(f"Selected input: {tx_in} ({lovelace})")

        # 3. Construct the Minting Transaction using cardano-cli inside docker
        # Output: Same address, same lovelace (fees 0), plus minted token
        # Asset Name must be hex encoded
        asset_name_hex = asset_name.encode('utf-8').hex()
        fq_asset = f"{POLICY_ID}.{asset_name_hex}"
        mint_str = f"{quantity} {fq_asset}"
        
        # Build Raw Tx
        # Ledger requires minimum fees (detected ~170k lovelace).
        fee = 200000
        output_lovelace = lovelace - fee
        
        cmd_build = [
            "docker", "compose", "exec", "cardano-node",
            "cardano-cli", "latest", "transaction", "build-raw",
            "--tx-in", tx_in,
            "--tx-out", f"{address}+{output_lovelace}+{mint_str}",
            "--mint", mint_str,
            "--mint-script-file", SCRIPT_FILE,
            "--fee", str(fee),
            "--invalid-hereafter", "200000000", # TODO: Get tip + TTL
            "--out-file", "/tmp/tx.raw"
        ]
        
        try:
            logger.info("Building raw transaction...")
            subprocess.run(cmd_build, check=True, capture_output=True)
            
            # Sign
            logger.info("Signing transaction...")
            cmd_sign = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "latest", "transaction", "sign",
                "--tx-body-file", "/tmp/tx.raw",
                "--signing-key-file", SK_FILE,
                "--testnet-magic", str(MAGIC),
                "--out-file", "/tmp/tx.signed"
            ]
            subprocess.run(cmd_sign, check=True, capture_output=True)

            # Read Signed Tx CBOR
            logger.info("Reading signed transaction...")
            cmd_cat = ["docker", "compose", "exec", "cardano-node", "cat", "/tmp/tx.signed"]
            result = subprocess.run(cmd_cat, capture_output=True, text=True, check=True)
            tx_json = json.loads(result.stdout)
            
            # Submit via WebSocket
            logger.info(f"Submitting transaction (TextEnvelope)...")
            await self.client.new_tx(tx_json)
            logger.info("Minting transaction submitted to Head!")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Cardano CLI failed: {e.stderr.decode() if e.stderr else e}")
            return False
        except Exception as e:
            logger.error(f"Minting failed: {e}")
            return False
    async def mint_batch_unique(self, prefix: str, count: int, batch_size: int = 50):
        """
        Mints 'count' unique NFTs in batches of 'batch_size'.
        Each NFT will be named {prefix}_{i}.
        """
        logger.info(f"Starting batch mint of {count} unique assets (Batch Size: {batch_size})...")
        
        total_batches = (count + batch_size - 1) // batch_size
        
        for b in range(total_batches):
            start_idx = b * batch_size
            end_idx = min(start_idx + batch_size, count)
            current_batch_count = end_idx - start_idx
            
            logger.info(f"Processing Batch {b+1}/{total_batches} (Indices {start_idx} to {end_idx-1})...")
            
            # 1. Fetch UTXOs (Need fresh UTXO for each batch transaction)
            # In a real high-perf scenario, we might chain txs, but for now we query-and-spend.
            utxos = await self.client.get_utxos()
            if not utxos:
                logger.error("No UTXOs available for batch.")
                return

            # Select largest UTXO to ensure enough funds for fees
            tx_in = sorted(utxos.keys(), key=lambda k: utxos[k]['value']['lovelace'] if isinstance(utxos[k]['value'], dict) else utxos[k]['value'], reverse=True)[0]
            utxo_info = utxos[tx_in]
            
            val = utxo_info['value']
            if isinstance(val, dict):
                 lovelace = val.get('lovelace', 0)
            else:
                 lovelace = val
                 
            address = utxo_info['address']

            # 2. Build Mint String
            mint_args = []
            
            # We need to construct the output value string carefully.
            # Output = Input - Fee + MintedAssets
            # The mint string for CLI look like: "1 <policy>.<hexname> + 1 <policy>.<hexname> ..."
            
            assets_str_list = []
            
            for i in range(start_idx, end_idx):
                asset_name = f"{prefix}_{i}"
                asset_hex = asset_name.encode('utf-8').hex()
                fq_asset = f"{POLICY_ID}.{asset_hex}"
                assets_str_list.append(f"1 {fq_asset}")

            mint_param = "+".join(assets_str_list)
            
            # Fee calculation
            # Batch txs are larger, so fee will be higher.
            # A simple linear approx: 200k base + 50k per asset? 
            # Let's be safe with 500000 + (10000 * count)?
            # Or just use a large enough fixed fee since it's testnet/L2.
            # 50 assets ~ 1MB? No, names are short.
            fee = 200000 + (30000 * current_batch_count) 
            output_lovelace = lovelace - fee
            
            tx_out_str = f"{address}+{output_lovelace}+{mint_param}"
            
            cmd_build = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "latest", "transaction", "build-raw",
                "--tx-in", tx_in,
                "--tx-out", tx_out_str,
                "--mint", mint_param,
                "--mint-script-file", SCRIPT_FILE,
                "--fee", str(fee),
                "--invalid-hereafter", "200000000",
                "--out-file", "/tmp/tx_batch.raw"
            ]
            
            try:
                subprocess.run(cmd_build, check=True, capture_output=True)
                
                # Sign
                cmd_sign = [
                    "docker", "compose", "exec", "cardano-node",
                    "cardano-cli", "latest", "transaction", "sign",
                    "--tx-body-file", "/tmp/tx_batch.raw",
                    "--signing-key-file", SK_FILE,
                    "--testnet-magic", str(MAGIC),
                    "--out-file", "/tmp/tx_batch.signed"
                ]
                subprocess.run(cmd_sign, check=True, capture_output=True)
                
                # Read & Submit
                cmd_cat = ["docker", "compose", "exec", "cardano-node", "cat", "/tmp/tx_batch.signed"]
                result = subprocess.run(cmd_cat, capture_output=True, text=True, check=True)
                tx_json = json.loads(result.stdout)
                
                await self.client.new_tx(tx_json)
                logger.info(f"Batch {b+1} submitted!")
                
                # Small sleep to allow node to process? 
                # Ideally we check for TxValid, but for benchmark speed we might fire-and-forget 
                # IF the node can handle pipelining. 
                # However, we are re-using UTXO, so we MUST wait for the UTXO to be available again?
                # Actually, we are spending the UTXO. The next batch needs the NEW UTXO produced by this tx.
                # Hydra confirmation is fast (<1s). 
                # We can poll get_utxos until the new transaction output appears?
                # Or we can just calculate the TxId and wait for it?
                
                # For high throughput, we should chain transactions or wait.
                # Let's poll briefly for UTXO update to ensure next batch finds funds.
                await self._wait_for_utxo_update(address, output_lovelace)

            except Exception as e:
                logger.error(f"Batch {b+1} failed: {e}")
                import traceback
                traceback.print_exc()

    async def _wait_for_utxo_update(self, address, expected_lovelace):
        """Wait for the new UTXO with 'expected_lovelace' to appear."""
        # Simple polling
        for _ in range(20): # Wait up to 2 seconds (0.1s interval)
            utxos = await self.client.get_utxos()
            for u in utxos.values():
                 val = u['value']
                 if isinstance(val, dict):
                     l = val.get('lovelace', 0)
                 else:
                     l = val
                 if l == expected_lovelace:
                     return
            await asyncio.sleep(0.1)
        logger.warning("Timed out waiting for next UTXO. Next batch might fail if UTXO not visible.")

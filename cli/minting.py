import subprocess
import json
import logging
import asyncio
import os
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
        
        utxos = await self.client.get_utxos()
        if not utxos:
            logger.error("No UTXOs available in the Head.")
            return False

        # Use first available UTXO
        tx_in = list(utxos.keys())[0]
        utxo_info = utxos[tx_in]
        
        # Handle value structure
        val = utxo_info['value']
        if isinstance(val, dict):
             lovelace = val.get('lovelace', 0)
        else:
             lovelace = val
             
        address = utxo_info['address']
        logger.info(f"Selected input: {tx_in} ({lovelace})")

        # Construct Minting Transaction
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
    def _get_tx_id(self, tx_file: str) -> str:
        """Calculates the TxId of a signed transaction file using cardano-cli."""
        cmd = [
            "docker", "compose", "exec", "cardano-node",
            "cardano-cli", "latest", "transaction", "txid",
            "--tx-file", tx_file
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        raw_output = result.stdout.strip()
        logger.info(f"TxId Raw Output: {raw_output}")
        # Clean it (it might contain warnings from docker?)
        # Extract first hex-like string of length 64
        import re
        match = re.search(r'[a-fA-F0-9]{64}', raw_output)
        if match:
            return match.group(0)
        return raw_output

    def _generate_metadata(self, assets: List[str]) -> Dict[str, Any]:
        """Generates CIP-25 metadata for the batch."""
        metadata_policy = {}
        POLICY_ID = "b7d525b149829894aa5fa73087d7758c2163c55520c8715652cb8515" # Should use constant from module scope?
        # Access module constant via logging? Or importing it?
        # Constants are in module scope. MintingEngine is in same module.
        # But POLICY_ID is defined at module.
        # We can use global POLICY_ID.
        
        for asset_name in assets:
            metadata_policy[asset_name] = {
                "name": asset_name,
                "image": "ipfs://QmPlaceholder",
                "mediaType": "image/png",
                "description": f"Hydra Powered NFT {asset_name}"
            }
        return {"721": {POLICY_ID: metadata_policy}}

    async def mint_batch_unique(self, prefix: str, count: int, batch_size: int = 50):
        """
        Mints 'count' NFTs in 'batch_size' chunks using Transaction Chaining.
        Splits assets into multiple outputs to avoid maxValueSize limits.
        """
        total_batches = (count + batch_size - 1) // batch_size
        logger.info(f"Starting CHAINED batch mint of {count} assets (Batch Size: {batch_size})...")
        
        # 1. Get Initial UTXO
        utxos = await self.client.get_utxos()
        if not utxos:
            logger.error("No UTXOs found in Head to start minting!")
            return

        # Pick the first UTXO as starting point
        tx_id_raw = list(utxos.keys())[0]
        # handle "Hash#Index" string
        if '#' in tx_id_raw:
             tx_id, tx_ix_str = tx_id_raw.split('#')
             tx_ix = int(tx_ix_str)
             current_lovelace = utxos[tx_id_raw]['value']['lovelace']
             address = utxos[tx_id_raw]['address']
        else:
             logger.error("Invalid UTXO format")
             return

        logger.info(f"Initial UTXO: {tx_id_raw} ({current_lovelace} lovelace)")
        
        # State tracking
        prev_tx_id = tx_id
        prev_output_indices = [tx_ix]
        
        # Ensure metadata dir exists
        subprocess.run(["mkdir", "-p", "/tmp/metadata"], check=False)

        for b in range(total_batches):
            batch_start_index = b * batch_size
            current_batch_count = min(batch_size, count - batch_start_index)
            
            # Prepare Assets
            assets = []
            for i in range(current_batch_count):
                asset_name = f"{prefix}_{batch_start_index + i}"
                assets.append(asset_name)

            # Generate Metadata
            metadata_json = self._generate_metadata(assets)
            metadata_filename = f"metadata_batch_{b}.json"
            metadata_host_path = os.path.abspath(f"keys/{metadata_filename}")
            metadata_container_path = f"/keys/{metadata_filename}"
            with open(metadata_host_path, "w") as f:
                json.dump(metadata_json, f)

            # Chunk Assets into outputs (Max 80 per output to fit 5KB value size)
            CHUNK_SIZE = 80
            asset_chunks = [assets[i:i + CHUNK_SIZE] for i in range(0, len(assets), CHUNK_SIZE)]
            
            logger.info(f"Building Batch {b+1}/{total_batches} (Input Tx: {prev_tx_id}, Outputs: {len(prev_output_indices)} -> {len(asset_chunks)})...")

            # Build Tx Args
            cmd_build = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "latest", "transaction", "build-raw"
            ]
            
            # Inputs (Spend all outputs from previous batch)
            current_input_list = [f"{prev_tx_id}#{ix}" for ix in prev_output_indices]
            for inp in current_input_list:
                cmd_build.extend(["--tx-in", inp])

            # Fee logic: 1 ADA fixed (Should be enough, 10 was overkill)
            fee = 1000000
            remaining_lovelace = current_lovelace - fee
            if remaining_lovelace < 0:
                logger.error(f"Ran out of funds! Needed {fee}, have {current_lovelace}")
                return

            # Distributed Lovelace logic:
            # Distribute remaining lovelace evenly across all chunks
            total_outputs = len(asset_chunks)
            outputs_args = []
            used_lovelace = 0
            mint_params_list = []

            for idx, chunk in enumerate(asset_chunks):
                # Build mint string for this chunk
                mint_entries = []
                for name in chunk:
                    name_hex = name.encode("utf-8").hex()
                    mint_entries.append(f"1 {POLICY_ID}.{name_hex}")
                mint_chunk_str = "+".join(mint_entries)
                mint_params_list.append(mint_chunk_str)
                
                # Lovelace for this output (Distribute evenly)
                chunk_lovelace_part = remaining_lovelace // total_outputs
                if idx == total_outputs - 1:
                    chunk_lovelace_part += remaining_lovelace % total_outputs
                
                used_lovelace += chunk_lovelace_part
                
                outputs_args.extend([
                    "--tx-out", f"{address}+{chunk_lovelace_part}+{mint_chunk_str}"
                ])

            cmd_build.extend(outputs_args)
            
            # Mint argument (Sum of all chunks)
            full_mint_str = "+".join(mint_params_list)
            cmd_build.extend([
                "--mint", full_mint_str,
                "--mint-script-file", SCRIPT_FILE,
                "--metadata-json-file", metadata_container_path,
                "--protocol-params-file", "/params/protocol-parameters.json",
                "--fee", str(fee),
                "--invalid-hereafter", "200000000",
                "--out-file", f"/tmp/tx_batch_{b}.raw"
            ])

            # Build and Sign
            try:
                subprocess.run(cmd_build, check=True, capture_output=True)
                
                cmd_sign = [
                    "docker", "compose", "exec", "cardano-node",
                    "cardano-cli", "latest", "transaction", "sign",
                    "--tx-body-file", f"/tmp/tx_batch_{b}.raw",
                    "--signing-key-file", SK_FILE,
                    "--testnet-magic", str(MAGIC),
                    "--out-file", f"/tmp/tx_batch_{b}.signed"
                ]
                subprocess.run(cmd_sign, check=True, capture_output=True)
                
                # Get TxId locally
                tx_id = self._get_tx_id(f"/tmp/tx_batch_{b}.signed")
                if not tx_id:
                     logger.error("Failed to get TxId")
                     return

                # Read Signed Tx
                cmd_msg = ["docker", "compose", "exec", "cardano-node", "cat", f"/tmp/tx_batch_{b}.signed"]
                result = subprocess.run(cmd_msg, capture_output=True, text=True, check=True)
                tx_json = json.loads(result.stdout)
                
                # Submit Async
                await self.client.new_tx(tx_json)
                
                # Update State for next batch
                prev_tx_id = tx_id
                prev_output_indices = list(range(total_outputs))
                current_lovelace = remaining_lovelace 
                
            except subprocess.CalledProcessError as e:
                 logger.error(f"Batch {b+1} failed (Command Error): {e}")
                 if e.stderr:
                     logger.error(f"STDERR: {e.stderr.decode()}")
                 raise 

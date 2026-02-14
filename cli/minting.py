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
            "--invalid-hereafter", "200000000",
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
            await self.client.new_tx(tx_json, wait=True)
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
        logger.debug(f"TxId Raw Output: {raw_output}")
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

        # Sort UTXOs by Lovelace value descending (pick richest)
        sorted_utxos = sorted(
            utxos.items(), 
            key=lambda item: item[1]['value']['lovelace'], 
            reverse=True
        )
        tx_id_raw = sorted_utxos[0][0]
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

            # Prepare Mint String (All 500 assets in one go)
            mint_entries = []
            for name in assets:
                name_hex = name.encode("utf-8").hex()
                mint_entries.append(f"1 {POLICY_ID}.{name_hex}")
            full_mint_str = "+".join(mint_entries)

            logger.info(f"Building Batch {b+1}/{total_batches} (Input Tx: {prev_tx_id}, Outputs: {len(prev_output_indices)} -> 2)...")

            # Build Tx Args
            cmd_build = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "latest", "transaction", "build-raw"
            ]
            
            # Inputs (Spend only the FUEL output from previous batch)
            current_input_list = [f"{prev_tx_id}#{ix}" for ix in prev_output_indices]
            for inp in current_input_list:
                cmd_build.extend(["--tx-in", inp])

            # Fee logic: 8 ADA fixed
            fee = 8000000
            min_utxo = 15000000 # 15 ADA to cover ~50-100 assets in output
            
            # Check funds
            # We need fee + min_utxo. Remainder stays as fuel.
            needed = fee + min_utxo
            remaining_fuel = current_lovelace - needed
            
            if remaining_fuel < 2000000:
                logger.error(f"Ran out of fuel! Have {current_lovelace}, need {needed} + buffer")
                return

            # Outputs
            # Output 0: The Minted Assets + Min UTXO
            out0 = f"{address}+{min_utxo}+{full_mint_str}"
            
            # Output 1: The Fuel (Change) for next batch
            out1 = f"{address}+{remaining_fuel}"
            
            cmd_build.extend([
                "--tx-out", out0,
                "--tx-out", out1
            ])
            
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
                
                # Submit Async (now Synchronous for reliability)
                await self.client.new_tx(tx_json, wait=True)
                
                # Update State for next batch
                prev_tx_id = tx_id
                prev_output_indices = [1]
                current_lovelace = remaining_fuel
                
            except subprocess.CalledProcessError as e:
                 logger.error(f"Batch {b+1} failed (Command Error): {e}")
                 if e.stderr:
                     logger.error(f"STDERR: {e.stderr.decode()}")
                 raise 

    async def mint_10k_turbo(self, prefix: str, count: int = 10000, batch_size: int = 100):
        """
        High-throughput minting: 10K NFTs in under 60 seconds.
        
        Two-phase pipeline:
          Phase 1: Pre-build ALL chained transactions (each mints batch_size NFTs)
          Phase 2: Rapid-fire submit all transactions without waiting for responses
        
        Uses transaction chaining — each tx consumes the fuel output of the
        previous tx, allowing sequential submission without UTXO conflicts.
        """
        import re
        import time
        
        total_batches = (count + batch_size - 1) // batch_size
        logger.info(f"╔══════════════════════════════════════════════════╗")
        logger.info(f"║  TURBO MINT: {count} NFTs in {total_batches} batches of {batch_size}  ║")
        logger.info(f"╚══════════════════════════════════════════════════╝")
        
        # 1. Get Initial UTXO
        utxos = await self.client.get_utxos()
        if not utxos:
            logger.error("No UTXOs found in Head!")
            return 0, 0
        
        # Pick richest UTXO
        sorted_utxos = sorted(
            utxos.items(),
            key=lambda item: item[1]['value']['lovelace'],
            reverse=True
        )
        tx_id_raw = sorted_utxos[0][0]
        if '#' not in tx_id_raw:
            logger.error("Invalid UTXO format")
            return 0, 0
        
        tx_id, tx_ix_str = tx_id_raw.split('#')
        tx_ix = int(tx_ix_str)
        current_lovelace = sorted_utxos[0][1]['value']['lovelace']
        address = sorted_utxos[0][1]['address']
        
        logger.info(f"  Initial UTXO: {tx_id_raw} ({current_lovelace / 1e6:.1f} ADA)")
        
        # Ensure tmp dirs exist
        os.makedirs("/tmp/metadata", exist_ok=True)
        
        # ════════════════════════════════════════════════════
        # PHASE 1: PRE-BUILD ALL TRANSACTIONS
        # ════════════════════════════════════════════════════
        logger.info(f"\n  ══ PHASE 1: Building {total_batches} transactions ══")
        phase1_start = time.time()
        
        prev_tx_id = tx_id
        prev_tx_ix = tx_ix
        built_txs = []  # List of TextEnvelope dicts
        
        for b in range(total_batches):
            batch_start_index = b * batch_size
            current_batch_count = min(batch_size, count - batch_start_index)
            
            # Prepare asset names
            assets = []
            for i in range(current_batch_count):
                asset_name = f"{prefix}_{batch_start_index + i:05d}"
                assets.append(asset_name)
            
            # Mint string
            mint_entries = []
            for name in assets:
                name_hex = name.encode("utf-8").hex()
                mint_entries.append(f"1 {POLICY_ID}.{name_hex}")
            full_mint_str = "+".join(mint_entries)
            
            # Fee and output calculations — optimized for L2
            # L2 fees are minimal; use realistic values
            fee = 300_000  # 0.3 ADA  
            min_utxo = 7_000_000  # 7 ADA — min for 100-asset UTXO (actual: ~6.6 ADA)
            remaining_fuel = current_lovelace - fee - min_utxo
            
            if remaining_fuel < 2_000_000:
                logger.error(f"  Ran out of fuel at batch {b+1}! Have {current_lovelace/1e6:.1f} ADA, need {(fee+min_utxo)/1e6:.1f}+")
                break
            
            # Build command
            cmd_build = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "latest", "transaction", "build-raw",
                "--tx-in", f"{prev_tx_id}#{prev_tx_ix}",
                "--tx-out", f"{address}+{min_utxo}+{full_mint_str}",
                "--tx-out", f"{address}+{remaining_fuel}",
                "--mint", full_mint_str,
                "--mint-script-file", SCRIPT_FILE,
                "--protocol-params-file", "/params/protocol-parameters.json",
                "--fee", str(fee),
                "--invalid-hereafter", "200000000",
                "--out-file", f"/tmp/turbo_{b}.raw"
            ]
            
            result = subprocess.run(cmd_build, capture_output=True, text=True, 
                                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if result.returncode != 0:
                logger.error(f"  Build failed batch {b+1}: {result.stderr[:200]}")
                break
            
            # Sign
            cmd_sign = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "latest", "transaction", "sign",
                "--tx-body-file", f"/tmp/turbo_{b}.raw",
                "--signing-key-file", SK_FILE,
                "--testnet-magic", str(MAGIC),
                "--out-file", f"/tmp/turbo_{b}.signed"
            ]
            result = subprocess.run(cmd_sign, capture_output=True, text=True,
                                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if result.returncode != 0:
                logger.error(f"  Sign failed batch {b+1}: {result.stderr[:200]}")
                break
            
            # Get TxId for chaining
            new_tx_id = self._get_tx_id(f"/tmp/turbo_{b}.signed")
            if not new_tx_id:
                logger.error(f"  TxId failed batch {b+1}")
                break
            
            # Read signed tx
            cmd_cat = [
                "docker", "compose", "exec", "cardano-node",
                "cat", f"/tmp/turbo_{b}.signed"
            ]
            result = subprocess.run(cmd_cat, capture_output=True, text=True,
                                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            tx_json = json.loads(result.stdout)
            built_txs.append(tx_json)
            
            # Chain to next batch
            prev_tx_id = new_tx_id
            prev_tx_ix = 1  # Fuel output is always index 1
            current_lovelace = remaining_fuel
            
            if (b + 1) % 10 == 0 or b == total_batches - 1:
                elapsed = time.time() - phase1_start
                rate = (b + 1) / elapsed if elapsed > 0 else 0
                logger.info(f"    Built {b+1}/{total_batches} txs ({elapsed:.1f}s, {rate:.1f} tx/s)")
        
        phase1_time = time.time() - phase1_start
        logger.info(f"  ✓ Phase 1 complete: {len(built_txs)} txs built in {phase1_time:.1f}s")
        
        if not built_txs:
            return 0, 0
        
        # ════════════════════════════════════════════════════
        # PHASE 2: SEQUENTIAL SUBMIT (chained txs need TxValid before next)
        # ════════════════════════════════════════════════════
        logger.info(f"\n  ══ PHASE 2: Submitting {len(built_txs)} chained transactions ══")
        phase2_start = time.time()
        
        valid = 0
        invalid = 0
        for i, tx in enumerate(built_txs):
            result = await self.client.new_tx(tx, wait=True)
            if result:
                valid += 1
            else:
                invalid += 1
                logger.error(f"    ✗ Batch {i+1} failed — aborting chain (subsequent txs depend on this)")
                break
            
            if (i + 1) % 10 == 0 or i == len(built_txs) - 1:
                elapsed = time.time() - phase2_start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(f"    ✓ {i+1}/{len(built_txs)} confirmed ({elapsed:.1f}s, {rate:.1f} tx/s)")
        
        phase2_time = time.time() - phase2_start
        total_time = phase1_time + phase2_time
        total_nfts = valid * batch_size
        
        logger.info(f"\n  ═══ TURBO MINT RESULTS ═══")
        logger.info(f"    Phase 1 (Build):  {phase1_time:.1f}s ({len(built_txs)} txs)")
        logger.info(f"    Phase 2 (Submit): {phase2_time:.1f}s")
        logger.info(f"    Total Time:       {total_time:.1f}s")
        logger.info(f"    Valid Txs:        {valid}/{len(built_txs)}")
        logger.info(f"    Invalid Txs:      {invalid}")
        logger.info(f"    NFTs Minted:      ~{total_nfts}")
        if total_time > 0:
            logger.info(f"    Effective TPS:    {total_nfts / total_time:.0f}")
        
        return valid, total_time

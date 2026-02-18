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
            "docker", "exec", "hydra-paas-cardano-node-1",
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
                "docker", "exec", "hydra-paas-cardano-node-1",
                "cardano-cli", "latest", "transaction", "sign",
                "--tx-body-file", "/tmp/tx.raw",
                "--signing-key-file", SK_FILE,
                "--testnet-magic", str(MAGIC),
                "--out-file", "/tmp/tx.signed"
            ]
            subprocess.run(cmd_sign, check=True, capture_output=True)

            # Read Signed Tx CBOR
            logger.info("Reading signed transaction...")
            cmd_cat = ["docker", "exec", "hydra-paas-cardano-node-1", "cat", "/tmp/tx.signed"]
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
            "docker", "exec", "hydra-paas-cardano-node-1",
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
                "docker", "exec", "hydra-paas-cardano-node-1",
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
                    "docker", "exec", "hydra-paas-cardano-node-1",
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
                cmd_msg = ["docker", "exec", "hydra-paas-cardano-node-1", "cat", f"/tmp/tx_batch_{b}.signed"]
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

    async def _split_utxo(self, amount_per_part: int, parts: int) -> List[Dict[str, Any]]:
        """
        Splits the largest available UTXO into 'parts' equal UTXOs.
        Returns the list of new UTXOs to be used by workers.
        """
        logger.info(f"Splitting funds into {parts} parts of {amount_per_part/1e6} ADA...")
        
        # 1. Find single large UTXO (with retries)
        utxos = {}
        for attempt in range(10):
            utxos = await self.client.get_utxos()
            if utxos:
                logger.info(f"  Found {len(utxos)} UTXOs on attempt {attempt+1}")
                break
            logger.warning(f"  No UTXOs found on attempt {attempt+1}. Retrying in 1s...")
            await asyncio.sleep(1)
            
        if not utxos: 
            logger.error("  Failed to find UTXOs after 10 attempts.")
            return []
        
        sorted_utxos = sorted(utxos.items(), key=lambda i: i[1]['value']['lovelace'], reverse=True)
        tx_in = sorted_utxos[0][0] # Hash#Index
        val = sorted_utxos[0][1]['value']['lovelace']
        address = sorted_utxos[0][1]['address']
        
        total_needed = amount_per_part * parts
        fee_buffer = 1_000_000 * parts # 1 ADA buffer per part for fees
        
        if val < (total_needed + fee_buffer):
            logger.error(f"Insufficient funds for split. Have {val}, need {total_needed + fee_buffer}")
            return []

        # 2. Build Split Tx
        cmd_build = [
            "docker", "exec", "hydra-paas-cardano-node-1",
            "cardano-cli", "latest", "transaction", "build-raw",
            "--tx-in", tx_in,
            "--invalid-hereafter", "200000000",
            "--out-file", "/tmp/split_parallel.raw"
        ]
        
        # Outputs
        for _ in range(parts):
            cmd_build.extend(["--tx-out", f"{address}+{amount_per_part}"])
            
        # Change (remainder)
        fee_est = 200_000 * parts
        change = val - (amount_per_part * parts) - fee_est
        cmd_build.extend(["--tx-out", f"{address}+{change}"])
        
        # Add fee
        cmd_build.extend(["--fee", str(fee_est)])

        try:
            subprocess.run(cmd_build, check=True, capture_output=True)
            
            # Sign
            cmd_sign = [
                "docker", "exec", "hydra-paas-cardano-node-1",
                "cardano-cli", "latest", "transaction", "sign",
                "--tx-body-file", "/tmp/split_parallel.raw",
                "--signing-key-file", SK_FILE,
                "--testnet-magic", str(MAGIC),
                "--out-file", "/tmp/split_parallel.signed"
            ]
            subprocess.run(cmd_sign, check=True, capture_output=True)
            
            # Get TxId
            tx_id = self._get_tx_id("/tmp/split_parallel.signed")
            if not tx_id: return []
            
            # Read & Submit
            cmd_cat = ["docker", "exec", "hydra-paas-cardano-node-1", "cat", "/tmp/split_parallel.signed"]
            res = subprocess.run(cmd_cat, capture_output=True, text=True, check=True)
            tx_json = json.loads(res.stdout)
            
            # Submit and Wait
            await self.client.new_tx(tx_json, wait=True)
            logger.info(f"Split transaction confirmed: {tx_id}")
            
            # Return the N new UTXOs (Indices 0 to parts-1)
            # We construct them manually since we know the structure
            new_utxos = []
            for i in range(parts):
                new_utxos.append({
                    "tx_id": tx_id,
                    "index": i,
                    "address": address,
                    "lovelace": amount_per_part
                })
            return new_utxos

        except Exception as e:
            logger.error(f"Split failed: {e}")
            return []

    def _build_chain(self, worker_id: int, initial_utxo: Dict, 
                    prefix: str, count: int, batch_size: int) -> List[Dict]:
        """
        Worker function to build a chain of transactions.
        Executed in a separate thread to allow parallelism.
        """
        import time
        built_txs = []
        total_batches = (count + batch_size - 1) // batch_size
        
        prev_tx_id = initial_utxo['tx_id']
        prev_tx_ix = initial_utxo['index']
        current_lovelace = initial_utxo['lovelace']
        address = initial_utxo['address']
        
        logger.info(f"[Worker {worker_id}] Starting chain: {count} NFTs in {total_batches} batches")
        
        for b in range(total_batches):
            logger.info(f"[Worker {worker_id}] Building batch {b}/{total_batches}, fuel={current_lovelace/1e6:.1f} ADA")
            batch_start_index = b * batch_size
            current_batch_count = min(batch_size, count - batch_start_index)
            
            # Assets
            assets = []
            for i in range(current_batch_count):
                # Unique name: prefix_W{worker}_B{batch}_I{index}
                # using global index to keep it clean: prefix_{global_index}
                # We need to know global offset if strictly contiguous, but for speed 
                # we can use worker-based suffixing or ensure caller handles offset.
                # Here we assume caller passed a unique prefix per worker or handled offset logic.
                asset_name = f"{prefix}_{batch_start_index + i:05d}"
                assets.append(asset_name)
            
            mint_entries = [f"1 {POLICY_ID}.{name.encode('utf-8').hex()}" for name in assets]
            full_mint_str = "+".join(mint_entries)
            
            # Fees
            fee = 1_000_000 # Increased to 1 ADA to be safe
            min_utxo = 10_000_000  # 10 ADA for 50 NFT output (safer for ledger checks)
            remaining_fuel = current_lovelace - fee - min_utxo
            
            if remaining_fuel < 1_000_000:
                logger.error(f"[Worker {worker_id}] Out of fuel at batch {b}")
                break
                
            # Build Raw
            # Note: Parallel docker execs might race on /tmp files if we don't unique them.
            # Use unique filenames for this worker/batch.
            raw_file = f"/tmp/w{worker_id}_b{b}.raw"
            signed_file = f"/tmp/w{worker_id}_b{b}.signed"

            cmd_build = [
                "docker", "exec", "hydra-paas-cardano-node-1",
                "cardano-cli", "latest", "transaction", "build-raw",
                "--tx-in", f"{prev_tx_id}#{prev_tx_ix}",
                "--tx-out", f"{address}+{min_utxo}+{full_mint_str}",
                "--tx-out", f"{address}+{remaining_fuel}",
                "--mint", full_mint_str,
                "--mint-script-file", SCRIPT_FILE,
                "--protocol-params-file", "/params/protocol-parameters.json",
                "--fee", str(fee),
                "--invalid-hereafter", "200000000",
                "--out-file", raw_file
            ]
            
            try:
                subprocess.run(cmd_build, check=True, capture_output=True)
                
                # Sign
                cmd_sign = [
                    "docker", "exec", "hydra-paas-cardano-node-1",
                    "cardano-cli", "latest", "transaction", "sign",
                    "--tx-body-file", raw_file,
                    "--signing-key-file", SK_FILE,
                    "--testnet-magic", str(MAGIC),
                    "--out-file", signed_file
                ]
                subprocess.run(cmd_sign, check=True, capture_output=True)
                
                # Get TxId (cardano-cli latest returns JSON: {"txhash": "hex..."})
                cmd_txid = ["docker", "exec", "hydra-paas-cardano-node-1", "cardano-cli", "latest", "transaction", "txid", "--tx-file", signed_file]
                res_txid = subprocess.run(cmd_txid, check=True, capture_output=True, text=True)
                raw_txid = res_txid.stdout.strip()
                # Parse JSON if present, otherwise use raw
                import re
                if raw_txid.startswith('{'):
                    txid_data = json.loads(raw_txid)
                    new_tx_id = txid_data.get('txhash', txid_data.get('transaction', ''))
                else:
                    # Fallback: extract 64-char hex string
                    m = re.search(r'[a-fA-F0-9]{64}', raw_txid)
                    new_tx_id = m.group(0) if m else raw_txid
                
                # Read JSON
                cmd_cat = ["docker", "exec", "hydra-paas-cardano-node-1", "cat", signed_file]
                res_cat = subprocess.run(cmd_cat, capture_output=True, text=True, check=True)
                tx_json = json.loads(res_cat.stdout)
                
                built_txs.append(tx_json)
                
                prev_tx_id = new_tx_id
                prev_tx_ix = 1
                current_lovelace = remaining_fuel
                
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode() if e.stderr else "no stderr"
                logger.error(f"[Worker {worker_id}] Build failed at batch {b}: {stderr[:500]}")
                break
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Build failed at batch {b}: {e}")
                break
                
        logger.info(f"[Worker {worker_id}] Built {len(built_txs)} transactions.")
        return built_txs

    async def mint_parallel(self, prefix: str, total_count: int = 10000, batch_size: int = 100, workers: int = 4):
        """
        Parallel Minting Engine.
        1. Splits funds into 'workers' parts.
        2. Spawns 'workers' threads to build transaction chains concurrently.
        3. Submits all transactions (interleaved or sequential per chain).
        """
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        logger.info(f"🚀 PARALLEL MINT: {total_count} NFTs | {workers} Workers | {batch_size} Batch Size")
        
        # 1. Calculate requirements
        per_worker_count = total_count // workers
        batches_per_worker = (per_worker_count + batch_size - 1) // batch_size
        
        # Cost per batch = fee + min_utxo. The min_utxo is NOT recycled —
        # it stays in the NFT output. Only remaining_fuel carries forward.
        fee_est = 1_000_000
        min_utxo_est = 10_000_000 # 10 ADA for 50 NFT output
        needed_per_worker = (batches_per_worker * (fee_est + min_utxo_est)) + 5_000_000
        
        # 2. Split Funds
        worker_utxos = await self._split_utxo(needed_per_worker, workers)
        if len(worker_utxos) < workers:
            logger.error("Failed to split funds for workers. Aborting.")
            return 0, 0
            
        # 3. Build Parallel Chains
        logger.info("Building chains in parallel...")
        build_start = time.time()
        
        loop = asyncio.get_running_loop()
        all_chains = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            tasks = []
            for w in range(workers):
                # Offset prefix for uniqueness? 
                # e.g. prefix="Hydra" -> worker 0: Hydra_00000..., worker 1: Hydra_02500...
                # We handle this by passing base index or modifying prefix
                worker_prefix = f"{prefix}_W{w}"
                
                tasks.append(
                    loop.run_in_executor(
                        executor, 
                        self._build_chain, 
                        w, worker_utxos[w], worker_prefix, per_worker_count, batch_size
                    )
                )
            
            all_chains = await asyncio.gather(*tasks)
            
        build_time = time.time() - build_start
        total_built = sum(len(c) for c in all_chains)
        logger.info(f"✅ Build Complete: {total_built} txs in {build_time:.1f}s ({(total_built/build_time):.1f} tx/s built)")

        # 4. Submit Phase — Fire-and-Forget with Interleaved Chains
        # Instead of serializing through ws_lock, we:
        #   a) Interleave txs from all chains (round-robin by depth)
        #   b) Submit ALL txs as fast as possible (fire-and-forget)
        #   c) Collect TxValid/TxInvalid events at the end
        # Chained txs within a worker are ordered correctly by interleaving.
        
        logger.info("Submitting chains (fire-and-forget)...")
        submit_start = time.time()
        
        # Interleave: submit tx[0] from each chain, then tx[1] from each, etc.
        # This ensures dependent txs within a chain maintain order while
        # maximizing parallelism across chains.
        max_depth = max(len(c) for c in all_chains) if all_chains else 0
        submitted = 0
        
        for depth in range(max_depth):
            for chain in all_chains:
                if depth < len(chain):
                    await self.client.send_command({
                        "tag": "NewTx",
                        "transaction": chain[depth]
                    })
                    submitted += 1
        
        logger.info(f"  Submitted {submitted} txs. Collecting confirmations...")
        
        # Collect confirmations
        valid = 0
        invalid = 0
        timeout_per_tx = 2  # seconds per tx max wait
        deadline = time.time() + max(submitted * timeout_per_tx, 30)
        
        while (valid + invalid) < submitted and time.time() < deadline:
            try:
                event = await asyncio.wait_for(
                    self.client.receive_event(), 
                    timeout=min(5, deadline - time.time())
                )
                tag = event.get("tag", "")
                if tag == "TxValid":
                    valid += 1
                elif tag == "TxInvalid":
                    invalid += 1
                    reason = event.get("validationError", {}).get("reason", "Unknown")
                    if invalid <= 5:  # Only log first 5 failures
                        logger.warning(f"  TxInvalid: {reason[:100]}")
            except asyncio.TimeoutError:
                break
        
        submit_time = time.time() - submit_start
        total_valid_txs = valid
        total_nfts = total_valid_txs * batch_size
        total_time = build_time + submit_time
        
        logger.info(f"═══ PARALLEL RESULTS ═══")
        logger.info(f"  Submitted: {submitted}")
        logger.info(f"  Valid Txs: {valid}")
        logger.info(f"  Invalid:   {invalid}")
        logger.info(f"  NFTs:      {total_nfts}")
        logger.info(f"  Build:     {build_time:.1f}s")
        logger.info(f"  Submit:    {submit_time:.1f}s")
        logger.info(f"  Total:     {total_time:.1f}s")
        if submit_time > 0:
            logger.info(f"  TPS (submit only): {total_nfts/submit_time:.1f}")
        if total_time > 0:
            logger.info(f"  TPS (total):       {total_nfts/total_time:.1f}")
            
        return total_valid_txs, total_time

    async def mint_10k_turbo(self, prefix: str, count: int = 10000, batch_size: int = 100, workers: int = 4):
        """High-performance wrapper: parallel workers for max throughput."""
        return await self.mint_parallel(prefix, count, batch_size, workers=workers)

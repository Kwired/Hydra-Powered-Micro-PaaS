#!/usr/bin/env python3
"""
Comprehensive Hydra E2E Demo Script
====================================
Handles the COMPLETE lifecycle automatically:
  0. Reset: Stop hydra-node, wipe persistence, restart
  1. Check: Verify Idle status
  2. Init:  Initialize Hydra Head
  3. Fund:  Commit small UTXO, balance/sign/submit, wait for HeadIsOpen
  4. Mint:  Mint 10 NFTs with unique metadata inside the Head
  5. Close: Close the Head and get L1 tx hashes for CardanoScan verification

In Hydra 1.2.0, fuel marking is deprecated. ALL UTXOs at the
cardano-signing-key address are fuel. We commit a SMALL UTXO 
and leave larger ones as fuel for L1 fees.
"""

import asyncio
import json
import logging
import time
import subprocess
import sys
import os
import requests
import websockets

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

HYDRA_WS = "ws://localhost:4001"
HYDRA_HTTP = "http://localhost:4001"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(PROJECT_DIR, "keys/payment.addr"), "r") as f:
    MY_ADDRESS = f.read().strip()

# Track all L1 tx hashes for verification
L1_TX_HASHES = []


def run_docker(*args, check=True, capture=True):
    """Helper to run docker compose commands. Suppresses noisy stderr."""
    cmd = ["docker", "compose"] + list(args)
    env = os.environ.copy()
    env["DOCKER_CLI_HINTS"] = "false"
    
    kwargs = {"text": True, "cwd": PROJECT_DIR, "env": env}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.DEVNULL
    
    res = subprocess.run(cmd, **kwargs)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return res


def step_banner(num, total, title):
    logger.info("")
    logger.info(f"{'='*60}")
    logger.info(f"  STEP {num}/{total}: {title}")
    logger.info(f"{'='*60}")


# ──────────────────────────────────────────────────────────
# STEP 0: RESET
# ──────────────────────────────────────────────────────────
def step_0_reset():
    step_banner(0, 6, "RESET — Stop, Wipe, Restart")
    
    # Stop hydra-node
    logger.info("  Stopping hydra-node...")
    run_docker("stop", "hydra-node", check=False)
    
    # Wipe persistence
    persistence_dir = os.path.join(PROJECT_DIR, "hydra-persistence")
    logger.info(f"  Wiping persistence: {persistence_dir}")
    for f in os.listdir(persistence_dir):
        fp = os.path.join(persistence_dir, f)
        try:
            if os.path.isfile(fp):
                os.unlink(fp)
            elif os.path.isdir(fp):
                import shutil
                shutil.rmtree(fp)
        except Exception as e:
            logger.warning(f"  Could not delete {fp}: {e}")
    
    # Restart hydra-node
    logger.info("  Starting hydra-node...")
    run_docker("start", "hydra-node")
    
    # Wait for node to sync
    logger.info("  Waiting 25s for hydra-node to sync...")
    time.sleep(25)
    logger.info("  ✓ Reset complete!")


# ──────────────────────────────────────────────────────────
# STEP 1: CHECK STATUS
# ──────────────────────────────────────────────────────────
async def step_1_check_status():
    step_banner(1, 6, "CHECK STATUS")
    
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())
    head_status = greeting.get("headStatus", "Unknown")
    await ws.close()
    
    logger.info(f"  Head Status: {head_status}")
    
    if head_status != "Idle":
        logger.error(f"  ✗ Expected 'Idle', got '{head_status}'")
        logger.error(f"  Try running the script again — it will reset.")
        return None
    
    logger.info("  ✓ Head is Idle — ready to initialize!")
    return head_status


# ──────────────────────────────────────────────────────────
# STEP 2: INIT
# ──────────────────────────────────────────────────────────
async def step_2_init():
    step_banner(2, 6, "INITIALIZE HYDRA HEAD")
    
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())  # consume greeting
    
    logger.info("  Sending Init command...")
    await ws.send(json.dumps({"tag": "Init"}))
    
    # Wait for HeadIsInitializing
    start = time.time()
    init_success = False
    while time.time() - start < 120:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            tag = msg.get("tag", "")
            logger.info(f"    ← {tag}")
            
            if tag == "HeadIsInitializing":
                init_success = True
                break
            elif tag == "CommandFailed":
                logger.error(f"  ✗ Init failed: {json.dumps(msg)[:300]}")
                break
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            logger.info(f"    ...waiting ({elapsed:.0f}s)")
    
    await ws.close()
    
    if not init_success:
        logger.error("  ✗ Head did not initialize!")
        return False
    
    logger.info("  ✓ Head is Initializing!")
    logger.info("  Waiting 10s for Init tx L1 confirmation...")
    time.sleep(10)
    return True


# ──────────────────────────────────────────────────────────
# STEP 3: FUND (COMMIT)
# ──────────────────────────────────────────────────────────
async def step_3_fund():
    step_banner(3, 6, "FUND — Commit UTXO into Head")
    
    # Query UTXOs via Ogmios
    from cli.ogmios_client import OgmiosClient
    ogmios = OgmiosClient()
    await ogmios.connect()
    utxos = await ogmios.query_utxo(MY_ADDRESS)
    await ogmios.close()
    
    if not utxos:
        logger.error("  ✗ No UTXOs found!")
        return False
    
    # Filter and sort ascending
    utxos = [u for u in utxos if u['value']['ada']['lovelace'] > 5_000_000]
    utxos.sort(key=lambda u: u['value']['ada']['lovelace'])
    
    logger.info(f"  Available UTXOs ({len(utxos)}):")
    for u in utxos:
        txid = u['transaction']['id']
        idx = u['index']
        lovelace = u['value']['ada']['lovelace']
        has_datum = u.get('datum') is not None or u.get('datumHash') is not None
        logger.info(f"    {txid[:12]}...#{idx}: {lovelace / 1e6:.1f} ADA {'(datum)' if has_datum else ''}")
    
    # Filter out UTXOs with datums for commit — they can't be used for 
    # simple commits because the /commit payload doesn't include datum info.
    # Fee UTXOs CAN have datums — they're consumed as regular cardano-cli inputs.
    clean_utxos = [u for u in utxos 
                   if u.get('datum') is None and u.get('datumHash') is None]
    
    if not clean_utxos:
        logger.error("  ✗ No clean UTXOs (without datum) available for commit!")
        return False
    
    logger.info(f"  Clean UTXOs (no datum): {len(clean_utxos)}")
    
    # If only 1 clean UTXO and it's big, we need to split it first.
    # Hydra needs fuel UTXOs remaining, so we can't commit everything.
    biggest_clean = max(clean_utxos, key=lambda u: u['value']['ada']['lovelace'])
    biggest_ada = biggest_clean['value']['ada']['lovelace']
    
    if len(clean_utxos) == 1 and biggest_ada > 500_000_000:
        # Split: 3000 ADA for commit, remainder for fuel
        logger.info(f"  Only 1 clean UTXO ({biggest_ada/1e6:.0f} ADA). Splitting first...")
        split_txid = biggest_clean['transaction']['id']
        split_idx = biggest_clean['index']
        commit_amount = 1_000_000_000  # 1000 ADA for the Head
        split_fee = 200_000  # 0.2 ADA fee
        fuel_amount = biggest_ada - commit_amount - split_fee
        
        # Build split tx
        run_docker(
            "exec", "cardano-node",
            "cardano-cli", "conway", "transaction", "build-raw",
            "--tx-in", f"{split_txid}#{split_idx}",
            "--tx-out", f"{MY_ADDRESS}+{commit_amount}",
            "--tx-out", f"{MY_ADDRESS}+{fuel_amount}",
            "--fee", str(split_fee),
            "--out-file", "/keys/split.raw"
        )
        run_docker(
            "exec", "cardano-node",
            "cardano-cli", "conway", "transaction", "sign",
            "--tx-body-file", "/keys/split.raw",
            "--signing-key-file", "/keys/cardano.sk",
            "--testnet-magic", "1",
            "--out-file", "/keys/split.signed"
        )
        
        # Submit split tx
        submit_cmd = [
            "docker", "compose", "exec", "cardano-node",
            "cardano-cli", "conway", "transaction", "submit",
            "--tx-file", "/keys/split.signed",
            "--testnet-magic", "1",
            "--socket-path", "/ipc/node.socket"
        ]
        res = subprocess.run(submit_cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
        if res.returncode != 0:
            logger.error(f"  ✗ Split tx failed: {res.stderr[:200]}")
            return False
        
        logger.info(f"  ✓ Split tx submitted! Waiting for confirmation...")
        
        # Wait for split to confirm — poll UTXOs until we see ≥2 clean ones
        for attempt in range(9):  # 9 × 10s = 90s max
            time.sleep(10)
            ogmios = OgmiosClient()
            await ogmios.connect()
            utxos = await ogmios.query_utxo(MY_ADDRESS)
            await ogmios.close()
            
            utxos = [u for u in utxos if u['value']['ada']['lovelace'] > 5_000_000]
            clean_utxos = [u for u in utxos 
                           if u.get('datum') is None and u.get('datumHash') is None]
            logger.info(f"    Poll {attempt+1}: {len(clean_utxos)} clean UTXOs found")
            if len(clean_utxos) >= 2:
                break
        
        utxos.sort(key=lambda u: u['value']['ada']['lovelace'])
        
        logger.info(f"  After split — Clean UTXOs: {len(clean_utxos)}")
        for u in clean_utxos:
            txid = u['transaction']['id']
            idx = u['index']
            lovelace = u['value']['ada']['lovelace']
            logger.info(f"    {txid[:12]}...#{idx}: {lovelace / 1e6:.1f} ADA")
    
    # Pick the SMALLEST clean UTXO >= 200 ADA for commit
    # (100 batches × ~2.3 ADA = ~230 ADA minimum needed inside Head)
    # This leaves large UTXOs as fuel for Hydra L1 operations
    clean_utxos.sort(key=lambda u: u['value']['ada']['lovelace'])  # ascending
    
    commit_utxo = None
    for u in clean_utxos:
        u_lovelace = u['value']['ada']['lovelace']
        u_key = f"{u['transaction']['id']}#{u['index']}"
        others = [x for x in utxos if f"{x['transaction']['id']}#{x['index']}" != u_key]
        has_fuel = others and any(x['value']['ada']['lovelace'] >= 5_000_000 for x in others)
        if u_lovelace >= 200_000_000 and has_fuel:
            commit_utxo = u
            break
    
    if not commit_utxo:
        commit_utxo = clean_utxos[0]  # Fallback
    
    txid = commit_utxo['transaction']['id']
    idx = commit_utxo['index']
    lovelace = commit_utxo['value']['ada']['lovelace']
    commit_key = f"{txid}#{idx}"
    
    # Fee UTXO — any UTXO different from commit (can have datum)
    fee_utxo = None
    for u in utxos:
        uid = f"{u['transaction']['id']}#{u['index']}"
        if uid != commit_key and u['value']['ada']['lovelace'] >= 5_000_000:
            fee_utxo = u
            break
    
    if not fee_utxo:
        logger.error("  ✗ No separate fee UTXO found!")
        return False
    
    logger.info(f"\n  → Commit UTXO: {commit_key} ({lovelace / 1e6:.1f} ADA)")
    logger.info(f"  → Fee UTXO:    {fee_utxo['transaction']['id'][:12]}...#{fee_utxo['index']} ({fee_utxo['value']['ada']['lovelace'] / 1e6:.1f} ADA)")
    
    # Call POST /commit
    commit_payload = {
        commit_key: {
            "address": MY_ADDRESS,
            "value": {"lovelace": lovelace}
        }
    }
    
    logger.info("  Calling POST /commit...")
    resp = requests.post(
        f"{HYDRA_HTTP}/commit",
        json=commit_payload,
        headers={'Content-Type': 'application/json'}
    )
    
    if resp.status_code != 200:
        error = resp.text[:500]
        logger.error(f"  ✗ Commit draft failed ({resp.status_code}): {error}")
        return False
    
    draft = resp.json()
    draft_cbor = draft.get('cborHex')
    if not draft_cbor:
        logger.error(f"  ✗ No cborHex in response")
        return False
    
    logger.info(f"  ✓ Draft commit tx received ({len(draft_cbor)} chars)")
    
    # Balance
    from cli.balance_utils import balance_commit_tx
    try:
        balanced_cbor = balance_commit_tx(draft_cbor, fee_utxo, fee_utxo, MY_ADDRESS)
        logger.info(f"  ✓ Balanced")
    except Exception as e:
        logger.error(f"  ✗ Balance failed: {e}")
        return False
    
    # Save
    cbor_path = os.path.join(PROJECT_DIR, "keys/commit.balanced.cbor")
    with open(cbor_path, "w") as f:
        json.dump({"type": "Tx ConwayEra", "description": "", "cborHex": balanced_cbor}, f)
    
    # Sign
    logger.info("  Signing commit tx...")
    res = run_docker(
        "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "sign",
        "--tx-body-file", "/keys/commit.balanced.cbor",
        "--signing-key-file", "/keys/cardano.sk",
        "--testnet-magic", "1",
        "--out-file", "/keys/commit.signed"
    )
    
    # Submit (use subprocess directly to capture both stdout + stderr)
    logger.info("  Submitting commit tx to L1...")
    submit_cmd = [
        "docker", "compose", "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "submit",
        "--tx-file", "/keys/commit.signed",
        "--testnet-magic", "1",
        "--socket-path", "/ipc/node.socket"
    ]
    res = subprocess.run(
        submit_cmd, capture_output=True, text=True, cwd=PROJECT_DIR
    )
    
    if res.returncode != 0:
        logger.error(f"  ✗ Submit failed: {res.stderr[:300]}")
        return False
    
    # cardano-cli puts output on stdout or stderr depending on version
    all_output = (res.stdout + "\n" + res.stderr).strip()
    
    # Parse tx hash
    commit_hash = ""
    for line in all_output.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            if line.startswith('{'):
                tx_data = json.loads(line)
                commit_hash = tx_data.get("txhash", "")
                break
        except json.JSONDecodeError:
            pass
        # Look for "Transaction successfully submitted." or hex hash
        if len(line) == 64 and all(c in '0123456789abcdef' for c in line):
            commit_hash = line
            break
    
    logger.info(f"  ✓ Commit tx submitted!")
    if commit_hash:
        logger.info(f"    Hash: {commit_hash}")
    L1_TX_HASHES.append(("Commit", commit_hash))
    
    # Wait for HeadIsOpen
    logger.info("  Waiting for HeadIsOpen (1-2 blocks, ~40-60s)...")
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())  # consume greeting
    
    start = time.time()
    head_opened = False
    utxo_in_head = {}
    
    while time.time() - start < 300:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            tag = msg.get("tag", "")
            logger.info(f"    ← {tag}")
            
            if tag == "HeadIsOpen":
                head_opened = True
                utxo_in_head = msg.get("utxo", {})
                break
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            logger.info(f"    ...waiting ({elapsed:.0f}s)")
    
    await ws.close()
    
    if not head_opened:
        logger.error("  ✗ Head did not open within 5 minutes!")
        return False
    
    logger.info("  ✓ HEAD IS OPEN!")
    logger.info(f"  UTXOs in Head: {len(utxo_in_head)}")
    for k, v in utxo_in_head.items():
        ada = v.get('value', {}).get('lovelace', 0) / 1e6
        logger.info(f"    {k}: {ada:.1f} ADA")
    
    return True


# ──────────────────────────────────────────────────────────
# STEP 4: MINT 10 NFTs
# ──────────────────────────────────────────────────────────
async def step_4_mint():
    step_banner(4, 6, "TURBO MINT 10,000 NFTs")
    
    from cli.hydra_client import HydraClient
    from cli.minting import MintingEngine
    
    client = HydraClient()
    await client.connect()
    greeting = await client.receive_event()  # consume greeting
    
    engine = MintingEngine(client)
    
    NFT_COUNT = 10_000
    BATCH_SIZE = 100  # 100 NFTs per transaction
    
    batch_start = time.time()
    valid_txs, mint_time = await engine.mint_10k_turbo(
        prefix="Hydra",
        count=NFT_COUNT,
        batch_size=BATCH_SIZE
    )
    batch_elapsed = time.time() - batch_start
    
    success_count = valid_txs * BATCH_SIZE
    mint_results = [{"name": f"batch_{i}", "status": "success"} for i in range(valid_txs)]
    
    await client.close()
    return mint_results, batch_elapsed, success_count


# ──────────────────────────────────────────────────────────
# STEP 5: CLOSE
# ──────────────────────────────────────────────────────────
async def step_5_close():
    step_banner(5, 6, "CLOSE HYDRA HEAD")
    
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())  # consume greeting
    
    logger.info("  Sending Close command...")
    await ws.send(json.dumps({"tag": "Close"}))
    
    start = time.time()
    closed = False
    while time.time() - start < 120:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            tag = msg.get("tag", "")
            logger.info(f"    ← {tag}")
            
            if tag == "HeadIsClosed":
                closed = True
                logger.info("  ✓ Head is Closed! Contestation period active.")
                break
            elif tag == "CommandFailed":
                logger.error(f"  ✗ Close failed!")
                break
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            logger.info(f"    ...waiting ({elapsed:.0f}s)")
    
    await ws.close()
    return closed


# ──────────────────────────────────────────────────────────
# STEP 6: VERIFY ON L1
# ──────────────────────────────────────────────────────────
def step_6_verify():
    step_banner(6, 6, "L1 VERIFICATION")
    
    # Query final UTXOs
    logger.info("  Querying L1 UTXOs...")
    res = run_docker(
        "exec", "cardano-node",
        "cardano-cli", "query", "utxo",
        "--address", MY_ADDRESS,
        "--testnet-magic", "1",
        "--socket-path", "/ipc/node.socket",
        "--out-file", "/dev/stdout"
    )
    
    try:
        utxos = json.loads(res.stdout)
        logger.info(f"  L1 UTXOs at payment address ({len(utxos)}):")
        total_ada = 0
        for k, v in utxos.items():
            lovelace = v.get('value', {}).get('lovelace', 0)
            total_ada += lovelace
            logger.info(f"    {k}: {lovelace / 1e6:.1f} ADA")
        logger.info(f"  Total: {total_ada / 1e6:.1f} ADA")
    except json.JSONDecodeError:
        logger.info(f"  Raw output: {res.stdout[:500]}")
    
    # Print CardanoScan links
    logger.info("")
    logger.info("  ═══ CardanoScan Verification Links (Testnet) ═══")
    logger.info(f"  Address: https://preprod.cardanoscan.io/address/{MY_ADDRESS}")
    for label, txhash in L1_TX_HASHES:
        if txhash and len(txhash) == 64:
            logger.info(f"  {label} Tx: https://preprod.cardanoscan.io/transaction/{txhash}")
        else:
            logger.info(f"  {label} Tx: {txhash}")


# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────
async def run_e2e():
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║                HYDRA E2E DEMO                         ║")
    logger.info("║   Init → Fund → Mint 10 NFTs → Close → Verify        ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info(f"  Address: {MY_ADDRESS}")
    logger.info(f"  Time:    {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start = time.time()
    
    # Step 0: Reset
    step_0_reset()
    
    # Step 1: Check
    status = await step_1_check_status()
    if status != "Idle":
        logger.error("Cannot proceed — Head is not Idle after reset!")
        return False
    
    # Step 2: Init
    if not await step_2_init():
        logger.error("Init failed!")
        return False
    
    # Step 3: Fund
    if not await step_3_fund():
        logger.error("Fund failed!")
        return False
    
    # Step 4: Mint
    mint_results, mint_time, success_count = await step_4_mint()
    
    # Step 5: Close
    await step_5_close()
    
    # Step 6: Verify
    step_6_verify()
    
    overall_elapsed = time.time() - overall_start
    
    # Save results
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "address": MY_ADDRESS,
        "overall_time_seconds": round(overall_elapsed, 2),
        "minted": mint_results,
        "total_nfts": len(mint_results),
        "successful_mints": success_count,
        "minting_time_seconds": round(mint_time, 2),
        "tps": round(success_count / mint_time, 1) if mint_time > 0 else 0,
        "l1_transactions": [{"label": l, "hash": h} for l, h in L1_TX_HASHES],
        "cardanoscan_address": f"https://preprod.cardanoscan.io/address/{MY_ADDRESS}"
    }
    
    results_path = os.path.join(PROJECT_DIR, "e2e_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║                  E2E COMPLETE!                        ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info(f"  Minted:       ~{success_count} NFTs")
    logger.info(f"  Mint Time:    {mint_time:.2f}s")
    logger.info(f"  Overall Time: {overall_elapsed:.1f}s")
    logger.info(f"  Results:      {results_path}")
    logger.info(f"  CardanoScan:  https://preprod.cardanoscan.io/address/{MY_ADDRESS}")
    
    return success_count > 0


if __name__ == "__main__":
    success = asyncio.run(run_e2e())
    sys.exit(0 if success else 1)

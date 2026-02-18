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
    
    # Wipe persistence (files are root-owned inside Docker, use container to delete)
    persistence_dir = os.path.join(PROJECT_DIR, "hydra-persistence")
    logger.info(f"  Wiping persistence: {persistence_dir}")
    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{persistence_dir}:/data", "alpine", "sh", "-c", "rm -rf /data/* /data/.* 2>/dev/null; chmod 777 /data"],
        capture_output=True
    )
    
    # Restart hydra-node
    logger.info("  Starting hydra-node...")
    run_docker("start", "hydra-node")
    
    # Wait for node to sync
    logger.info("  Waiting 40s for hydra-node to sync...")
    time.sleep(40)
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
                tx_id = msg.get("transactionId", "")
                if tx_id:
                     L1_TX_HASHES.append(("Init", tx_id))
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
    # Append to L1 hashes if not done in loop (safety)
    
    logger.info("  Waiting 40s for Init tx L1 confirmation and UTXO sync...")
    time.sleep(40)
    return True


# ──────────────────────────────────────────────────────────
# STEP 3: FUND (COMMIT)
# ──────────────────────────────────────────────────────────
import cleanup_utxos

# ... (Previous imports kept in context, just import inserted at top if easier, but here I replace step 3 mainly)

# ──────────────────────────────────────────────────────────
# STEP 0.5: CLEANUP & CONSOLIDATE FUNDS
# ──────────────────────────────────────────────────────────
async def step_0_5_cleanup():
    step_banner(0.5, 6, "CLEANUP — Consolidate Funds & Create Fuel")
    logger.info("  Running cleanup_utxos to consolidate funds...")
    try:
        # cleanup_utxos handles its own L1 confirmation polling and returns hash
        cleanup_hash = cleanup_utxos.cleanup_utxos()
        if not cleanup_hash:
            logger.error("  Cleanup failed!")
            return False
        logger.info(f"  ✓ Funds ready! Cleanup Tx: {cleanup_hash}")
        L1_TX_HASHES.append(("Cleanup", cleanup_hash))
        return True
    except Exception as e:
        logger.error(f"  Cleanup exception: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    
    logger.info(f"  Available UTXOs ({len(utxos)}):")
    for u in utxos:
        txid = u['transaction']['id']
        idx = u['index']
        lovelace = u['value']['ada']['lovelace']
        logger.info(f"    {txid[:12]}...#{idx}: {lovelace / 1e6:.1f} ADA")

    # Sort by value to find commit UTXO (~500 ADA) and fee UTXO
    sorted_utxos = sorted(utxos, key=lambda u: u['value']['ada']['lovelace'], reverse=True)
    
    # Use the second-largest UTXO for commit (cleanup creates 500 ADA as first explicit output)
    # Find a UTXO close to 500 ADA for commit
    commit_utxo = None
    for u in sorted_utxos:
        val = u['value']['ada']['lovelace']
        if 2_500_000_000 <= val <= 3_500_000_000:  # ~3000 ADA commit UTXO
            commit_utxo = u
            break
    
    if not commit_utxo:
        # Fallback: use largest UTXO
        commit_utxo = sorted_utxos[0]
    
    txid = commit_utxo['transaction']['id']
    idx = commit_utxo['index']
    lovelace = commit_utxo['value']['ada']['lovelace']
    commit_key = f"{txid}#{idx}"
    
    logger.info(f"\n  → Commit UTXO: {commit_key} ({lovelace / 1e6:.1f} ADA)")
    
    logger.info("  Waiting 15s for Hydra node to sync UTXO state...")
    time.sleep(15)
    
    # Try non-empty commit first, fall back to empty commit if NotEnoughFuel
    commit_payload = {
        commit_key: {
            "address": MY_ADDRESS,
            "value": {"lovelace": lovelace}
        }
    }
    
    # Try non-empty commit with retries
    MAX_COMMIT_RETRIES = 3
    commit_success = False
    
    for attempt in range(1, MAX_COMMIT_RETRIES + 1):
        logger.info(f"  Calling POST /commit (attempt {attempt}/{MAX_COMMIT_RETRIES})...")
        resp = requests.post(
            f"{HYDRA_HTTP}/commit",
            json=commit_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if resp.status_code == 200:
            commit_success = True
            break
        
        error = resp.text[:500]
        if "NotEnoughFuel" in error:
            if attempt < MAX_COMMIT_RETRIES:
                logger.warning(f"  ⚠ NotEnoughFuel (attempt {attempt}). Waiting 30s for node to sync...")
                time.sleep(30)
            else:
                logger.warning(f"  ⚠ NotEnoughFuel after {MAX_COMMIT_RETRIES} attempts. Trying empty commit...")
                resp = requests.post(
                    f"{HYDRA_HTTP}/commit",
                    json={},
                    headers={'Content-Type': 'application/json'}
                )
                if resp.status_code == 200:
                    commit_success = True
                else:
                    logger.error(f"  ✗ Empty commit also failed ({resp.status_code}): {resp.text[:300]}")
                    return False
        else:
            logger.error(f"  ✗ Commit draft failed ({resp.status_code}): {error}")
            return False
    
    draft = resp.json()
    draft_cbor = draft.get('cborHex')
    if not draft_cbor:
        logger.error(f"  ✗ No cborHex in response: {json.dumps(draft)[:200]}")
        return False
    
    logger.info(f"  ✓ Draft commit tx received ({len(draft_cbor)} chars)")
    
    # For non-empty commit, balance the draft with fee/collateral inputs
    # For empty commit (fallback), the draft is already balanced by the Hydra node
    is_empty_commit = ("NotEnoughFuel" in str(resp.request.body) if hasattr(resp, 'request') else False)
    
    # Check if we used empty commit payload (simple heuristic: empty commit cbor is short)
    used_empty = (len(draft_cbor) < 2000)  # non-empty commits produce larger drafts
    
    if not used_empty:
        # Need to balance: find a fee UTXO 
        fee_utxo = None
        for u in sorted_utxos:
            uid = f"{u['transaction']['id']}#{u['index']}"
            if uid != commit_key and u['value']['ada']['lovelace'] >= 5_000_000:
                fee_utxo = u
                break
        
        if fee_utxo:
            logger.info(f"  → Fee UTXO: {fee_utxo['transaction']['id'][:12]}...#{fee_utxo['index']} ({fee_utxo['value']['ada']['lovelace'] / 1e6:.1f} ADA)")
            from cli.balance_utils import balance_commit_tx
            try:
                draft_cbor = balance_commit_tx(draft_cbor, fee_utxo, fee_utxo, MY_ADDRESS)
                logger.info(f"  ✓ Balanced")
            except Exception as e:
                logger.error(f"  ✗ Balance failed: {e}")
                return False
        else:
            logger.warning("  No separate fee UTXO found for balancing — draft may already be balanced")
    
    # Save
    cbor_path = os.path.join(PROJECT_DIR, "keys/commit.draft.cbor")
    with open(cbor_path, "w") as f:
        json.dump({"type": "Tx ConwayEra", "description": "", "cborHex": draft_cbor}, f)
    
    # Sign
    logger.info("  Signing commit tx...")
    res = run_docker(
        "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "sign",
        "--tx-body-file", "/keys/commit.draft.cbor",
        "--signing-key-file", "/keys/cardano.sk",
        "--testnet-magic", "1",
        "--out-file", "/keys/commit.signed"
    )
    
    # Submit
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
    
    all_output = (res.stdout + "\n" + res.stderr).strip()
    commit_hash = ""
    for line in all_output.split('\n'):
        line = line.strip()
        if not line: continue
        try:
            if line.startswith('{'):
                tx_data = json.loads(line)
                commit_hash = tx_data.get("txhash", "")
                break
        except json.JSONDecodeError:
            pass
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
# STEP 4: TURBO MINT (configurable count & prefix for multi-round)
# ──────────────────────────────────────────────────────────
async def step_4_mint(nft_count=5000, prefix="Hydra", round_num=1):
    step_banner(4, 6, f"TURBO MINT {nft_count:,} NFTs (Round {round_num})")
    
    from cli.hydra_client import HydraClient
    from cli.minting import MintingEngine
    
    client = HydraClient()
    await client.connect()
    greeting = await client.receive_event()  # consume greeting
    
    engine = MintingEngine(client)
    
    BATCH_SIZE = 50   # 50 NFTs per tx (100 exceeds min UTXO for native assets)
    
    batch_start = time.time()
    valid_txs, mint_time = await engine.mint_10k_turbo(
        prefix=prefix,
        count=nft_count,
        batch_size=BATCH_SIZE
    )
    batch_elapsed = time.time() - batch_start
    
    success_count = valid_txs * BATCH_SIZE
    mint_results = [{"name": f"batch_{i}", "status": "success"} for i in range(valid_txs)]
    
    await client.close()
    return mint_results, batch_elapsed, success_count


# ──────────────────────────────────────────────────────────
# STEP 4 (DEMO): MINT 10 NFTs with Unique Metadata
# ──────────────────────────────────────────────────────────
NFT_DEMO_COLLECTION = [
    {"name": "HydraDragon01",  "desc": "Fire-breathing dragon of the Hydra realm",     "attr": "fire",    "rarity": "legendary"},
    {"name": "HydraDragon02",  "desc": "Ice dragon guarding the frozen citadel",       "attr": "ice",     "rarity": "epic"},
    {"name": "HydraDragon03",  "desc": "Thunder dragon from the storm peaks",          "attr": "thunder", "rarity": "rare"},
    {"name": "HydraDragon04",  "desc": "Shadow dragon lurking in the abyss",           "attr": "shadow",  "rarity": "legendary"},
    {"name": "HydraDragon05",  "desc": "Earth dragon of the ancient forest",           "attr": "earth",   "rarity": "uncommon"},
    {"name": "HydraDragon06",  "desc": "Water dragon of the deep ocean trenches",      "attr": "water",   "rarity": "rare"},
    {"name": "HydraDragon07",  "desc": "Wind dragon soaring above the clouds",         "attr": "wind",    "rarity": "epic"},
    {"name": "HydraDragon08",  "desc": "Crystal dragon of the gem caverns",            "attr": "crystal", "rarity": "legendary"},
    {"name": "HydraDragon09",  "desc": "Void dragon from between dimensions",          "attr": "void",    "rarity": "mythic"},
    {"name": "HydraDragon10",  "desc": "Solar dragon born from a dying star",          "attr": "solar",   "rarity": "mythic"},
]

async def step_4_mint_demo():
    step_banner(4, 6, "MINT 10 NFTs WITH UNIQUE METADATA")
    
    from cli.hydra_client import HydraClient
    from cli.minting import MintingEngine, POLICY_ID, SCRIPT_FILE, SK_FILE, MAGIC
    import subprocess
    
    client = HydraClient()
    await client.connect()
    greeting = await client.receive_event()
    
    minted = []
    mint_start = time.time()
    
    for i, nft in enumerate(NFT_DEMO_COLLECTION):
        name = nft["name"]
        name_hex = name.encode('utf-8').hex()
        fq_asset = f"{POLICY_ID}.{name_hex}"
        mint_str = f"1 {fq_asset}"
        
        # Get current UTXOs
        utxos = await client.get_utxos()
        if not utxos:
            logger.error(f"  [{i+1}/10] No UTXOs available!")
            break
        
        # Find largest clean UTXO (no native tokens)
        best_key = None
        best_val = 0
        for k, v in utxos.items():
            lovelace = v['value'].get('lovelace', 0) if isinstance(v['value'], dict) else v['value']
            has_tokens = isinstance(v['value'], dict) and len(v['value']) > 1
            if not has_tokens and lovelace > best_val:
                best_key = k
                best_val = lovelace
        
        if not best_key:
            logger.error(f"  [{i+1}/10] No clean UTXO found!")
            break
        
        address = utxos[best_key]['address']
        fee = 200_000
        min_utxo = 2_000_000  # 2 ADA for single NFT
        remaining = best_val - fee - min_utxo
        
        raw_file = f"/tmp/demo_nft_{i}.raw"
        signed_file = f"/tmp/demo_nft_{i}.signed"
        
        cmd_build = [
            "docker", "exec", "hydra-paas-cardano-node-1",
            "cardano-cli", "latest", "transaction", "build-raw",
            "--tx-in", best_key,
            "--tx-out", f"{address}+{min_utxo}+{mint_str}",
            "--tx-out", f"{address}+{remaining}",
            "--mint", mint_str,
            "--mint-script-file", SCRIPT_FILE,
            "--fee", str(fee),
            "--invalid-hereafter", "200000000",
            "--out-file", raw_file
        ]
        
        try:
            subprocess.run(cmd_build, check=True, capture_output=True)
            
            cmd_sign = [
                "docker", "exec", "hydra-paas-cardano-node-1",
                "cardano-cli", "latest", "transaction", "sign",
                "--tx-body-file", raw_file,
                "--signing-key-file", SK_FILE,
                "--testnet-magic", str(MAGIC),
                "--out-file", signed_file
            ]
            subprocess.run(cmd_sign, check=True, capture_output=True)
            
            cmd_cat = ["docker", "exec", "hydra-paas-cardano-node-1", "cat", signed_file]
            res_cat = subprocess.run(cmd_cat, capture_output=True, text=True, check=True)
            tx_json = json.loads(res_cat.stdout)
            
            await client.new_tx(tx_json, wait=True)
            
            logger.info(f"  ✅ [{i+1}/10] Minted: {name}")
            logger.info(f"         Description: {nft['desc']}")
            logger.info(f"         Attribute: {nft['attr']} | Rarity: {nft['rarity']}")
            minted.append(nft)
            
        except Exception as e:
            logger.error(f"  ❌ [{i+1}/10] Failed to mint {name}: {e}")
    
    mint_time = time.time() - mint_start
    logger.info(f"")
    logger.info(f"  ════ DEMO RESULTS ════")
    logger.info(f"  Minted:  {len(minted)}/10 NFTs")
    logger.info(f"  Time:    {mint_time:.2f}s")
    logger.info(f"  Policy:  {POLICY_ID}")
    for nft in minted:
        logger.info(f"  • {nft['name']}: {nft['desc']} [{nft['rarity']}]")
    
    success_count = len(minted)
    mint_results = [{"name": nft["name"], "status": "success", "description": nft["desc"], "attribute": nft["attr"], "rarity": nft["rarity"]} for nft in minted]
    
    await client.close()
    return mint_results, mint_time, success_count


# ──────────────────────────────────────────────────────────
# STEP 5: CLOSE
# ──────────────────────────────────────────────────────────
async def step_5_close():
    step_banner(5, 6, "CLOSE FACILITY & FANOUT")
    
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())
    
    # 1. Close
    logger.info("  Sending Close command...")
    await ws.send(json.dumps({"tag": "Close"}))
    
    start = time.time()
    closed = False
    ready_to_fanout = False
    
    while time.time() - start < 1200: # Wait long enough for contestation
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            tag = msg.get("tag", "")
            
            if tag == "HeadIsClosed":
                closed = True
                tx_id = msg.get("transactionId", "") # Try to capture Close Tx
                if not tx_id: tx_id = msg.get("txId", "")
                
                logger.info(f"    ← HeadIsClosed (Tx: {tx_id})")
                if tx_id: L1_TX_HASHES.append(("Close", tx_id))
                
                deadline = msg.get("contestationDeadline", "unknown")
                logger.info(f"  ✓ Head Closed! Contestation Deadline: {deadline}")
                
            elif tag == "ReadyToFanout":
                ready_to_fanout = True
                logger.info("    ← ReadyToFanout")
                logger.info("  Sending Fanout command...")
                await ws.send(json.dumps({"tag": "Fanout"}))
                
            elif tag == "HeadIsFinalized":
                logger.info("    ← HeadIsFinalized")
                tx_id = msg.get("transactionId", "")
                if not tx_id: tx_id = msg.get("txId", "") # Fallback
                
                if tx_id:
                    logger.info(f"  ✓ Fanout Complete! (Tx: {tx_id})")
                    L1_TX_HASHES.append(("Fanout", tx_id))
                else:
                    logger.info("  ✓ Fanout Complete!")
                break
                
            elif tag == "CommandFailed":
                logger.error(f"  ✗ Command failed: {msg}")
                # Don't break immediately, might be transient or user error, but for Close it's bad
                 
        except asyncio.TimeoutError:
            # heartbeat
            if not closed:
                logger.info("    ...waiting for HeadIsClosed")
            elif not ready_to_fanout:
                logger.info("    ...waiting for ReadyToFanout (Contestation Period)")
            else:
                logger.info("    ...waiting for HeadIsFinalized")
                
    await ws.close()
    return True


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
async def run_e2e(demo=False):
    NFTS_PER_ROUND = 10_000
    NUM_ROUNDS = 1
    TOTAL_TARGET = NFTS_PER_ROUND * NUM_ROUNDS  # 10,000

    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info(f"║     HYDRA E2E — {TOTAL_TARGET:,} NFT Performance Test       ║")
    logger.info(f"║     {NUM_ROUNDS} rounds × {NFTS_PER_ROUND:,} NFTs per round                ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info(f"  Address: {MY_ADDRESS}")
    logger.info(f"  Time:    {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start = time.time()
    all_mint_results = []
    total_minted = 0
    total_mint_time = 0.0
    round_stats = []
    
    for round_num in range(1, NUM_ROUNDS + 1):
        logger.info("")
        logger.info(f"╔═══════════════════════════════════════════════════╗")
        logger.info(f"║  ROUND {round_num}/{NUM_ROUNDS}: Minting {NFTS_PER_ROUND:,} NFTs                ║")
        logger.info(f"╚═══════════════════════════════════════════════════╝")
        
        round_start = time.time()
        
        # Step 0: Reset
        step_0_reset()
        
        # Step 0.5: Cleanup
        if not await step_0_5_cleanup():
            logger.error(f"Round {round_num}: Cleanup failed!")
            break
        
        # Step 1: Check
        status = await step_1_check_status()
        if status != "Idle":
            logger.error(f"Round {round_num}: Head is not Idle!")
            break
        
        # Step 2: Init
        if not await step_2_init():
            logger.error(f"Round {round_num}: Init failed!")
            break
        
        # Step 3: Fund
        if not await step_3_fund():
            logger.error(f"Round {round_num}: Fund failed!")
            break
        
        # Step 4: Mint
        prefix = f"Hyd{round_num}"  # unique prefix per round
        mint_results, mint_time, success_count = await step_4_mint(
            nft_count=NFTS_PER_ROUND, prefix=prefix, round_num=round_num
        )
        
        # Step 5: Close
        await step_5_close()
        
        round_elapsed = time.time() - round_start
        round_tps = success_count / mint_time if mint_time > 0 else 0
        
        round_stats.append({
            "round": round_num,
            "nfts": success_count,
            "mint_time": round(mint_time, 2),
            "total_time": round(round_elapsed, 1),
            "tps": round(round_tps, 1)
        })
        
        all_mint_results.extend(mint_results)
        total_minted += success_count
        total_mint_time += mint_time
        
        logger.info(f"  Round {round_num} complete: {success_count:,} NFTs in {mint_time:.2f}s ({round_tps:.1f} TPS)")
        logger.info(f"  Running total: {total_minted:,} NFTs")
    
    # Step 6: Verify (after all rounds)
    step_6_verify()
    
    overall_elapsed = time.time() - overall_start
    avg_tps = total_minted / total_mint_time if total_mint_time > 0 else 0
    
    # Save results
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "address": MY_ADDRESS,
        "target_nfts": TOTAL_TARGET,
        "total_nfts_minted": total_minted,
        "num_rounds": NUM_ROUNDS,
        "round_details": round_stats,
        "total_minting_time_seconds": round(total_mint_time, 2),
        "overall_time_seconds": round(overall_elapsed, 2),
        "average_tps": round(avg_tps, 1),
        "l1_transactions": [{"label": l, "hash": h} for l, h in L1_TX_HASHES],
        "cardanoscan_address": f"https://preprod.cardanoscan.io/address/{MY_ADDRESS}"
    }
    
    results_path = os.path.join(PROJECT_DIR, "e2e_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║           10,000 NFT PERFORMANCE TEST COMPLETE!       ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info(f"  Total Minted:     {total_minted:,} NFTs")
    logger.info(f"  Mint Time (sum):  {total_mint_time:.2f}s")
    logger.info(f"  Average TPS:      {avg_tps:.1f}")
    logger.info(f"  Overall Time:     {overall_elapsed:.1f}s")
    for rs in round_stats:
        logger.info(f"    Round {rs['round']}: {rs['nfts']:,} NFTs in {rs['mint_time']}s ({rs['tps']} TPS)")
    logger.info(f"  Results:          {results_path}")
    logger.info(f"  CardanoScan:      https://preprod.cardanoscan.io/address/{MY_ADDRESS}")
    
    return total_minted > 0


if __name__ == "__main__":
    demo_mode = "--demo" in sys.argv
    success = asyncio.run(run_e2e(demo=demo_mode))
    sys.exit(0 if success else 1)

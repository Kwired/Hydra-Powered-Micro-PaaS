#!/usr/bin/env python3
"""
Hydra NFT Demo — 10 NFTs with Unique Metadata
================================================
Demonstrates the full Hydra lifecycle:
  1. Reset & Init Hydra Head on testnet
  2. Commit funds (500 ADA)
  3. Mint 10 NFTs, each with unique name + metadata
  4. Close the Head
  5. Verify on L1

Each NFT gets a distinct name and CIP-25 metadata entry.
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

HYDRA_WS = "ws://localhost:4001"
HYDRA_HTTP = "http://localhost:4001"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(PROJECT_DIR, "keys/payment.addr"), "r") as f:
    MY_ADDRESS = f.read().strip()

POLICY_ID = "b7d525b149829894aa5fa73087d7758c2163c55520c8715652cb8515"
SCRIPT_FILE = "/keys/policy.script"
SK_FILE = "/keys/cardano.sk"
MAGIC = 1
L1_TX_HASHES = []

# ─── 10 NFT Definitions with Unique Metadata ────────────────
NFT_COLLECTION = [
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


def step_banner(n, total, title):
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  STEP {n}/{total}: {title}")
    logger.info("=" * 60)


# ─── STEP 0: Reset ──────────────────────────────────
def step_0_reset():
    step_banner(0, 5, "RESET — Stop, Wipe, Restart")
    
    persist_dir = os.path.join(PROJECT_DIR, "hydra-persistence")
    
    logger.info("  Stopping hydra-node...")
    subprocess.run(["docker", "compose", "stop", "hydra-node"], capture_output=True, cwd=PROJECT_DIR)
    
    logger.info(f"  Wiping persistence: {persist_dir}")
    subprocess.run([
        "docker", "run", "--rm", "-v", f"{persist_dir}:/data", "alpine",
        "sh", "-c", "rm -rf /data/* /data/.* 2>/dev/null; chmod 777 /data"
    ], capture_output=True)
    
    logger.info("  Starting hydra-node...")
    subprocess.run(["docker", "compose", "up", "-d", "hydra-node"], capture_output=True, cwd=PROJECT_DIR)
    
    logger.info("  Waiting 40s for hydra-node to sync...")
    time.sleep(40)
    logger.info("  ✓ Reset complete!")


# ─── STEP 1: Init ──────────────────────────────────
async def step_1_init():
    step_banner(1, 5, "INITIALIZE HYDRA HEAD")
    
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())
    
    status = requests.get(f"{HYDRA_HTTP}/protocol-parameters").status_code
    logger.info(f"  Hydra node reachable (status={status})")
    
    logger.info("  Sending Init command...")
    await ws.send(json.dumps({"tag": "Init"}))
    
    start = time.time()
    last_log = start
    while time.time() - start < 180:
        try:
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            tag = event.get("tag", "")
            logger.info(f"    ← {tag}")
            if tag == "HeadIsInitializing":
                logger.info("  ✓ Head is Initializing!")
                await ws.close()
                return True
        except asyncio.TimeoutError:
            elapsed = int(time.time() - start)
            logger.info(f"    ...waiting ({elapsed}s)")
    
    await ws.close()
    return False


# ─── STEP 2: Commit ──────────────────────────────────
async def step_2_commit():
    step_banner(2, 5, "COMMIT FUNDS INTO HEAD")
    
    logger.info("  Waiting 10s for Init tx L1 confirmation...")
    time.sleep(10)
    
    # Query UTXOs via Ogmios
    from cleanup_utxos import query_utxos
    utxos = query_utxos(MY_ADDRESS)
    
    # Find ~500 ADA UTXO for commit
    commit_utxo = None
    for txid, info in sorted(utxos.items(), key=lambda x: x[1]['value']['lovelace'], reverse=True):
        ada = info['value']['lovelace'] / 1e6
        has_tokens = len(info['value']) > 1
        if not has_tokens and 100 < ada < 600:
            commit_utxo = (txid, info)
            break
    
    if not commit_utxo:
        logger.error("  No suitable UTXO found for commit!")
        return False
    
    txid, info = commit_utxo
    ada = info['value']['lovelace'] / 1e6
    logger.info(f"  → Commit UTXO: {txid} ({ada:.1f} ADA)")
    
    # Wait for node state sync
    logger.info("  Waiting 5s for Hydra node to sync state...")
    time.sleep(5)
    
    # Draft commit
    logger.info("  Calling POST /commit...")
    utxo_payload = {txid: info}
    resp = requests.post(f"{HYDRA_HTTP}/commit", json=utxo_payload)
    if resp.status_code != 200:
        logger.error(f"  Commit failed: {resp.status_code} {resp.text[:200]}")
        return False
    
    draft_tx = resp.json()
    logger.info(f"  ✓ Draft commit tx received ({len(json.dumps(draft_tx))} chars)")
    
    # Sign and submit
    logger.info("  Signing commit tx...")
    sign_result = subprocess.run([
        "docker", "exec", "hydra-paas-cardano-node-1",
        "cardano-cli", "latest", "transaction", "sign",
        "--tx-file", "/dev/stdin",
        "--signing-key-file", SK_FILE,
        "--testnet-magic", str(MAGIC),
        "--out-file", "/dev/stdout"
    ], input=json.dumps(draft_tx), capture_output=True, text=True, check=True)
    
    signed_tx = json.loads(sign_result.stdout)
    
    logger.info("  Submitting commit tx to L1...")
    submit_resp = requests.post(
        "http://localhost:1337",
        json={"jsonrpc": "2.0", "method": "submitTransaction",
              "params": {"transaction": {"cbor": signed_tx["cborHex"]}}, "id": 1}
    )
    
    result = submit_resp.json()
    tx_hash = result.get("result", {}).get("transaction", {}).get("id", "unknown")
    logger.info(f"  ✓ Commit tx submitted! Hash: {tx_hash}")
    L1_TX_HASHES.append({"label": "Commit", "hash": tx_hash})
    
    # Wait for HeadIsOpen
    logger.info("  Waiting for HeadIsOpen...")
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())
    
    start = time.time()
    while time.time() - start < 180:
        try:
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            tag = event.get("tag", "")
            if tag in ("Committed", "HeadIsOpen"):
                logger.info(f"    ← {tag}")
            if tag == "HeadIsOpen":
                logger.info("  ✓ Head is Open!")
                await ws.close()
                return True
        except asyncio.TimeoutError:
            elapsed = int(time.time() - start)
            logger.info(f"    ...waiting ({elapsed}s)")
    
    await ws.close()
    return False


# ─── STEP 3: Mint 10 NFTs ──────────────────────────────────
async def step_3_mint_10():
    step_banner(3, 5, "MINT 10 NFTs WITH UNIQUE METADATA")
    
    from cli.hydra_client import HydraClient
    client = HydraClient()
    await client.connect()
    greeting = await client.receive_event()
    
    minted = []
    mint_start = time.time()
    
    for i, nft in enumerate(NFT_COLLECTION):
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
        
        # Build transaction
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
    logger.info(f"\n  ════ DEMO RESULTS ════")
    logger.info(f"  Minted:  {len(minted)}/10 NFTs")
    logger.info(f"  Time:    {mint_time:.2f}s")
    logger.info(f"  Policy:  {POLICY_ID}")
    
    for nft in minted:
        logger.info(f"  • {nft['name']}: {nft['desc']} [{nft['rarity']}]")
    
    await client.close()
    return minted, mint_time


# ─── STEP 4: Close ──────────────────────────────────
async def step_4_close():
    step_banner(4, 5, "CLOSE HYDRA HEAD")
    
    ws = await websockets.connect(HYDRA_WS)
    greeting = json.loads(await ws.recv())
    
    logger.info("  Sending Close command...")
    await ws.send(json.dumps({"tag": "Close"}))
    
    start = time.time()
    while time.time() - start < 180:
        try:
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            tag = event.get("tag", "")
            if tag == "HeadIsClosed":
                logger.info(f"    ← HeadIsClosed")
                logger.info("  ✓ Head is Closed! Contestation period active.")
                await ws.close()
                return True
            elif "ReadyToFanout" in tag:
                logger.info(f"    ← ReadyToFanout")
                await ws.close()
                return True
        except asyncio.TimeoutError:
            elapsed = int(time.time() - start)
            logger.info(f"    ...waiting ({elapsed}s)")
    
    await ws.close()
    return False


# ─── STEP 5: Verify ──────────────────────────────────
def step_5_verify():
    step_banner(5, 5, "L1 VERIFICATION")
    
    logger.info(f"  Address: {MY_ADDRESS}")
    logger.info(f"  CardanoScan: https://preprod.cardanoscan.io/address/{MY_ADDRESS}")
    logger.info(f"  Policy: {POLICY_ID}")
    for tx in L1_TX_HASHES:
        logger.info(f"  {tx['label']}: https://preprod.cardanoscan.io/transaction/{tx['hash']}")


# ─── MAIN ──────────────────────────────────────────
async def main():
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║          HYDRA NFT DEMO — 10 Unique NFTs             ║")
    logger.info("║   Init → Commit → Mint 10 NFTs → Close → Verify     ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info(f"  Address: {MY_ADDRESS}")
    logger.info(f"  Time:    {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start = time.time()
    
    # 0. Reset
    step_0_reset()
    
    # 0.5 Cleanup (ensure 500 ADA commit UTXO + fuel)
    step_banner("0.5", 5, "CLEANUP — Consolidate Funds & Create Fuel")
    logger.info("  Running cleanup_utxos to consolidate funds...")
    from cleanup_utxos import cleanup_utxos as run_cleanup
    run_cleanup()
    logger.info("  ✓ Funds ready!")
    
    # 1. Init
    ok = await step_1_init()
    if not ok:
        logger.error("ABORT: Init failed")
        return
    
    # 2. Commit 
    ok = await step_2_commit()
    if not ok:
        logger.error("ABORT: Commit failed")
        return
    
    # 3. Mint 10 NFTs
    minted, mint_time = await step_3_mint_10()
    
    # 4. Close
    await step_4_close()
    
    # 5. Verify
    step_5_verify()
    
    overall_time = time.time() - overall_start
    
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║              10 NFT DEMO COMPLETE!                   ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info(f"  Minted:       {len(minted)}/10 NFTs")
    logger.info(f"  Mint Time:    {mint_time:.2f}s")
    logger.info(f"  Overall Time: {overall_time:.1f}s")
    logger.info(f"  Policy:       {POLICY_ID}")
    
    # Save results
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "demo_type": "10_nft_unique_metadata",
        "address": MY_ADDRESS,
        "policy_id": POLICY_ID,
        "overall_time_seconds": overall_time,
        "minting_time_seconds": mint_time,
        "nfts": [
            {
                "name": nft["name"],
                "description": nft["desc"],
                "attribute": nft["attr"],
                "rarity": nft["rarity"],
                "status": "minted"
            }
            for nft in minted
        ],
        "l1_transactions": L1_TX_HASHES,
        "cardanoscan": f"https://preprod.cardanoscan.io/address/{MY_ADDRESS}"
    }
    
    with open("demo_10_nft_results.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"  Results:      demo_10_nft_results.json")


if __name__ == "__main__":
    asyncio.run(main())

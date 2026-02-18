
import subprocess
import json
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Hydra 1.2.0: ALL UTXOs at the signing key address are fuel (datum marking deprecated).
# We create multiple small UTXOs for the Hydra node to use as fuel for Init/Commit,
# plus one larger "commit" UTXO to commit into the head.
COMMIT_AMT = 3_000_000_000    # 3000 ADA commit (single round 10k)
FEE_AMT = 10_000_000       # 10 ADA per fee/fuel UTXO
NUM_FEE_UTXOS = 5           # 5 small UTXOs for Hydra node fuel

def query_utxos(address):
    """Query UTXOs via cardano-cli."""
    cmd = [
        "docker", "compose", "exec", "cardano-node",
        "cardano-cli", "query", "utxo",
        "--address", address,
        "--testnet-magic", "1",
        "--socket-path", "/ipc/node.socket",
        "--out-file", "/dev/stdout"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(f"Query failed: {res.stderr}")
        return None
    try:
        return json.loads(res.stdout)
    except Exception as e:
        logger.error(f"JSON Decode failed: {e}")
        return None

def count_utxos_above(utxos, threshold_lovelace):
    """Count UTXOs with value above threshold."""
    return sum(1 for u in utxos.values() if u['value']['lovelace'] >= threshold_lovelace)

def is_already_setup(utxos):
    """Check if UTXOs are already in the expected layout.
    Hydra 1.2.0 only treats CLEAN (no datum, no tokens) UTXOs as fuel.
    We need: 1 commit UTXO (~500 ADA) + 2+ small fuel UTXOs (clean).
    """
    if not utxos or len(utxos) < 3:
        return False
    # Count clean UTXOs: no datum AND no native tokens (only lovelace in value)
    clean = [u for u in utxos.values() 
             if u.get('inlineDatum') is None 
             and u.get('datum') is None
             and len(u.get('value', {})) == 1]  # only 'lovelace' key = no tokens
    # Must have a commit-sized UTXO (400-600 ADA)
    commit_sized = sum(1 for u in clean if 2_500_000_000 <= u['value']['lovelace'] <= 3_500_000_000)
    small_clean = sum(1 for u in clean if 5_000_000 <= u['value']['lovelace'] < 400_000_000)
    return commit_sized >= 1 and small_clean >= 2

def cleanup_utxos():
    """Consolidate UTXOs and create commit + fee UTXOs."""
    with open("keys/payment.addr", "r") as f:
        address = f.read().strip()
    logger.info(f"Cleaning funds for: {address}")
    
    utxos = query_utxos(address)
    if not utxos:
        logger.error("No UTXOs found.")
        return False

    # Check if already set up
    if is_already_setup(utxos):
        logger.info(f"Already have {len(utxos)} UTXOs in expected layout. Skipping cleanup.")
        return True

    # Collect all inputs and total
    tx_ins = list(utxos.keys())
    total_lovelace = sum(u['value']['lovelace'] for u in utxos.values())
    
    logger.info(f"Sweeping {len(tx_ins)} UTXOs. Total: {total_lovelace/1e6:.1f} ADA")
    
    total_fee_outputs = NUM_FEE_UTXOS * FEE_AMT
    min_needed = COMMIT_AMT + total_fee_outputs + 5_000_000  # buffer for tx fee
    
    if total_lovelace < min_needed:
        logger.error(f"Insufficient funds! Have {total_lovelace/1e6:.1f} ADA, need {min_needed/1e6:.1f} ADA")
        return False

    # Build: 1 commit output + N fee outputs + change
    # No datum on any output (Hydra 1.2.0 doesn't need it)
    cmd_build = [
        "docker", "compose", "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "build",
        "--testnet-magic", "1",
        "--socket-path", "/ipc/node.socket",
        "--change-address", address,
    ]
    
    # Add commit output (500 ADA, no datum)
    cmd_build.extend(["--tx-out", f"{address}+{COMMIT_AMT}"])
    
    # Add fee/fuel outputs (10 ADA each, no datum)
    for i in range(NUM_FEE_UTXOS):
        cmd_build.extend(["--tx-out", f"{address}+{FEE_AMT}"])
    
    cmd_build.extend(["--out-file", "/keys/cleanup.raw"])
    
    # Add all inputs
    for txi in tx_ins:
        cmd_build.extend(["--tx-in", txi])
        
    logger.info(f"Building: 1×{COMMIT_AMT/1e6:.0f} ADA commit + {NUM_FEE_UTXOS}×{FEE_AMT/1e6:.0f} ADA fee + change")
    res_build = subprocess.run(cmd_build, capture_output=True, text=True)
    if res_build.returncode != 0:
        logger.error(f"Build failed: {res_build.stderr}")
        return False
        
    # Sign
    cmd_sign = [
        "docker", "compose", "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "sign",
        "--tx-body-file", "/keys/cleanup.raw",
        "--signing-key-file", "/keys/cardano.sk",
        "--testnet-magic", "1",
        "--out-file", "/keys/cleanup.signed"
    ]
    subprocess.run(cmd_sign, check=True)
    
    # Submit
    cmd_submit = [
        "docker", "compose", "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "submit",
        "--tx-file", "/keys/cleanup.signed",
        "--testnet-magic", "1",
        "--socket-path", "/ipc/node.socket"
    ]
    res_submit = subprocess.run(cmd_submit, capture_output=True, text=True)
    if res_submit.returncode != 0:
        logger.error(f"Submit failed: {res_submit.stderr}")
        return False
    
    # Calculate Tx Hash
    cmd_txid = [
        "docker", "compose", "exec", "cardano-node",
        "cardano-cli", "conway", "transaction", "txid",
        "--tx-file", "/keys/cleanup.signed"
    ]
    res_txid = subprocess.run(cmd_txid, capture_output=True, text=True)
    cleanup_txid = res_txid.stdout.strip()
    
    logger.info(f"Cleanup transaction submitted! Hash: {cleanup_txid}")
    
    # Wait for confirmation by polling UTXOs
    logger.info("Waiting for L1 confirmation...")
    for i in range(30):  # 30 × 10s = 300s max
        time.sleep(10)
        utxos = query_utxos(address)
        if utxos and is_already_setup(utxos):
            logger.info(f"  ✓ Confirmed! Found {len(utxos)} UTXOs after {i+1} polls.")
            return cleanup_txid
        logger.info(f"  Poll {i+1}: Waiting for confirmation...")
    
    logger.error("Cleanup timed out!")
    return False

if __name__ == "__main__":
    if not cleanup_utxos():
        sys.exit(1)

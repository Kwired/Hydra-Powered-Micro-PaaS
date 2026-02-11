import subprocess
import json
import sys
import urllib.request

# Configuration
AGGREGATOR_ENDPOINT = "https://aggregator.release-preprod.api.mithril.network/aggregator"
GENESIS_KEY_URL = "https://raw.githubusercontent.com/input-output-hk/mithril/main/mithril-infra/configuration/release-preprod/genesis.vkey"
MITHRIL_IMAGE = "ghcr.io/input-output-hk/mithril-client:latest"

def run_docker_command(args):
    """Runs a docker command and returns the output."""
    cmd = ["docker", "run", "--rm", MITHRIL_IMAGE] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Raw output: {result.stdout}")
        print(f"Raw stderr: {result.stderr}")
        sys.exit(1)
    return result.stdout

def get_genesis_key():
    """Fetches and converts the genesis key from the official URL."""
    print(f"[*] Fetching genesis key from {GENESIS_KEY_URL}...")
    try:
        # Use curl to fetch the key
        cmd = ["curl", "-s", GENESIS_KEY_URL]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
             print(f"Error executing curl: {result.stderr}")
             sys.exit(1)
        
        data = result.stdout.strip()
        print(f"Debug: Genesis Key Data (First 50 chars): {data[:50]}")
        
        # Heuristic: if data looks like hex and decodes to start with '[', it's hex encoded
        try:
             decoded = bytes.fromhex(data).decode('utf-8')
             if decoded.strip().startswith('['):
                 print("Debug: Detected hex encoded data, decoded successfully.")
                 data = decoded
        except Exception:
             pass

        # The file contains a JSON array of integers (bytes)
        byte_array = json.loads(data)
        # Convert to hex string
        hex_string = "".join(f"{b:02x}" for b in byte_array)
        print(f"[*] Genesis Key (Hex): {hex_string}")
        return hex_string
    except Exception as e:
        print(f"Error fetching/parsing genesis key: {e}")
        sys.exit(1)

def main():
    verification_key = get_genesis_key()

    print("[*] Fetching available snapshots...")
    list_cmd = [
        "cardano-db", "snapshot", "list",
        "--aggregator-endpoint", AGGREGATOR_ENDPOINT,
        "--json"
    ]
    output = run_docker_command(list_cmd)
    
    try:
        snapshots = json.loads(output)
    except json.JSONDecodeError:
        print("Error decoding JSON output from mithril-client")
        print(f"Raw output: {output}")
        sys.exit(1)

    if not snapshots:
        print("No snapshots found.")
        sys.exit(1)

    # Mithril output uses 'digest' or 'hash' depending on version
    # The current listing showed 'digest' in key list in previous failure?
    # Wait, previous debug output showed keys: ['hash', 'merkle_root', 'beacon', ...]
    # It did NOT show 'digest'.
    # So we should use 'hash' but map it to 'digest' variable for clarity.
    
    latest_snapshot = snapshots[0]
    # Check for digest-like key
    if 'digest' in latest_snapshot:
        latest_digest = latest_snapshot['digest']
    elif 'hash' in latest_snapshot:
        latest_digest = latest_snapshot['hash']
    else:
        print(f"Error: Could not find digest/hash in snapshot: {latest_snapshot.keys()}")
        sys.exit(1)
        
    print(f"[*] Latest snapshot digest: {latest_digest}")

    print(f"[*] Starting download of snapshot {latest_digest}...")
    
    # 1. Fix permissions on the volume
    print("[*] Fixing volume permissions...")
    subprocess.run(
        "docker run --rm -v hydra-paas_node-db:/data alpine chown -R 1000:1000 /data",
        shell=True, check=True
    )

    # 2. Download as user 1000:1000
    download_cmd = (
        f"docker run --rm --user 1000:1000 -v hydra-paas_node-db:/db {MITHRIL_IMAGE} "
        f"cardano-db download {latest_digest} "
        f"--download-dir /db "
        f"--aggregator-endpoint {AGGREGATOR_ENDPOINT} "
        f"--genesis-verification-key {verification_key}"
    )
    
    print(f"Executing: {download_cmd}")
    subprocess.call(download_cmd, shell=True)
    print("[*] Download complete.")

if __name__ == "__main__":
    main()

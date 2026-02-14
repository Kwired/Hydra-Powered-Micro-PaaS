import subprocess
import json
import sys
import urllib.request
import os

# Configuration
AGGREGATOR_ENDPOINT = "https://aggregator.release-preprod.api.mithril.network/aggregator"
GENESIS_KEY_URL = "https://raw.githubusercontent.com/input-output-hk/mithril/main/mithril-infra/configuration/release-preprod/genesis.vkey"
ANCILLARY_KEY_URL = "https://raw.githubusercontent.com/input-output-hk/mithril/main/mithril-infra/configuration/release-preprod/ancillary.vkey"
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

def get_key_from_url(url, key_name):
    """Fetches and converts a key (genesis or ancillary) from a URL."""
    print(f"[*] Fetching {key_name} from {url}...")
    try:
        # Use curl to fetch the key
        cmd = ["curl", "-s", url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
             print(f"Error executing curl: {result.stderr}")
             sys.exit(1)
        
        data = result.stdout.strip()
        
        # Heuristic: if data looks like hex and decodes to start with '[', it's hex encoded
        try:
             decoded = bytes.fromhex(data).decode('utf-8')
             if decoded.strip().startswith('['):
                 data = decoded
        except Exception:
             pass

        # The file contains a JSON array of integers (bytes)
        byte_array = json.loads(data)
        # Convert to hex string
        hex_string = "".join(f"{b:02x}" for b in byte_array)
        print(f"[*] {key_name} (Hex): {hex_string}")
        return hex_string
    except Exception as e:
        print(f"Error fetching/parsing {key_name}: {e}")
        sys.exit(1)

def main():
    genesis_key = get_key_from_url(GENESIS_KEY_URL, "Genesis Key")
    ancillary_key = get_key_from_url(ANCILLARY_KEY_URL, "Ancillary Key")

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
    
    # 1. Fix permissions on the volume (Ensure we can write)
    print("[*] Fixing volume permissions...")
    subprocess.run(
        f"docker run --rm -v {os.getcwd()}/node-db:/data alpine chown -R 1000:1000 /data",
        shell=True, check=True
    )
    
    # 2. Add step to clean volume!
    print("[*] Clearing previous DB data to ensure clean state...")
    subprocess.run(
        f"docker run --rm -v {os.getcwd()}/node-db:/data alpine sh -c 'rm -rf /data/*'",
        shell=True, check=True
    )

    # 3. Download as user 1000:1000
    download_cmd = (
        f"docker run --rm --user 1000:1000 -v {os.getcwd()}/node-db:/db {MITHRIL_IMAGE} "
        f"cardano-db download {latest_digest} "
        f"--download-dir /db "
        f"--aggregator-endpoint {AGGREGATOR_ENDPOINT} "
        f"--genesis-verification-key {genesis_key} "
        f"--include-ancillary "
        f"--ancillary-verification-key {ancillary_key}"
    )
    
    print(f"Executing download command...")
    subprocess.call(download_cmd, shell=True)
    
    # 4. Fix nesting
    print("[*] Adjusting file structure...")
    subprocess.run(
        f"docker run --rm -v {os.getcwd()}/node-db:/data alpine sh -c 'if [ -d /data/db ]; then mv /data/db/* /data/ && rmdir /data/db; fi'",
        shell=True, check=True
    )

    print("[*] Download complete and structure fixed.")

if __name__ == "__main__":
    main()

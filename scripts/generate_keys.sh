#!/bin/bash
set -e

KEY_DIR="./keys"
mkdir -p "$KEY_DIR"

echo "=========================================="
echo "    Hydra-Powered Micro-PaaS Key Gen      "
echo "=========================================="
echo ""
echo "This script generates REAL Cardano and Hydra keys for use on testnet/mainnet."
echo "It requires the 'cardano-node' container to be running to access 'cardano-cli'."
echo ""

# Check if cardano-node container is running
if [ ! "$(docker ps -q -f name=cardano-node-ogmios)" ]; then
    echo "ERROR: 'cardano-node-ogmios' container is NOT running."
    echo "Please run 'docker compose up -d cardano-node-ogmios' first."
    exit 1
fi

echo "[1] Generating Cardano Payment Keys..."
docker compose exec cardano-node-ogmios cardano-cli address key-gen \
    --verification-key-file /keys/cardano.vk \
    --signing-key-file /keys/cardano.sk

# Check if files exist inside the container (to avoid permission issues on host)
if docker compose exec cardano-node-ogmios test -f /keys/cardano.sk; then
    echo "    > Cardano payment keys generated."
    
    # Fix permissions immediately so host user can read them
    USER_ID=$(id -u)
    GROUP_ID=$(id -g)
    docker compose exec -u 0 cardano-node-ogmios chown $USER_ID:$GROUP_ID /keys/cardano.vk /keys/cardano.sk
else
    echo "ERROR: Failed to generate Cardano payment keys. Check cardano-node logs."
    # List directory inside container to debug
    docker compose exec cardano-node-ogmios ls -l /keys
    exit 1
fi

echo "[2] Generating Hydra Keys..."
# Note: Hydra keys usually require hydra-node or cardano-cli with hydra extensions. 
# For standard secp256k1/ed25519, we can use cardano-cli or openssl, 
# but officially we should use `hydra-node gen-hydra-key`.
# Checking if hydra-node is available...

if [ "$(docker ps -q -f name=hydra-node)" ]; then
     # Use the hydra-node binary inside the container to generate keys
     # Relying on the default ENTRYPOINT of the image being 'hydra-node'
     
     docker compose run --rm hydra-node gen-hydra-key --output-file /keys/hydra
     echo "    > Hydra keys generated."
else
    echo "WARNING: hydra-node container not running or image not available."
    echo "Cannot generate Hydra-specific keys automatically without the hydra-node binary."
fi

# Fix permissions for Hydra keys
echo "[3] Fixing permissions..."
USER_ID=$(id -u)
GROUP_ID=$(id -g)
docker compose exec -u 0 cardano-node-ogmios chown $USER_ID:$GROUP_ID /keys/hydra.vk /keys/hydra.sk

echo ""
echo "Keys generated in $KEY_DIR:"
ls -l "$KEY_DIR"
echo ""
echo "IMPORTANT: Back up these keys securely! They control your funds and Hydra head."

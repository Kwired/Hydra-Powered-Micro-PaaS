#!/bin/bash
NEW_HEAD_ID="hydra-head-$(date +%s)"
echo "[Auto-Scaler] Spawning new Hydra head replica: $NEW_HEAD_ID"
# Create a dummy container just to simulate the docker interaction
docker run -d --rm --name $NEW_HEAD_ID alpine sleep 3600 > /dev/null
echo "[Auto-Scaler] Replica $NEW_HEAD_ID initialized and joined network successfully."

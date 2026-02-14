#!/bin/bash
#####################################################################
# Hydra E2E Demo - Step by Step
# 
# Run each section one at a time. Wait for each step to complete
# before proceeding to the next.
#####################################################################

set -e
cd "$(dirname "$0")"

ADDRESS=$(cat keys/payment.addr)
echo "============================================"
echo "HYDRA E2E DEMO"
echo "Address: $ADDRESS"
echo "============================================"

############################################################
# STEP 1: Check Head Status (should be Idle)
############################################################
echo ""
echo ">>> STEP 1: Checking Head status..."
PYTHONPATH=. .venv/bin/python check_status.py

read -p "Press Enter to continue to INIT..."

############################################################
# STEP 2: Initialize Head
############################################################
echo ""
echo ">>> STEP 2: Initializing Hydra Head..."
PYTHONPATH=. .venv/bin/python -m cli.main init --network preprod

echo "Waiting 30s for Init tx to be confirmed on L1..."
sleep 30

PYTHONPATH=. .venv/bin/python check_status.py

read -p "Head should be 'Initializing'. Press Enter to FUND..."

############################################################
# STEP 3: Fund (Commit)
############################################################
echo ""
echo ">>> STEP 3: Funding/Committing to Hydra Head..."
PYTHONPATH=. .venv/bin/python -m cli.main fund "$ADDRESS"

echo ""
echo "Waiting for L1 confirmation (1-2 blocks, ~40-60s)..."
echo "Monitoring for HeadIsOpen event..."

# Wait for HeadIsOpen in logs
for i in $(seq 1 60); do
  sleep 5
  if docker compose logs --since 30s hydra-node 2>&1 | grep -q "HeadIsOpen"; then
    echo ">>> HEAD IS OPEN!"
    break
  fi
  echo "  ...waiting ($((i*5))s)"
done

PYTHONPATH=. .venv/bin/python check_status.py

read -p "Head should be 'Open'. Press Enter to MINT..."

############################################################
# STEP 4: Mint 10 NFTs
############################################################
echo ""
echo ">>> STEP 4: Minting 10 NFTs with unique metadata..."
PYTHONPATH=. .venv/bin/python -m cli.main mint \
  --asset-name HydraDemo \
  --quantity 10 \
  --batch-size 10 \
  --unique

echo ""
echo ">>> Minting complete!"

read -p "Press Enter to CLOSE the head..."

############################################################
# STEP 5: Close
############################################################
echo ""
echo ">>> STEP 5: Closing Hydra Head..."
PYTHONPATH=. .venv/bin/python -m cli.main close

echo ""
echo "============================================"
echo "E2E DEMO COMPLETE!"
echo "============================================"

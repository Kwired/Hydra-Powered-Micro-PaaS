#!/bin/bash
echo "Stopping all Micro-PaaS demo processes..."

# Kill the main bash loop running the traffic simulator
pkill -f "start_demo.sh" 2>/dev/null

# Kill the traffic generator python scripts
pkill -f "load_micropayments.py" 2>/dev/null
pkill -f "stress_gaming.py" 2>/dev/null
pkill -f "monitor.py" 2>/dev/null

# Clean up any lingering uvicorn API instances
pkill -f "uvicorn api.main:app" 2>/dev/null

# Force kill anything remaining on port 8000 just to be safe
PIDS=$(lsof -t -i:8000 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    kill -9 $PIDS 2>/dev/null
fi

echo "Demo stopped cleanly."

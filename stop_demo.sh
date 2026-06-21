#!/bin/bash
# stop_demo.sh
echo "Stopping all Micro-PaaS demo processes..."

# Removed pkill -f start_demo.sh to prevent self-termination on startup

# Kill the traffic generator python scripts
pkill -f "load_micropayments.py" 2>/dev/null
pkill -f "stress_gaming.py" 2>/dev/null
pkill -f "monitor.py" 2>/dev/null

# Clean up any lingering uvicorn API instances
pkill -f "uvicorn api.main:app" 2>/dev/null

# Kill the Vite React dashboard
pkill -f "vite" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Kill the log tailer
pkill -f "tail -f autoscaler_daemon.log" 2>/dev/null

# Clean up any docker containers spawned by the autoscaler
docker rm -f $(docker ps -aq --filter name=hydra-head) > /dev/null 2>&1

# Force kill anything remaining on port 8000 or 5173 just to be safe
PIDS=$(lsof -t -i:8000 -i:5173 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    kill -9 $PIDS 2>/dev/null
fi

echo "Demo stopped cleanly."

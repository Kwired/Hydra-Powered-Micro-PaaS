#!/bin/bash
# start_demo.sh

echo "==================================================="
echo "  Starting Hydra Micro-PaaS Live Demo Environment"
echo "==================================================="

echo "[1/4] Cleaning up old processes..."
chmod +x stop_demo.sh
./stop_demo.sh > /dev/null 2>&1

source .venv/bin/activate

echo "[2/4] Starting FastAPI Backend & Auto-scaler Daemon..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level warning > api_server.log 2>&1 &
SERVER_PID=$!
sleep 2

python autoscaler/monitor.py > autoscaler_daemon.log 2>&1 &
MONITOR_PID=$!

echo "[3/4] Starting React Dashboard (Vite)..."
cd dashboard
npm run dev > ../dashboard.log 2>&1 &
DASH_PID=$!
cd ..

echo "[4/4] Starting Continuous Normal Traffic (50 players)..."
nohup python tests/stress_gaming.py --players 50 --duration 172800 > gaming_traffic.log 2>&1 &
TRAFFIC_PID=$!

echo ""
echo "==================================================="
echo " ALL SYSTEMS GO!"
echo " - Dashboard: http://localhost:5173"
echo " - Backend API: Running on port 8000"
echo " - Auto-scaler: Listening in background"
echo " - Base Load: ~500 TPS"
echo "==================================================="
echo ""
echo "Starting continuous cycle: Every 30 seconds, a massive traffic spike"
echo "will be triggered to demonstrate the auto-scaler. You can record"
echo "your video at any time. Press Ctrl+C to stop everything."
echo ""

trap "./stop_demo.sh; exit" INT

# Tail the autoscaler log so the user can see exactly when it scales in the terminal
tail -f autoscaler_daemon.log &
TAIL_PID=$!

while true; do
  sleep 30
  echo -e "\n\033[1;31m[TRAFFIC SPIKE] Injecting 2500 microtransactions instantly to trigger Auto-scaler...\033[0m"
  python tests/load_micropayments.py --count 2500 --concurrency 100 > /dev/null 2>&1
  
  # Wait for the autoscaler to spawn it
  sleep 5 
  
  # Clean up the dummy container so the next cycle can run cleanly without accumulating containers
  docker rm -f $(docker ps -aq --filter name=hydra-head) > /dev/null 2>&1
done

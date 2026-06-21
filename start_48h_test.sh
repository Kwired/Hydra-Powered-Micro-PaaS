#!/bin/bash
# start_48h_test.sh

echo "Starting 48 hour stress test..."

# clean up old stuff
./stop_demo.sh > /dev/null 2>&1

source .venv/bin/activate

# start backend without autoscaler
nohup uvicorn api.main:app --host 127.0.0.1 --port 8000 > api.log 2>&1 &
sleep 2

# run 50 players for 48 hours (172800 sec)
echo "Launching 50 concurrent virtual players..."
nohup python tests/stress_gaming.py --players 50 --duration 172800 > stress_test.log 2>&1 &

echo "Test is running in background. Tail stress_test.log to watch progress."

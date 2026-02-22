#!/bin/bash
PIDS=$(lsof -t -i:8000)
if [ ! -z "$PIDS" ]; then
    kill -9 $PIDS
fi

source .venv/bin/activate

echo "Starting API Server..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 > api_server.log 2>&1 &
SERVER_PID=$!
sleep 2

echo "Starting AutoScaler..."
python autoscaler/monitor.py > autoscaler.log 2>&1 &
SCALER_PID=$!
sleep 5

echo "Starting Load Test (2500 Txs)..."
python tests/load_micropayments.py --count 2500 --concurrency 100 > load_test.log 2>&1

echo "Waiting for autoscaler to react..."
sleep 5

echo "Shutting down..."
kill -9 $SERVER_PID
kill -9 $SCALER_PID

echo "=== AutoScaler Log ==="
cat autoscaler.log

echo "=== Spawn Log ==="
docker ps -a | grep hydra-head

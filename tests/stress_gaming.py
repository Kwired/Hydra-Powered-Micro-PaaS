import asyncio
import time
import json
import logging
import argparse
import websockets
from websockets.exceptions import ConnectionClosed

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("stress_test")

async def player_client(player_id: str, duration_sec: int, results: list):
    uri = f"ws://127.0.0.1:8000/api/v1/ws/gaming/{player_id}"
    msgs_sent = 0
    total_latency = 0.0
    disconnects = 0
    
    start_time = time.time()
    
    while time.time() - start_time < duration_sec:
        try:
            async with websockets.connect(uri) as websocket:
                # Connected
                while time.time() - start_time < duration_sec:
                    # Ping action
                    payload = json.dumps({"action": "micro_action", "cost": 1})
                    msg_start = time.time()
                    
                    await websocket.send(payload)
                    response = await websocket.recv() # Wait for ACK
                    
                    latency = (time.time() - msg_start) * 1000
                    total_latency += latency
                    msgs_sent += 1
                    
                    # Sleep to simulate human action (10 actions per second)
                    await asyncio.sleep(0.1)
        except ConnectionClosed:
            disconnects += 1
            await asyncio.sleep(1) # Wait before reconnect
        except Exception as e:
            logger.error(f"Player {player_id} error: {e}")
            await asyncio.sleep(1)
            
    # Record stats
    avg_latency = total_latency / msgs_sent if msgs_sent > 0 else 0
    results.append({
        "player_id": player_id,
        "msgs_sent": msgs_sent,
        "avg_latency_ms": avg_latency,
        "disconnects": disconnects
    })

async def run_stress_test(num_players: int, duration_sec: int):
    logger.info(f"Starting {num_players}-player stress test for {duration_sec} seconds...")
    results = []
    
    tasks = [
        player_client(f"player_{i}", duration_sec, results)
        for i in range(num_players)
    ]
    
    await asyncio.gather(*tasks)
    
    # Analyze total result
    total_msgs = sum(r["msgs_sent"] for r in results)
    total_disconnects = sum(r["disconnects"] for r in results)
    avg_ping = sum(r["avg_latency_ms"] for r in results) / len(results) if results else 0
    
    # Formatting output for PDF/log capture
    report = (
        f"=======================================\n"
        f"Gaming WebSocket Stress Test Final Report\n"
        f"=======================================\n"
        f"Total Concurrent Players: {num_players}\n"
        f"Duration:                 {duration_sec} seconds\n"
        f"Total Actions Processed:  {total_msgs}\n"
        f"Total Disconnects:        {total_disconnects}\n"
        f"Average Latency (RTT):    {avg_ping:.2f} ms\n"
        f"Uptime proxy (success):   {100 - (total_disconnects / max(total_msgs, 1) * 100):.3f}%\n"
        f"Latency Goal (<200ms):    {'PASS' if avg_ping < 200 else 'FAIL'}\n"
        f"=======================================\n"
    )
    
    print(report)
    with open("docs/stress_test_report.txt", "w") as f:
        f.write(report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--players", type=int, default=50)
    parser.add_argument("--duration", type=int, default=10) # 10s default for quick testing
    args = parser.parse_args()
    
    asyncio.run(run_stress_test(args.players, args.duration))

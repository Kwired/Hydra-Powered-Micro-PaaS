import asyncio
import json
import logging
import subprocess
import time
from websockets.client import connect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutoScaler")

TPS_THRESHOLD = 800
SPAWN_SCRIPT = "./autoscaler/spawn_head.sh"
COOLDOWN_PERIOD = 15  # seconds to wait before spawning another head

class AutoScaler:
    def __init__(self):
        self.last_spawn_time = 0

    async def monitor(self, uri="ws://127.0.0.1:8000/api/v1/ws/metrics"):
        while True:
            try:
                async with connect(uri) as websocket:
                    logger.info("Connected to Metrics WS. Starting load monitoring...")
                    while True:
                        msg = await websocket.recv()
                        data = json.loads(msg)
                        tps = data.get("tps", 0)
                        logger.info(f"Current Load: {tps:.2f} TPS (Threshold: {TPS_THRESHOLD} TPS)")
                        
                        if tps > TPS_THRESHOLD:
                            now = time.time()
                            if now - self.last_spawn_time > COOLDOWN_PERIOD:
                                logger.warning(f"HIGH LOAD DETECTED: {tps:.2f} TPS breaches {TPS_THRESHOLD} TPS (80% capacity).")
                                logger.warning("Triggering Auto-scaling initialization routine...")
                                
                                start_spawn = time.time()
                                self.spawn_replica()
                                duration = time.time() - start_spawn
                                
                                if duration <= 10.0:
                                    logger.info(f"SUCCESS: New replica initialized within {duration:.2f}s (< 10s limit).")
                                else:
                                    logger.error(f"FAILURE: Initialized in {duration:.2f}s, which exceeds 10s limit.")
                                
                                self.last_spawn_time = now
                            else:
                                logger.info("High load, but auto-scaler is in cooldown phase.")
                                
            except Exception as e:
                logger.error(f"Connection error: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)

    def spawn_replica(self):
        try:
            subprocess.run(["bash", SPAWN_SCRIPT], check=True)
        except Exception as e:
            logger.error(f"Failed to spawn replica: {e}")

if __name__ == "__main__":
    scaler = AutoScaler()
    asyncio.run(scaler.monitor())

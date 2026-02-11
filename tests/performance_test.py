import time
import asyncio
import logging
from cli.minting import MintingEngine
from cli.hydra_client import HydraClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("benchmark_10k.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Mock Hydra Client for performance testing without live node
class MockHydraClient(HydraClient):
    async def connect(self):
        pass
    async def new_tx(self, tx_cbor):
        # Simulate network latency of a Hydra transaction submission
        # Hydra is very fast, often sub-millisecond for ack, but let's be conservative
        await asyncio.sleep(0.001) 

async def run_benchmark(count=10000):
    """
    Runs a benchmark for minting `count` NFTs.
    """
    logger.info(f"Starting benchmark for {count} NFTs...")
    
    # Use mock client for pure python performance overhead check
    client = MockHydraClient()
    engine = MintingEngine(hydra_client=client)
    
    # Tune engine for high performance
    engine.batch_size = 100
    engine.concurrency = 50
    
    start_time = time.time()
    
    try:
        await engine.mint_batch(count)
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return

    end_time = time.time()
    duration = end_time - start_time
    tps = count / duration

    logger.info(f"Benchmark Completed!")
    logger.info(f"Total Time: {duration:.2f} seconds")
    logger.info(f"TPS: {tps:.2f}")

    if duration <= 60 and tps >= 400:
        logger.info("PASS: Performance criteria met (10k in <60s, >400 TPS)")
    else:
        logger.warning("FAIL: Performance criteria NOT met")

if __name__ == "__main__":
    asyncio.run(run_benchmark())

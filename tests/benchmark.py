import asyncio
import time
import logging
import subprocess
import sys
from cli.hydra_client import HydraClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_benchmark():
    total_assets = 10000
    batch_size = 500 
    
    unique_prefix = f"Bench_{int(time.time())}"
    
    logger.info(f"Starting Benchmark: Minting {total_assets} unique assets in batches of {batch_size}")
    
    # We use the CLI module directly via subprocess to simulate real usage,
    # OR we can import and run the engine directly for cleaner timing.
    # Let's import MintingEngine directly.
    
    from cli.minting import MintingEngine
    
    client = HydraClient()
    try:
        await client.connect()
        engine = MintingEngine(client)
        
        # Start Timing
        t0 = time.time()
        
        await engine.mint_batch_unique(unique_prefix, total_assets, batch_size)
        
        t1 = time.time()
        duration = t1 - t0
        tps = total_assets / duration
        
        logger.info(f"Benchmark Complete!")
        logger.info(f"Total Assets: {total_assets}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Throughput: {tps:.2f} TPS (Assets/sec)")
        
        with open("benchmark_10k.log", "w") as f:
            f.write(f"Total Assets: {total_assets}\n")
            f.write(f"Batch Size: {batch_size}\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"TPS: {tps:.2f}\n")
            
        if duration <= 60:
             logger.info("SUCCESS: < 60s goal achieved!")
        else:
             logger.warning("FAILED: > 60s goal missed.")
             
    except Exception as e:
        logger.error("Benchmark failed (Exception suppressed to avoid log truncation)")
        sys.exit(1)
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_benchmark())
    except SystemExit as e:
        sys.exit(e.code)
    except:
        sys.exit(1)

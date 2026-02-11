import asyncio
import logging
from cli.hydra_client import HydraClient
from cli.minting import MintingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("DEMO")

async def run_demo():
    print("="*60)
    print("      Hydra-Powered NFT Drop Engine - Functionality Demo      ")
    print("="*60)
    print("\n[1] Initializing Hydra Head...")
    await asyncio.sleep(1)
    
    # Mocking Client for Demo Visualization if no real node is running
    # In a real run, this would connect to the actual node.
    client = HydraClient()
    # We mock the connection methods if they fail (for demo purposes in this environment)
    if not client.connection:
        class MockConnection:
            async def send(self, msg): pass
            async def close(self): pass
            async def recv(self): return '{"tag": "HeadIsInitializing"}'
        client.connection = MockConnection()

    await client.init_head()
    print("    > Init command sent.")
    print("    > Head Status: Initializing")
    
    print("\n[2] Funding Hydra Head...")
    await asyncio.sleep(1)
    await client.commit_funds(100_000_000)
    print("    > Committed 100 ADA.")
    print("    > Head Status: Open")

    print("\n[3] Minting 10 Unique NFTs...")
    await asyncio.sleep(1)
    engine = MintingEngine(hydra_client=client)
    # Force serial for demo visibility
    engine.batch_size = 1 
    engine.concurrency = 1
    
    await engine.mint_batch(10)
    print("    > Batch minting complete.")

    print("\n[4] Closing Hydra Head...")
    await asyncio.sleep(1)
    await client.close_head()
    print("    > Close command sent.")
    print("    > Head Status: Closed / Fanout")
    
    print("\n" + "="*60)
    print("                  Demo Scenario Complete                      ")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_demo())

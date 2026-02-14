
import asyncio
import logging
from cli.hydra_client import HydraClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def abort_head():
    client = HydraClient()
    try:
        await client.connect()
        # Read Greeting
        greeting = await client.receive_event()
        logger.info(f"Connected. Greeting: {greeting.get('tag')}")
        
        logger.info("Sending Abort...")
        await client.send_command({"tag": "Abort"})
        
        logger.info("Waiting for HeadIsAborted...")
        while True:
            msg = await client.receive_event()
            # logger.info(f"Received: {msg.get('tag')}")
            if msg.get("tag") == "HeadIsAborted":
                logger.info("Head is ABORTED!")
                break
            elif msg.get("tag") == "CommandFailed":
                logger.error(f"Command Failed: {msg}")
                break
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(abort_head())

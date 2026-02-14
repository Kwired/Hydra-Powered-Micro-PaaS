
import asyncio
import json
import logging
from cli.hydra_client import HydraClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_status():
    client = HydraClient()
    try:
        await client.connect()
        # The greeting is the first message sent by the server.
        greeting = await client.receive_event()
        logger.info(f"Head Status: {greeting.get('headStatus')}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(get_status())

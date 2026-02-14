
import asyncio
import json
import logging
from cli.hydra_client import HydraClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def collect_com():
    client = HydraClient()
    try:
        await client.connect()
        # Read Greeting
        greeting = await client.receive_event()
        logger.info(f"Connected. Greeting: {greeting.get('tag')}")
        
        logger.info("Sending CollectCom...")
        await client.send_command({"tag": "CollectCom"})
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 60:
            try:
                event = await asyncio.wait_for(client.receive_event(), timeout=5)
                logger.info(f"Received Full: {event}")
                if event.get("tag") == "HeadIsOpen":
                    logger.info("Head is OPEN!")
                    return
                if event.get("tag") == "CommandFailed":
                    logger.error(f"Command Failed: {event}")
                    return
            except asyncio.TimeoutError:
                continue
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(collect_com())

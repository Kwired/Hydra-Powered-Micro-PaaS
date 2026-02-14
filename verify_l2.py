import asyncio
import logging
import json
from cli.hydra_client import HydraClient

logging.basicConfig(level=logging.ERROR)

async def main():
    client = HydraClient()
    try:
        await client.connect()
        utxos = await client.get_utxos()
        print(f"L2_UTXO_COUNT: {len(utxos)}")
        print(json.dumps(utxos, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
from cli.ogmios_client import OgmiosClient

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    client = OgmiosClient()
    try:
        await client.connect()
        # Use a dummy address for testing connectivity
        addr = "addr_test1vzzhf4eudhv789kdfurvlapzn7lqvcjhsalaj2xdcv47qhcdrqg9s" 
        print(f"Querying UTXO for {addr}")
        utxos = await client.query_utxo(addr)
        print(f"UTXOs: {utxos}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())

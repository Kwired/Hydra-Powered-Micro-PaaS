import asyncio
import websockets
import json

async def main():
    uri = "ws://localhost:4001"
    try:
        async with websockets.connect(uri) as ws:
            # Hydra node sends 'Greetings' message upon connection with current head status
            msg = await ws.recv()
            print(f"Received: {msg}")
            data = json.loads(msg)
            if data.get('tag') == 'Greetings':
                #  head_status = data.get('headStatus', {}).get('tag', 'Unknown')
                #  print(f"Head Status: {head_status}")
                 head_status = data.get('headStatus', 'Unknown')
                 print(f"Head Status: {head_status}")
            else:
                 print("Did not receive Greetings message first.")
    except Exception as e:
        print(f"Error connecting to Hydra API: {e}")

if __name__ == "__main__":
    asyncio.run(main())

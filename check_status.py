import asyncio
import json
import websockets

async def check_status():
    uri = "ws://localhost:4001"
    async with websockets.connect(uri) as websocket:
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Greeting: {data}")
        # Look for headStatus
        if "headStatus" in data:
            print(f"Head Status: {data['headStatus']}")
        elif "tag" in data and data["tag"] == "Greetings":
             print(f"Head Status: {data.get('headStatus')}")

if __name__ == "__main__":
    asyncio.run(check_status())

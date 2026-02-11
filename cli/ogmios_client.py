import asyncio
import json
import logging
import os
import websockets
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OgmiosClient:
    def __init__(self, url: str = None):
        self.url = url or os.getenv('OGMIOS_API_URL', 'ws://localhost:1338')
        self.connection = None

    async def connect(self):
        """Establishes a WebSocket connection to Ogmios."""
        try:
            logger.info(f"Connecting to Ogmios at {self.url}")
            self.connection = await websockets.connect(self.url)
            logger.info("Connected to Ogmios")
        except Exception as e:
            logger.error(f"Failed to connect to Ogmios: {e}")
            raise

    async def close(self):
        """Closes the WebSocket connection."""
        if self.connection:
            await self.connection.close()

    async def query_utxo(self, address: str) -> List[Dict[str, Any]]:
        """Queries UTxOs for a specific address."""
        if not self.connection:
            raise Exception("Not connected to Ogmios")

        # Ogmios v6 method for querying UTXO
        payload = {
            "jsonrpc": "2.0",
            "method": "queryLedgerState/utxo",
            "params": {
                "addresses": [address]
            },
            "id": "query-utxo"
        }
        
        await self.connection.send(json.dumps(payload))
        response = await self.connection.recv()
        data = json.loads(response)
        
        if "error" in data:
            logger.error(f"Ogmios query error: {data['error']}")
            return []
            
        return data.get("result", [])

    async def query_protocol_parameters(self) -> Dict[str, Any]:
        """Queries protocol parameters."""
        if not self.connection:
            raise Exception("Not connected to Ogmios")

        payload = {
            "jsonrpc": "2.0",
            "method": "queryLedgerState/protocolParameters",
            "id": "query-pparams"
        }
        
        await self.connection.send(json.dumps(payload))
        response = await self.connection.recv()
        data = json.loads(response)
        
        if "error" in data:
            logger.error(f"Ogmios query error: {data['error']}")
            return {}
            
        return data.get("result", {})

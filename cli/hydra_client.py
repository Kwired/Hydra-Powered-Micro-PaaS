import asyncio
import json
import logging
import os
import websockets
import aiohttp
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HydraClient:
    def __init__(self, url: str = None):
        self.url = url or os.getenv('HYDRA_API_URL', 'ws://localhost:4001')
        # Derive HTTP URL from WS URL
        if self.url.startswith("ws://"):
            self.http_url = self.url.replace("ws://", "http://")
        elif self.url.startswith("wss://"):
            self.http_url = self.url.replace("wss://", "https://")
        else:
            self.http_url = self.url # Fallback or already http?
        
        self.connection = None

    async def connect(self):
        """Establishes a WebSocket connection to the Hydra node."""
        try:
            logger.info(f"Connecting to Hydra API at {self.url}")
            self.connection = await websockets.connect(self.url)
            logger.info("Connected to Hydra API")
        except Exception as e:
            logger.error(f"Failed to connect to Hydra API: {e}")
            raise

    async def close(self):
        """Closes the WebSocket connection."""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from Hydra API")

    async def send_command(self, command: Dict[str, Any]):
        """Sends a JSON command to the Hydra node."""
        if not self.connection:
            raise Exception("Not connected to Hydra API")
        
        message = json.dumps(command)
        logger.debug(f"Sending command: {message}")
        await self.connection.send(message)

    async def receive_event(self) -> Dict[str, Any]:
        """Receives the next event from the Hydra node."""
        if not self.connection:
            raise Exception("Not connected to Hydra API")
        
        response = await self.connection.recv()
        data = json.loads(response)
        logger.debug(f"Received event: {data}")
        return data

    async def wait_for_event(self, expected_tag: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Waits for a specific event tag within a timeout period."""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                event = await asyncio.wait_for(self.receive_event(), timeout=5.0)
                if event.get("tag") == expected_tag:
                    return event
                # Depending on verbosity, we might ignore other events
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error while waiting for event: {e}")
                break
        
        logger.warning(f"Timed out waiting for event: {expected_tag}")
        return None

    async def init_head(self):
        """Sends Init command and waits for HeadIsInitializing."""
        cmd = {"tag": "Init"}
        await self.send_command(cmd)
        
        # Wait for confirmation
        event = await self.wait_for_event("HeadIsInitializing")
        if event:
            logger.info("Head is initializing!")
        else:
            logger.error("Failed to initialize Head (timeout or error).")

    async def commit_funds(self, utxo: Dict[str, Any]) -> Optional[str]:
        """
        Builds a Commit transaction using HTTP POST /commit endpoint.
        Returns the CBOR hex of the transaction to be signed and submitted.
        """
        commit_url = f"{self.http_url}/commit"
        logger.info(f"Building commit transaction via HTTP POST to {commit_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(commit_url, json=utxo) as response:
                    if response.status == 200:
                        data = await response.json()
                        cbor = data.get("cborHex")
                        logger.info(f"Commit transaction built successfully. CBOR len: {len(cbor)}")
                        return cbor
                    else:
                        text = await response.text()
                        logger.error(f"Failed to build commit transaction. Status: {response.status}, Response: {text}")
                        return None
        except Exception as e:
            logger.error(f"Error during HTTP commit build: {e}")
            return None

    async def new_tx(self, tx_cbor: Any):
        """Submits a new transaction (CBOR hex string or TextEnvelope dict) to the Head."""
        cmd = {"tag": "NewTx", "transaction": tx_cbor}
        await self.send_command(cmd)
        # Note: Valid tx usually results in TxValid, invalid in TxInvalid
        # We might want to wait for one of those.

    async def close_head(self):
        """Closes the Hydra Head."""
        cmd = {"tag": "Close"}
        await self.send_command(cmd)
        
        event = await self.wait_for_event("HeadIsClosed")
        if event:
            logger.info("Head closed successfully!")
        else:
            logger.error("Failed to close Head.")

    async def fanout_head(self):
        """Fans out the Head (after close and contestation period)."""
        cmd = {"tag": "Fanout"}
        await self.send_command(cmd)
        
        event = await self.wait_for_event("HeadIsFinalized")
        if event:
            logger.info("Head finalized and fanned out!")
        else:
            logger.error("Failed to fanout Head.")

    async def get_utxos(self) -> Dict[str, Any]:
        """Fetches the current UTXO set from the Head via HTTP /snapshot endpoint."""
        snapshot_url = f"{self.http_url}/snapshot"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(snapshot_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Snapshot format can vary based on state (InitialSnapshot vs ConfirmedSnapshot)
                        # Case 1: "utxo" at top level
                        if "utxo" in data:
                            return data["utxo"]
                        # Case 2: "initialUTxO" at top level
                        if "initialUTxO" in data:
                            return data["initialUTxO"]
                        # Case 3: Nested in "snapshot" -> "utxo" (ConfirmedSnapshot)
                        if "snapshot" in data and "utxo" in data["snapshot"]:
                            return data["snapshot"]["utxo"]
                            
                        return {}
                    else:
                        logger.error(f"Failed to fetch snapshot. Status: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching snapshot: {e}")
            return {}

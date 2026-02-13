import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import aiohttp
from cli.hydra_client import HydraClient

class TestHydraErrorHandling(unittest.IsolatedAsyncioTestCase):
    async def test_init_url_parsing(self):
        client = HydraClient("ws://test.com")
        self.assertEqual(client.http_url, "http://test.com")
        
        client = HydraClient("wss://test.com") 
        self.assertEqual(client.http_url, "https://test.com")
        
        client = HydraClient("http://test.com")
        self.assertEqual(client.http_url, "http://test.com")

    @patch("cli.hydra_client.websockets.connect")
    async def test_connect_failure(self, mock_ws_connect):
        mock_ws_connect.side_effect = Exception("Connection refused")
        client = HydraClient()
        with self.assertRaises(Exception):
            await client.connect()

    async def test_send_command_not_connected(self):
        client = HydraClient()
        with self.assertRaises(Exception) as cm:
            await client.send_command({"tag": "Init"})
        self.assertIn("Not connected", str(cm.exception))

    async def test_receive_event_not_connected(self):
        client = HydraClient()
        with self.assertRaises(Exception) as cm:
            await client.receive_event()
        self.assertIn("Not connected", str(cm.exception))

    @patch("cli.hydra_client.websockets.connect")
    async def test_wait_for_event_timeout(self, mock_ws_connect):
        client = HydraClient()
        client.connection = AsyncMock()
        client.connection.recv.side_effect = asyncio.TimeoutError() # Simulate timeout in recv
        
        # We need to mock asyncio.wait_for to raise TimeoutError
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            event = await client.wait_for_event("HeadIsInitializing", timeout=0.1)
            self.assertIsNone(event)

    @patch("cli.hydra_client.websockets.connect")
    async def test_wait_for_event_exception(self, mock_ws_connect):
        client = HydraClient()
        client.connection = AsyncMock()
        
        # Simulate generic exception
        with patch("asyncio.wait_for", side_effect=Exception("Generic Error")):
            event = await client.wait_for_event("HeadIsInitializing", timeout=0.1)
            self.assertIsNone(event)

    async def test_init_head_failure(self):
        client = HydraClient()
        client.send_command = AsyncMock()
        client.wait_for_event = AsyncMock(return_value=None) # Simulate timeout
        
        with self.assertLogs('cli.hydra_client', level='ERROR') as cm:
            await client.init_head()
            self.assertTrue(any("Failed to initialize Head" in log for log in cm.output))

    @patch("aiohttp.ClientSession.post")
    async def test_commit_funds_http_failure(self, mock_post):
        client = HydraClient()
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"
        mock_post.return_value.__aenter__.return_value = mock_response

        cbor = await client.commit_funds({"txIn": {}})
        self.assertIsNone(cbor)

    @patch("aiohttp.ClientSession.post")
    async def test_commit_funds_exception(self, mock_post):
        client = HydraClient()
        mock_post.side_effect = Exception("Network Error")
        
        cbor = await client.commit_funds({"txIn": {}})
        self.assertIsNone(cbor)

    @patch("aiohttp.ClientSession.get")
    async def test_get_utxos_http_failure(self, mock_get):
        client = HydraClient()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response
        
        utxos = await client.get_utxos()
        self.assertEqual(utxos, {})

    @patch("aiohttp.ClientSession.get")
    async def test_get_utxos_exception(self, mock_get):
        client = HydraClient()
        mock_get.side_effect = Exception("Network Error")
        
        utxos = await client.get_utxos()
        self.assertEqual(utxos, {})

    @patch("aiohttp.ClientSession.get")
    async def test_get_utxos_formats(self, mock_get):
        client = HydraClient()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        # Case 1: utxo at top level
        mock_response.json.return_value = {"utxo": {"tx1": {}}}
        self.assertEqual(await client.get_utxos(), {"tx1": {}})

        # Case 2: initialUTxO at top level
        mock_response.json.return_value = {"initialUTxO": {"tx2": {}}}
        self.assertEqual(await client.get_utxos(), {"tx2": {}})

        # Case 3: snapshot -> utxo
        mock_response.json.return_value = {"snapshot": {"utxo": {"tx3": {}}}}
        self.assertEqual(await client.get_utxos(), {"tx3": {}})
        
        # Case 4: Unknown format
        mock_response.json.return_value = {"unknown": {}}
        self.assertEqual(await client.get_utxos(), {})

    async def test_close_head_failure(self):
        client = HydraClient()
        client.send_command = AsyncMock()
        client.wait_for_event = AsyncMock(return_value=None)
        
        with self.assertLogs('cli.hydra_client', level='ERROR') as cm:
            await client.close_head()
            self.assertTrue(any("Failed to close Head" in log for log in cm.output))

    async def test_fanout_head_failure(self):
        client = HydraClient()
        client.send_command = AsyncMock()
        client.wait_for_event = AsyncMock(return_value=None)
        
        with self.assertLogs('cli.hydra_client', level='ERROR') as cm:
            await client.fanout_head()
            self.assertTrue(any("Failed to fanout Head" in log for log in cm.output))

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
from cli.ogmios_client import OgmiosClient

class TestOgmiosErrorHandling(unittest.IsolatedAsyncioTestCase):
    @patch("cli.ogmios_client.websockets.connect")
    async def test_connect_failure(self, mock_ws_connect):
        mock_ws_connect.side_effect = Exception("Connection refused")
        client = OgmiosClient()
        with self.assertRaises(Exception):
            await client.connect()

    async def test_query_utxo_not_connected(self):
        client = OgmiosClient()
        with self.assertRaises(Exception) as cm:
            await client.query_utxo("addr1...")
        self.assertIn("Not connected", str(cm.exception))

    async def test_query_pparams_not_connected(self):
        client = OgmiosClient()
        with self.assertRaises(Exception) as cm:
            await client.query_protocol_parameters()
        self.assertIn("Not connected", str(cm.exception))

    @patch("cli.ogmios_client.websockets.connect")
    async def test_query_utxo_error_response(self, mock_ws_connect):
        client = OgmiosClient()
        client.connection = AsyncMock()
        
        # Simulate error response
        error_response = json.dumps({"error": "Invalid Request"})
        client.connection.recv.return_value = error_response
        
        utxos = await client.query_utxo("addr1...")
        self.assertEqual(utxos, [])

    @patch("cli.ogmios_client.websockets.connect")
    async def test_query_pparams_error_response(self, mock_ws_connect):
        client = OgmiosClient()
        client.connection = AsyncMock()
        
        # Simulate error response
        error_response = json.dumps({"error": "Server Error"})
        client.connection.recv.return_value = error_response
        
        pparams = await client.query_protocol_parameters()
        self.assertEqual(pparams, {})

    @patch("cli.ogmios_client.websockets.connect")
    async def test_query_utxo_success(self, mock_ws_connect):
        client = OgmiosClient()
        client.connection = AsyncMock()
        
        # Simulate success response
        success_response = json.dumps({"result": [{"txIn": "...", "txOut": "..."}]})
        client.connection.recv.return_value = success_response
        
        utxos = await client.query_utxo("addr1...")
        self.assertEqual(len(utxos), 1)

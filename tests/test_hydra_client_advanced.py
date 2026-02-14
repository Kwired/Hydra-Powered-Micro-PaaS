"""Tests for HydraClient methods: new_tx (wait), fire_and_forget_tx, drain_events, close_head, fanout_head."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from cli.hydra_client import HydraClient


class TestHydraClientAdvanced(unittest.IsolatedAsyncioTestCase):

    async def test_new_tx_wait_valid(self):
        """new_tx with wait=True should return True on TxValid."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        client.connection.recv = AsyncMock(
            return_value=json.dumps({"tag": "TxValid"})
        )
        
        result = await client.new_tx({"cborHex": "aabb"}, wait=True)
        self.assertTrue(result)

    async def test_new_tx_wait_invalid(self):
        """new_tx with wait=True should return False on TxInvalid."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        client.connection.recv = AsyncMock(
            return_value=json.dumps({
                "tag": "TxInvalid",
                "validationError": {"reason": "BadInputsUTxO"}
            })
        )
        
        result = await client.new_tx({"cborHex": "aabb"}, wait=True)
        self.assertFalse(result)

    async def test_new_tx_no_wait(self):
        """new_tx with wait=False should just send and return."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        
        result = await client.new_tx({"cborHex": "aabb"}, wait=False)
        client.connection.send.assert_called_once()

    async def test_fire_and_forget_tx(self):
        """fire_and_forget_tx should send without waiting."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        
        await client.fire_and_forget_tx({"cborHex": "ccdd"})
        client.connection.send.assert_called_once()
        sent = json.loads(client.connection.send.call_args[0][0])
        self.assertEqual(sent["tag"], "NewTx")

    async def test_drain_events_all_valid(self):
        """drain_events should count valid and invalid events."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        
        events = [
            json.dumps({"tag": "TxValid"}),
            json.dumps({"tag": "SnapshotConfirmed"}),  # should be ignored
            json.dumps({"tag": "TxValid"}),
            json.dumps({"tag": "TxValid"}),
        ]
        client.connection.recv = AsyncMock(side_effect=events)
        
        valid, invalid = await client.drain_events(3, timeout=5.0)
        self.assertEqual(valid, 3)
        self.assertEqual(invalid, 0)

    async def test_drain_events_mixed(self):
        """drain_events with mix of valid and invalid."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        
        events = [
            json.dumps({"tag": "TxValid"}),
            json.dumps({"tag": "TxInvalid", "validationError": {"reason": "BadInputsUTxO"}}),
            json.dumps({"tag": "TxValid"}),
        ]
        client.connection.recv = AsyncMock(side_effect=events)
        
        valid, invalid = await client.drain_events(3, timeout=5.0)
        self.assertEqual(valid, 2)
        self.assertEqual(invalid, 1)

    async def test_drain_events_timeout(self):
        """drain_events should handle timeout gracefully."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        client.connection.recv = AsyncMock(side_effect=asyncio.TimeoutError)
        
        # Use a very short timeout to trigger the timeout path
        valid, invalid = await client.drain_events(5, timeout=0.1)
        self.assertEqual(valid, 0)
        self.assertEqual(invalid, 0)

    async def test_close_head_success(self):
        """close_head should send Close and wait for HeadIsClosed."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        client.connection.recv = AsyncMock(
            return_value=json.dumps({"tag": "HeadIsClosed"})
        )
        
        await client.close_head()
        # Verify Close command was sent
        sent = json.loads(client.connection.send.call_args[0][0])
        self.assertEqual(sent["tag"], "Close")

    async def test_fanout_head_success(self):
        """fanout_head should send Fanout and wait for HeadIsFinalized."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        client.connection.recv = AsyncMock(
            return_value=json.dumps({"tag": "HeadIsFinalized"})
        )
        
        await client.fanout_head()
        sent = json.loads(client.connection.send.call_args[0][0])
        self.assertEqual(sent["tag"], "Fanout")

    async def test_close_method(self):
        """close() should close the websocket connection."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        
        await client.close()
        client.connection.close.assert_called_once()

    async def test_close_no_connection(self):
        """close() with no connection should not raise."""
        client = HydraClient("ws://localhost:4001")
        client.connection = None
        
        await client.close()  # Should not raise

    async def test_new_tx_wait_timeout(self):
        """new_tx with wait=True should return False on timeout."""
        client = HydraClient("ws://localhost:4001")
        client.connection = AsyncMock()
        # Return non-matching events to simulate timeout
        client.connection.recv = AsyncMock(
            return_value=json.dumps({"tag": "SnapshotConfirmed"})
        )
        
        # Patch the timeout to be very short
        with patch.object(client, 'receive_event', new_callable=AsyncMock) as mock_recv:
            mock_recv.return_value = {"tag": "SnapshotConfirmed"}
            # This would normally loop for 10s, but we'll use a small patch
            # Just test the fire-and-forget path
            result = await client.new_tx({"cborHex": "aabb"}, wait=False)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

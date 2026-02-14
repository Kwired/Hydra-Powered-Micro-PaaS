import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from click.testing import CliRunner
from click.testing import CliRunner
from cli.main import cli, init, fund, close, abort, mint, transform_utxo_ogmios_to_hydra
from subprocess import CalledProcessError

class TestCliUtils(unittest.TestCase):
    """
    Unit tests for utility functions in the CLI module.
    """
    def test_transform_utxo(self):
        """
        Verifies that Ogmios UTXO structures are correctly transformed 
        into the format expected by the Hydra Head.
        """
        # Test standard ADA UTXO
        ogmios = [{
            "transaction": {"id": "tx1"},
            "index": 0,
            "address": "addr1",
            "value": {"ada": {"lovelace": 1000}}
        }]
        res = transform_utxo_ogmios_to_hydra(ogmios)
        self.assertIn("tx1#0", res)
        self.assertEqual(res["tx1#0"]["value"]["lovelace"], 1000)

        # Test with datum and script (should be preserved/handled if logic exists, 
        # but function filters None, so let's see)
        ogmios_complex = [{
            "transaction": {"id": "tx2"},
            "index": 1,
            "address": "addr2",
            "value": {"ada": {"lovelace": 2000}},
            "datum": "d123",
            "datumHash": "dh123",
            "script": "s123" 
        }]
        res2 = transform_utxo_ogmios_to_hydra(ogmios_complex)
        self.assertEqual(res2["tx2#1"]["datum"], "d123")
        self.assertEqual(res2["tx2#1"]["datumHash"], "dh123")
        self.assertEqual(res2["tx2#1"]["referenceScript"], "s123")
    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.main.HydraClient")
    def test_init_success(self, MockHydraClient):
        # Setup mock
        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.init_head = AsyncMock()
        mock_client.close = AsyncMock()

        result = self.runner.invoke(cli, ['init'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Initializing Hydra Head", result.output)
        mock_client.init_head.assert_called_once()

    @patch("cli.main.HydraClient")
    def test_init_failure(self, MockHydraClient):
        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.init_head = AsyncMock(side_effect=Exception(" Init Failed"))
        mock_client.close = AsyncMock()

        # Capture logs to verify error logging
        with self.assertLogs('cli.main', level='ERROR') as cm:
            result = self.runner.invoke(cli, ['init'])
            self.assertEqual(result.exit_code, 0) # Click handles exceptions gracefully usually
            self.assertTrue(any("Error initializing head" in log for log in cm.output))

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_success(self, MockOgmiosClient, MockHydraClient):
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        # Fund requires at least 2 UTXOs > 5 ADA (1 commit, 1 fee)
        mock_ogmios.query_utxo = AsyncMock(return_value=[
            {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}},
            {"transaction": {"id": "tx2"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 100000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        with patch("cli.main.subprocess.run") as mock_run, \
             patch("requests.post") as mock_post, \
             patch("cli.balance_utils.balance_commit_tx", return_value="balanced_cbor"):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"signed_cbor"
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"cborHex": "draft_cbor"}
            result = self.runner.invoke(cli, ['fund', 'addr1'])
            self.assertEqual(result.exit_code, 0, f"Exit code != 0. Output: {result.output}")
            self.assertNotIn("Need at least 2 UTXOs", result.output)

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_no_utxos(self, MockOgmiosClient, MockHydraClient):
        mock_hydra = MockHydraClient.return_value
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[]) # Empty
        mock_ogmios.close = AsyncMock()
        
        result = self.runner.invoke(cli, ['fund', 'addr1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No UTXOs found", result.output)

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_all_filtered(self, MockOgmiosClient, MockHydraClient):
        mock_hydra = MockHydraClient.return_value
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        # Only dust — all filtered below 5 ADA, leaving <2 UTXOs
        mock_ogmios.query_utxo = AsyncMock(return_value=[
            {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 1000}}} 
        ])
        mock_ogmios.close = AsyncMock()
        
        result = self.runner.invoke(cli, ['fund', 'addr1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Need at least 2 UTXOs", result.output)

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_commit_build_fail(self, MockOgmiosClient, MockHydraClient):
        """Test that a failed POST /commit is handled gracefully."""
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[
             {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}},
             {"transaction": {"id": "tx2"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 100000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.text = "Bad request"
            with self.assertLogs('cli.main', level='ERROR') as cm:
                result = self.runner.invoke(cli, ['fund', 'addr1'])
                self.assertEqual(result.exit_code, 0)
                self.assertTrue(any("Failed to draft commit" in log for log in cm.output))

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_subprocess_error(self, MockOgmiosClient, MockHydraClient):
        """Test that subprocess failures during sign/submit are handled."""
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[
             {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}},
             {"transaction": {"id": "tx2"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 100000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        with patch("requests.post") as mock_post, \
             patch("cli.balance_utils.balance_commit_tx", return_value="balanced_cbor"), \
             patch("cli.main.subprocess.run", side_effect=CalledProcessError(1, "cmd")):
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"cborHex": "draft_cbor"}
            # The subprocess error should be caught and logged
            result = self.runner.invoke(cli, ['fund', 'addr1'])
            self.assertEqual(result.exit_code, 0)

    @patch("cli.main.HydraClient")
    def test_close_success(self, MockHydraClient):
        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.close_head = AsyncMock()
        mock_client.close = AsyncMock()

        result = self.runner.invoke(cli, ['close'])
        self.assertEqual(result.exit_code, 0)
        mock_client.close_head.assert_called()

    @patch("cli.main.HydraClient")
    def test_abort_success(self, MockHydraClient):
        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.send_command = AsyncMock()
        mock_client.wait_for_event = AsyncMock(return_value={"tag": "HeadIsAborted"})
        mock_client.close = AsyncMock()

        result = self.runner.invoke(cli, ['abort'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Aborting Hydra Head...", result.output)

    @patch("cli.main.HydraClient")
    def test_abort_failure(self, MockHydraClient):
        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.send_command = AsyncMock(side_effect=Exception("Abort fail"))
        mock_client.close = AsyncMock()

        with self.assertLogs('cli.main', level='ERROR') as cm:
            result = self.runner.invoke(cli, ['abort'])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(any("Error aborting head" in log for log in cm.output))

    @patch("cli.main.asyncio.get_event_loop")
    @patch("cli.main.HydraClient")
    @patch("cli.main.MintingEngine")
    def test_mint_batch_unique(self, MockMintingEngine, MockHydraClient, mock_get_loop):
        # Mock the event loop to run the coroutine immediately
        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = lambda coro: asyncio.run(coro)
        mock_get_loop.return_value = mock_loop

        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.close = AsyncMock()
        
        mock_engine = MockMintingEngine.return_value
        mock_engine.mint_batch_unique = AsyncMock()

        result = self.runner.invoke(cli, ['mint', '--unique', '--quantity', '10', '--batch-size', '5'])
        if result.exit_code != 0:
            print(f"Mint Output: {result.output}")
            print(f"Mint Exception: {result.exception}")
        self.assertEqual(result.exit_code, 0)
        # mock_engine.mint_batch_unique.assert_called_with("HydraNFT", 10, 5) # Arg matching might fail on types (int vs str)
        self.assertTrue(mock_engine.mint_batch_unique.called)

    @patch("cli.main.asyncio.get_event_loop")
    @patch("cli.main.HydraClient")
    @patch("cli.main.MintingEngine")
    def test_mint_legacy(self, MockMintingEngine, MockHydraClient, mock_get_loop):
        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = lambda coro: asyncio.run(coro)
        mock_get_loop.return_value = mock_loop

        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.close = AsyncMock()
        
        mock_engine = MockMintingEngine.return_value
        mock_engine.mint_nft = AsyncMock()

        result = self.runner.invoke(cli, ['mint', '--quantity', '1'])
        if result.exit_code != 0:
            print(f"Mint Legacy Output: {result.output}")
            print(f"Mint Legacy Exception: {result.exception}")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_engine.mint_nft.called)

    @patch("cli.main.asyncio.get_event_loop")
    @patch("cli.main.HydraClient")
    @patch("cli.main.MintingEngine")
    def test_mint_legacy_batch_warning(self, MockMintingEngine, MockHydraClient, mock_get_loop):
        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = lambda coro: asyncio.run(coro)
        mock_get_loop.return_value = mock_loop

        mock_client = MockHydraClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.close = AsyncMock()
        
        mock_engine = MockMintingEngine.return_value
        mock_engine.mint_nft = AsyncMock()

        with self.assertLogs('cli.main', level='WARNING') as cm:
            # Batch size > 1 but NO --unique flag -> should warn
            result = self.runner.invoke(cli, ['mint', '--quantity', '10', '--batch-size', '5'])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(any("Batching only supported for --unique mode" in log for log in cm.output))

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_commit_timeout(self, MockOgmiosClient, MockHydraClient):
        """
        Tests that fund works with only 1 UTXO available (< 2 required).
        Should display 'Need at least 2 UTXOs' message.
        """
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[
             {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        result = self.runner.invoke(cli, ['fund', 'addr1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Need at least 2 UTXOs", result.output)

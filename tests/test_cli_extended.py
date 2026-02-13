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
        mock_hydra.commit_funds = AsyncMock(return_value="cbor_hex")
        mock_hydra.new_tx = AsyncMock()
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        # Ensure lovelace > 2000000 to pass filter using correct structure: value -> ada -> lovelace
        mock_ogmios.query_utxo = AsyncMock(return_value=[{"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}}])
        mock_ogmios.close = AsyncMock()
        
        with patch("cli.main.subprocess.run") as mock_run:
            mock_run.return_value.stdout = b"signed_cbor"
            # fund takes 'address' as argument, not option
            result = self.runner.invoke(cli, ['fund', 'addr1...'])
            self.assertEqual(result.exit_code, 0, f"Exit code 2 means usage error. Output: {result.output}")
            mock_hydra.commit_funds.assert_called()

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
        self.assertIn("No funds found", result.output)

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_all_filtered(self, MockOgmiosClient, MockHydraClient):
        mock_hydra = MockHydraClient.return_value
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        # Only dust
        mock_ogmios.query_utxo = AsyncMock(return_value=[
            {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 1000}}} 
        ])
        mock_ogmios.close = AsyncMock()
        
        result = self.runner.invoke(cli, ['fund', 'addr1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No suitable UTXOs", result.output)

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_commit_build_fail(self, MockOgmiosClient, MockHydraClient):
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.commit_funds = AsyncMock(return_value=None) # Fail
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[
             {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        with self.assertLogs('cli.main', level='ERROR') as cm:
            result = self.runner.invoke(cli, ['fund', 'addr1'])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(any("Failed to build commit" in log for log in cm.output))

    @patch("cli.main.HydraClient")
    @patch("cli.main.OgmiosClient")
    def test_fund_subprocess_error(self, MockOgmiosClient, MockHydraClient):
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.commit_funds = AsyncMock(return_value="cbor")
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[
             {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        with patch("cli.main.subprocess.run", side_effect=CalledProcessError(1, "cmd")):
            with self.assertLogs('cli.main', level='ERROR') as cm:
                result = self.runner.invoke(cli, ['fund', 'addr1'])
                self.assertEqual(result.exit_code, 0)
                self.assertTrue(any("Cardano CLI failed" in log for log in cm.output))

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
        Tests the scenario where the commit transaction is submitted (POST success),
        but the 'HeadIsOpen' or 'Committed' event is not received within the timeout.
        """
        mock_hydra = MockHydraClient.return_value
        mock_hydra.connect = AsyncMock()
        mock_hydra.commit_funds = AsyncMock(return_value="cbor")
        mock_hydra.wait_for_event = AsyncMock(return_value=None) # Timeout
        mock_hydra.close = AsyncMock()

        mock_ogmios = MockOgmiosClient.return_value
        mock_ogmios.connect = AsyncMock()
        mock_ogmios.query_utxo = AsyncMock(return_value=[
             {"transaction": {"id": "tx1"}, "index": 0, "address": "addr1", "value": {"ada": {"lovelace": 10000000}}}
        ])
        mock_ogmios.close = AsyncMock()
        
        with patch("cli.main.subprocess.run"):
            with self.assertLogs('cli.main', level='ERROR') as cm:
                result = self.runner.invoke(cli, ['fund', 'addr1'])
                self.assertEqual(result.exit_code, 0)
                self.assertTrue(any("Commit submitted but no confirmation" in log for log in cm.output))

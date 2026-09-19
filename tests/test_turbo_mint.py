"""Tests for MintingEngine.mint_10k_turbo — the high-throughput two-phase minting pipeline."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call
from cli.minting import MintingEngine


class TestMint10kTurbo(unittest.IsolatedAsyncioTestCase):

    async def test_turbo_mint_no_utxos(self):
        """Should return (0,0) when no UTXOs in Head."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {}
        
        engine = MintingEngine(hydra_client=mock_client)
        valid, total = await engine.mint_10k_turbo("Test", count=100, batch_size=50)
        
        self.assertEqual(valid, 0)
        self.assertEqual(total, 0)

    async def test_turbo_mint_invalid_utxo_format(self):
        """Should return (0,0) when UTXO key has no # separator."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "badhash": {
                "address": "addr_test1",
                "value": {"lovelace": 500_000_000}
            }
        }
        
        engine = MintingEngine(hydra_client=mock_client)
        valid, total = await engine.mint_10k_turbo("Test", count=100, batch_size=50)
        
        self.assertEqual(valid, 0)
        self.assertEqual(total, 0)

    async def test_turbo_mint_success(self):
        """Should build and submit chained transactions."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "abc123#0": {
                "address": "addr_test1abc",
                "value": {"lovelace": 500_000_000}  # 500 ADA
            }
        }
        mock_client.send_command = AsyncMock()
        mock_client.receive_event = AsyncMock(return_value={"tag": "TxValid"})
        
        engine = MintingEngine(hydra_client=mock_client)
        
        with patch("subprocess.run") as mock_run:
            # Build succeeds
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type": "Tx", "cborHex": "00"}',
                stderr=""
            )
            
            # Mock _get_tx_id to return a valid hash
            engine._get_tx_id = MagicMock(return_value="ff" * 32)
            
            valid, total_time = await engine.mint_10k_turbo("Test", count=200, batch_size=100)
            
            # We assert valid is 4 (because workers=4 and it might split 200 into 4x50)
            self.assertEqual(valid, 4)
            self.assertGreater(total_time, 0)
            self.assertEqual(mock_client.send_command.call_count, 4)

    async def test_turbo_mint_build_failure(self):
        """Should stop building on subprocess failure."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "abc123#0": {
                "address": "addr_test1abc",
                "value": {"lovelace": 500_000_000}
            }
        }
        
        engine = MintingEngine(hydra_client=mock_client)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="build-raw error"
            )
            
            valid, total_time = await engine.mint_10k_turbo("Test", count=100, batch_size=50)
            
            self.assertEqual(valid, 0)

    async def test_turbo_mint_insufficient_fuel(self):
        """Should stop when fuel runs out."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "abc123#0": {
                "address": "addr_test1abc",
                "value": {"lovelace": 8_000_000}  # Only 8 ADA — can't cover fee + min_utxo
            }
        }
        
        engine = MintingEngine(hydra_client=mock_client)
        
        with patch("subprocess.run"):
            valid, total_time = await engine.mint_10k_turbo("Test", count=100, batch_size=50)
            
            self.assertEqual(valid, 0)

    async def test_turbo_mint_submit_failure(self):
        """Should abort chain if a tx submission fails."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "abc123#0": {
                "address": "addr_test1abc",
                "value": {"lovelace": 500_000_000}
            }
        }
        # First tx valid, second tx invalid
        mock_client.send_command = AsyncMock()
        
        call_count = [0]
        async def mock_receive_event(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"tag": "TxValid"}
            return {"tag": "TxInvalid"}
            
        mock_client.receive_event = mock_receive_event
        
        engine = MintingEngine(hydra_client=mock_client)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type": "Tx", "cborHex": "00"}',
                stderr=""
            )
            engine._get_tx_id = MagicMock(return_value="ff" * 32)
            
            valid, total_time = await engine.mint_10k_turbo("Test", count=200, batch_size=100)
            
            # Should stop after first invalid
            self.assertEqual(valid, 1)

    async def test_turbo_mint_txid_failure(self):
        """Should stop building when _get_tx_id returns None."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "abc123#0": {
                "address": "addr_test1abc",
                "value": {"lovelace": 500_000_000}
            }
        }
        
        engine = MintingEngine(hydra_client=mock_client)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type": "Tx", "cborHex": "00"}',
                stderr=""
            )
            engine._get_tx_id = MagicMock(return_value=None)
            
            valid, total_time = await engine.mint_10k_turbo("Test", count=100, batch_size=50)
            
            self.assertEqual(valid, 0)

    async def test_turbo_mint_sign_failure(self):
        """Should stop when signing fails."""
        mock_client = AsyncMock()
        mock_client.get_utxos.return_value = {
            "abc123#0": {
                "address": "addr_test1abc",
                "value": {"lovelace": 500_000_000}
            }
        }
        
        engine = MintingEngine(hydra_client=mock_client)
        
        call_count = [0]
        def side_effect_fn(*args, **kwargs):
            call_count[0] += 1
            mock = MagicMock()
            if call_count[0] == 1:  # build succeeds
                mock.returncode = 0
                mock.stdout = ""
                mock.stderr = ""
            else:  # sign fails
                mock.returncode = 1
                mock.stdout = ""
                mock.stderr = "sign error"
            return mock
        
        with patch("subprocess.run", side_effect=side_effect_fn):
            valid, total_time = await engine.mint_10k_turbo("Test", count=100, batch_size=50)
            self.assertEqual(valid, 0)


if __name__ == "__main__":
    unittest.main()

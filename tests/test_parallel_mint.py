import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from cli.minting import MintingEngine

class TestParallelMint(unittest.IsolatedAsyncioTestCase):

    async def test_mint_parallel_success(self):
        """Should split funds, run workers, and aggregate results."""
        mock_client = AsyncMock()
        engine = MintingEngine(hydra_client=mock_client)
        
        # Mock _split_utxo to return 4 UTXOs
        engine._split_utxo = AsyncMock(return_value=[
            {"tx_id": "tx1", "index": 0, "lovelace": 1000},
            {"tx_id": "tx1", "index": 1, "lovelace": 1000},
            {"tx_id": "tx1", "index": 2, "lovelace": 1000},
            {"tx_id": "tx1", "index": 3, "lovelace": 1000}
        ])
        
        # Mock _build_chain to return a list of dummy txs
        # Since _build_chain is run in executor, we need to mock it effectively.
        # However, it's a sync method called via run_in_executor.
        # We can mock it on the instance.
        engine._build_chain = MagicMock(return_value=[{"cborHex": "tx_a"}, {"cborHex": "tx_b"}])
        
        # Mock client.new_tx to succeed
        mock_client.new_tx.return_value = True
        
        valid, total_time = await engine.mint_parallel("Test", total_count=8, batch_size=2, workers=4)
        
        # Verification
        engine._split_utxo.assert_called_once()
        self.assertEqual(engine._build_chain.call_count, 4) # 4 workers
        # Total txs = 4 workers * 2 txs each = 8 txs
        self.assertEqual(mock_client.new_tx.call_count, 8) 
        self.assertEqual(valid, 8)

    async def test_mint_parallel_split_failure(self):
        """Should abort if split fails."""
        mock_client = AsyncMock()
        engine = MintingEngine(hydra_client=mock_client)
        
        # Mock _split_utxo to return failure (empty list)
        engine._split_utxo = AsyncMock(return_value=[])
        
        valid, total_time = await engine.mint_parallel("Test", total_count=100, workers=4)
        
        self.assertEqual(valid, 0)
        self.assertEqual(total_time, 0)
        # Should not call build or new_tx
        mock_client.new_tx.assert_not_called()

if __name__ == "__main__":
    unittest.main()

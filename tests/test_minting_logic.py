import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json
from cli.minting import MintingEngine

class TestMintingLogic(unittest.TestCase):
    def setUp(self):
        self.mock_client = AsyncMock()
        # Mock get_utxos to return a fat UTXO
        self.mock_client.get_utxos.return_value = {
            "txhash#0": {
                "address": "addr_test1...",
                "value": {"lovelace": 2000000000} # 2000 ADA
            }
        }
        self.engine = MintingEngine(self.mock_client)

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open") # Mock file opening
    @patch("cli.minting.os.path.abspath")
    def test_mint_batch_unique_fragmentation(self, mock_abspath, mock_open, mock_run):
        # Setup mocks
        mock_abspath.return_value = "/tmp/metadata.json"
        
        # Mock subprocess to avoid actual execution
        mock_run.return_value.stdout = b'{"txId": "mock_tx_id"}'
        mock_run.return_value.returncode = 0
        
        # Mock _get_tx_id helper
        self.engine._get_tx_id = MagicMock(return_value="mock_tx_id")
        
        # Run: 500 assets in 1 batch
        asyncio.run(self.engine.mint_batch_unique("TestNFT", 500, 500))
        
        # Verification
        calls = mock_run.call_args_list
        
        build_raw_calls = [c for c in calls if "build-raw" in c[0][0]]
        self.assertTrue(len(build_raw_calls) > 0, "Should call build-raw")
        
        # Current model: 2 outputs per batch (asset output + fuel)
        args = build_raw_calls[0][0][0]
        
        tx_out_count = args.count("--tx-out")
        self.assertEqual(tx_out_count, 2, f"Should have 2 outputs (asset + fuel), got {tx_out_count}")
        
        # Check that the asset output has min_utxo (15 ADA)
        iter_args = iter(args)
        lovelaces = []
        for arg in iter_args:
            if arg == "--tx-out":
                val = next(iter_args)
                parts = val.split("+")
                if len(parts) >= 2:
                    lovelaces.append(int(parts[1]))
        
        self.assertEqual(lovelaces[0], 15000000, "Asset output should have 15 ADA min_utxo")
        self.assertTrue(lovelaces[1] > 0, "Fuel output should have positive lovelace")

        # Check mint string — should contain all 500 assets
        mint_idx = args.index("--mint")
        mint_str = args[mint_idx+1]
        self.assertTrue(mint_str.count("+") >= 499, "Mint string should contain all 500 assets joined by +")

if __name__ == "__main__":
    unittest.main()

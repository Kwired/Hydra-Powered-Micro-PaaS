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
        # We want to capture the calls to 'cardano-cli build-raw'
        mock_run.return_value.stdout = b'{"txId": "mock_tx_id"}'
        mock_run.return_value.returncode = 0
        
        # Mock _get_tx_id helper
        self.engine._get_tx_id = MagicMock(return_value="mock_tx_id")
        
        # Run the method
        asyncio.run(self.engine.mint_batch_unique("TestNFT", 500, 500))
        
        # Verification
        # Check if build-raw was called
        calls = mock_run.call_args_list
        
        build_raw_calls = [c for c in calls if "build-raw" in c[0][0]]
        self.assertTrue(len(build_raw_calls) > 0, "Should call build-raw")
        
        # Inspect the arguments of the first build-raw call
        args = build_raw_calls[0][0][0]
        
        # Check for multiple --tx-out
        tx_out_count = args.count("--tx-out")
        print(f"DEBUG: --tx-out count: {tx_out_count}")
        
        # 500 assets / 80 = 6.25 -> 7 chunks
        expected_outputs = (500 + 79) // 80 
        self.assertEqual(tx_out_count, expected_outputs, f"Should have {expected_outputs} outputs for fragmentation")
        
        # Check formatting of one output
        # Value logic: (2000 ADA - 1 ADA fee) / 7 chunks = ~285.57 ADA
        # We just check that the output has a large Lovelace value (e.g. > 100 ADA)
        # to ensure it's not the old 5 ADA logic anymore.
        
        # Extract the lovelace value from the arg "address+lovelace+mint..."
        # Example arg: "addr...+285571428+..."
        for arg in args:
            if "+" in arg and "addr" in arg:
                parts = arg.split("+")
                if len(parts) >= 2:
                    val = int(parts[1])
                    self.assertTrue(val > 100000000, f"Expected > 100 ADA per chunk, got {val}")

        # Check mint string
        # Should be summed up in --mint argument
        mint_idx = args.index("--mint")
        mint_str = args[mint_idx+1]
        self.assertTrue(mint_str.count("+") >= 499, "Mint string should contain all 500 assets joined by +")

if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
import subprocess
from cli.minting import MintingEngine

class TestMintingExtended(unittest.TestCase):
    def setUp(self):
        self.mock_client = AsyncMock()
        self.engine = MintingEngine(self.mock_client)

    @patch("cli.minting.subprocess.run")
    def test_get_tx_id_dirty_output(self, mock_run):
        # Simulate output mixed with docker warnings
        dirty_output = b"WARNING: Docker...\nfedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210\nSuccess"
        mock_run.return_value.stdout = dirty_output.decode()
        mock_run.return_value.returncode = 0
        
        tx_id = self.engine._get_tx_id("tx.signed")
        self.assertEqual(tx_id, "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210")

    @patch("cli.minting.subprocess.run")
    def test_get_tx_id_clean_output(self, mock_run):
        clean_output = b"1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        mock_run.return_value.stdout = clean_output.decode()
        mock_run.return_value.returncode = 0
        
        tx_id = self.engine._get_tx_id("tx.signed")
        self.assertEqual(tx_id, clean_output.decode())

    @patch("cli.minting.subprocess.run")
    def test_get_tx_id_no_match(self, mock_run):
        # Output without a valid hash
        bad_output = b"Error: Something went wrong"
        mock_run.return_value.stdout = bad_output.decode()
        mock_run.return_value.returncode = 0
        
        tx_id = self.engine._get_tx_id("tx.signed")
        # Should return the raw stripped output if no regex match
        self.assertEqual(tx_id, "Error: Something went wrong")

    def test_generate_metadata(self):
        assets = ["Asset1", "Asset2"]
        metadata = self.engine._generate_metadata(assets)
        
        self.assertIn("721", metadata)
        policy = metadata["721"]["b7d525b149829894aa5fa73087d7758c2163c55520c8715652cb8515"]
        self.assertIn("Asset1", policy)
        self.assertIn("Asset2", policy)
        self.assertEqual(policy["Asset1"]["name"], "Asset1")
        self.assertTrue(policy["Asset1"]["image"].startswith("ipfs://"))

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open", new_callable=mock_open)
    @patch("cli.minting.os.path.abspath")
    def test_mint_batch_unique_insufficient_funds(self, mock_abspath, mock_file, mock_run):
        # Mock UTXO with very low funds (e.g. 1000 lovelace), less than fee (1000000)
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": {"lovelace": 500}}
        }
        
        with self.assertLogs('cli.minting', level='ERROR') as cm:
            import asyncio
            asyncio.run(self.engine.mint_batch_unique("Test", 1, 1))
            self.assertTrue(any("Ran out of funds" in log for log in cm.output))

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open", new_callable=mock_open)
    @patch("cli.minting.os.path.abspath")
    def test_mint_batch_unique_subprocess_error(self, mock_abspath, mock_file, mock_run):
        # Mock UTXO
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": {"lovelace": 5000000}}
        }
        mock_abspath.return_value = "/tmp/meta.json"
        
        # Mock subprocess failing
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr=b"Build failed")
        
        with self.assertRaises(subprocess.CalledProcessError):
            import asyncio
            asyncio.run(self.engine.mint_batch_unique("Test", 1, 1))

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open", new_callable=mock_open)
    @patch("cli.minting.os.path.abspath")
    def test_mint_nft_legacy(self, mock_abspath, mock_file, mock_run):
         # Test the old mint_nft method
         self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": {"lovelace": 5000000}}
         }
         mock_run.return_value.stdout = b"Success"
         
         import asyncio
         asyncio.run(self.engine.mint_nft("LegacyAsset", 1))
         
         # Check if build-raw was called
         self.assertTrue(mock_run.called)

    def test_mint_nft_no_utxos(self):
        self.mock_client.get_utxos.return_value = {}
        import asyncio
        res = asyncio.run(self.engine.mint_nft("Asset", 1))
        self.assertFalse(res)

    @patch("cli.minting.subprocess.run")
    def test_mint_nft_value_int(self, mock_run):
        # Test handling of integer value instead of dict
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": 5000000}
        }
        
        # We expect 3 distinct calls: build, sign, read(cat)
        # Mock side effects
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "build-raw" in cmd:
                return MagicMock(returncode=0, stdout=b"")
            if "sign" in cmd:
                return MagicMock(returncode=0, stdout=b"")
            if "cat" in cmd:
                return MagicMock(returncode=0, stdout=b'{"type": "Tx", "cborHex": "..."}')
            return MagicMock(returncode=0, stdout=b"Success")
            
        mock_run.side_effect = side_effect
        
        import asyncio
        res = asyncio.run(self.engine.mint_nft("Asset", 1))
        self.assertTrue(res)

    @patch("cli.minting.subprocess.run")
    def test_mint_nft_process_error(self, mock_run):
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": 5000000}
        }
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr=b"Fail")
        import asyncio
        res = asyncio.run(self.engine.mint_nft("Asset", 1))
        self.assertFalse(res)

    @patch("cli.minting.subprocess.run")
    def test_mint_nft_generic_error(self, mock_run):
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": 5000000}
        }
        mock_run.side_effect = Exception("Generic fail")
        import asyncio
        res = asyncio.run(self.engine.mint_nft("Asset", 1))
        self.assertFalse(res)

    def test_mint_batch_invalid_utxo_format(self):
        # Key without '#'
        self.mock_client.get_utxos.return_value = {
            "tx_invalid": {"address": "addr", "value": {"lovelace": 10000000}}
        }
        import asyncio
        with self.assertLogs('cli.minting', level='ERROR') as cm:
            asyncio.run(self.engine.mint_batch_unique("Pref", 1, 1))
            self.assertTrue(any("Invalid UTXO format" in log for log in cm.output))

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open", new_callable=mock_open)
    @patch("cli.minting.os.path.abspath")
    def test_mint_batch_remainder_distribution(self, mock_abspath, mock_file, mock_run):
        """
        Verifies that lovelace is distributed correctly across output chunks,
        ensuring that any remainder from the division is added to the last chunk.
        """
        # 1000000 fee. Input 1000010. Remaining = 10.
        # 3 chunks. 10 // 3 = 3. Remainder 1.
        # Outputs: 3, 3, 4.
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": {"lovelace": 1000010}}
        }
        
        # Mock side effects for batch minting loop
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "build-raw" in cmd:
                return MagicMock(returncode=0, stdout=b"")
            if "sign" in cmd:
                return MagicMock(returncode=0, stdout=b"")
            if "cat" in cmd:
                 # Return valid JSON for Tx ID extraction/submission
                 return MagicMock(returncode=0, stdout=b'{"txId": "mock_tx_id"}')
            if "txid" in cmd:
                 return MagicMock(returncode=0, stdout=b"mock_tx_id")
            return MagicMock(returncode=0, stdout=b"")
            
        mock_run.side_effect = side_effect
        
        self.engine._get_tx_id = MagicMock(return_value="txid") 
        
        # We need to trigger 3 chunks. Batch size 150, Chunks > 1?
        # Chunk size is 80.
        # So we need > 160 assets to get 3 chunks.
        import asyncio
        asyncio.run(self.engine.mint_batch_unique("Pref", 161, 200)) # 1 batch logic
        
        # Verify call args for build-raw
        build_call = [c for c in mock_run.call_args_list if "build-raw" in c[0][0]][0]
        args = build_call[0][0]
        
        # Extract lovelace values from --tx-out
        # Iterate and look for --tx-out, then take next arg
        lovelaces = []
        iter_args = iter(args)
        for arg in iter_args:
            if arg == "--tx-out":
                val = next(iter_args)
                # addr+lovelace+mint
                parts = val.split("+")
                if len(parts) >= 2:
                    lovelaces.append(int(parts[1]))
        
        self.assertEqual(len(lovelaces), 3)
        self.assertEqual(sum(lovelaces), 10)
        self.assertIn(4, lovelaces) # One should carry the remainder

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open", new_callable=mock_open)
    @patch("cli.minting.os.path.abspath")
    def test_mint_batch_txid_fail(self, mock_abspath, mock_file, mock_run):
        # Setup inputs
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": {"lovelace": 5000000}}
        }
        # Side effect: build/sign success, but get_tx_id returns None?
        # Note: _get_tx_id is called internally.
        # We can mock _get_tx_id method of the engine.
        self.engine._get_tx_id = MagicMock(return_value=None)
        
        mock_run.return_value.stdout = b""
        
        import asyncio
        with self.assertLogs('cli.minting', level='ERROR') as cm:
             asyncio.run(self.engine.mint_batch_unique("Pref", 1, 1))
             self.assertTrue(any("Failed to get TxId" in log for log in cm.output))

    @patch("cli.minting.subprocess.run")
    @patch("cli.minting.open", new_callable=mock_open)
    @patch("cli.minting.os.path.abspath")
    def test_mint_batch_subprocess_stderr(self, mock_abspath, mock_file, mock_run):
        self.mock_client.get_utxos.return_value = {
            "tx#0": {"address": "addr", "value": {"lovelace": 5000000}}
        }
        
        # side_effect: success for mkdir, fail for build-raw
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "mkdir" in cmd:
                 return MagicMock(returncode=0)
            # Fail others (specifically build-raw which is first in loop)
            raise subprocess.CalledProcessError(1, "cmd", stderr=b"Custom Error Message")

        mock_run.side_effect = side_effect
        
        import asyncio
        with self.assertLogs('cli.minting', level='ERROR') as cm:
             with self.assertRaises(subprocess.CalledProcessError):
                 asyncio.run(self.engine.mint_batch_unique("Pref", 1, 1))
             self.assertTrue(any("STDERR: Custom Error Message" in log for log in cm.output))

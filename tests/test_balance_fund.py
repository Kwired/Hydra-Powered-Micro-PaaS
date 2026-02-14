"""Tests for cli/balance_utils.py — balance_commit_tx function."""
import unittest
from unittest.mock import patch, MagicMock

# Mock pycardano before importing the module
import sys

mock_pycardano = MagicMock()

# Create mock classes that behave properly
mock_tx_id_instance = MagicMock()
mock_pycardano.TransactionId.return_value = mock_tx_id_instance

mock_tx_input_instance = MagicMock()
mock_pycardano.TransactionInput.return_value = mock_tx_input_instance

mock_addr_instance = MagicMock()
mock_pycardano.Address.from_primitive.return_value = mock_addr_instance

mock_value_instance = MagicMock()
mock_pycardano.Value.return_value = mock_value_instance

mock_tx_output_instance = MagicMock()
mock_pycardano.TransactionOutput.return_value = mock_tx_output_instance

# Mock Transaction
mock_body = MagicMock()
mock_body.fee = 0
mock_body.inputs = []
mock_body.outputs = []
mock_body.collateral = None

mock_tx = MagicMock()
mock_tx.transaction_body = mock_body
mock_tx.to_cbor_hex.return_value = "balanced_cbor_hex"

mock_pycardano.Transaction.from_cbor.return_value = mock_tx

sys.modules['pycardano'] = mock_pycardano


class TestBalanceUtils(unittest.TestCase):

    def setUp(self):
        # Reset mocks for each test
        mock_body.fee = 0
        mock_body.inputs = []
        mock_body.outputs = []
        mock_body.collateral = None

    def test_balance_already_balanced(self):
        """If fee > 0, return draft unchanged."""
        mock_body.fee = 300000  # Already has fee set
        from cli.balance_utils import balance_commit_tx
        result = balance_commit_tx("already_balanced", {}, {}, "addr_test1")
        self.assertEqual(result, "already_balanced")

    def test_balance_adds_fee_input_and_change(self):
        """Normal balancing: adds fee input, collateral, and change output."""
        mock_body.fee = 0
        from cli.balance_utils import balance_commit_tx
        
        fee_utxo = {
            'transaction': {'id': 'aa' * 32},
            'index': 0,
            'value': {'ada': {'lovelace': 10_000_000}}  # 10 ADA
        }
        collateral_utxo = {
            'transaction': {'id': 'bb' * 32},
            'index': 1,
            'value': {'ada': {'lovelace': 5_000_000}}
        }
        
        result = balance_commit_tx("draft_cbor", fee_utxo, collateral_utxo, "addr_test1abc")
        
        # Should return serialized CBOR
        self.assertEqual(result, "balanced_cbor_hex")
        # Fee should be set
        self.assertEqual(mock_body.fee, 300000)
        # Inputs should have the fee input appended
        self.assertIn(mock_tx_input_instance, mock_body.inputs)
        # Collateral should be set
        self.assertEqual(mock_body.collateral, [mock_tx_input_instance])

    def test_balance_no_collateral(self):
        """Balancing with collateral_utxo=None should skip collateral."""
        mock_body.fee = 0
        from cli.balance_utils import balance_commit_tx
        
        fee_utxo = {
            'transaction': {'id': 'cc' * 32},
            'index': 0,
            'value': {'ada': {'lovelace': 5_000_000}}  # 5 ADA
        }
        
        result = balance_commit_tx("draft_cbor", fee_utxo, None, "addr_test1abc")
        self.assertEqual(result, "balanced_cbor_hex")
        # Collateral should remain None (not set)
        self.assertIsNone(mock_body.collateral)

    def test_balance_insufficient_funds(self):
        """If fee UTXO is too small, should raise exception."""
        mock_body.fee = 0
        from cli.balance_utils import balance_commit_tx
        
        fee_utxo = {
            'transaction': {'id': 'dd' * 32},
            'index': 0,
            'value': {'ada': {'lovelace': 500_000}}  # 0.5 ADA — too small
        }
        
        with self.assertRaises(Exception) as ctx:
            balance_commit_tx("draft_cbor", fee_utxo, None, "addr_test1abc")
        
        self.assertIn("Insufficient funds", str(ctx.exception))


class TestFundUtils(unittest.TestCase):

    def test_get_commit_output_dict_output_with_datum(self):
        """Parse CBOR tx with dict-based output containing datum."""
        import cbor2
        import binascii
        
        # Build a minimal CBOR transaction
        address_bytes = b'\x00' + b'\x01' * 28 + b'\x02' * 28  # 57-byte address
        body = {
            0: [],  # inputs
            1: [  # outputs
                {
                    0: address_bytes,
                    1: 50_000_000,        # lovelace
                    2: b'\x01\x02\x03'    # datum
                }
            ],
            2: 200_000  # fee
        }
        tx = [body, {}, None]
        cbor_hex = binascii.hexlify(cbor2.dumps(tx)).decode()
        
        from cli.fund_utils import get_commit_output
        addr_hex, lovelace, datum_cbor = get_commit_output(cbor_hex)
        
        self.assertIsNotNone(addr_hex)
        self.assertEqual(lovelace, 50_000_000)
        self.assertIsNotNone(datum_cbor)

    def test_get_commit_output_list_output(self):
        """Parse CBOR tx with list-based output containing datum."""
        import cbor2
        import binascii
        
        address_bytes = b'\x00' + b'\x01' * 28 + b'\x02' * 28
        body = {
            0: [],
            1: [
                [address_bytes, 25_000_000, b'\xAA\xBB']  # list format with datum
            ],
            2: 200_000
        }
        tx = [body, {}, None]
        cbor_hex = binascii.hexlify(cbor2.dumps(tx)).decode()
        
        from cli.fund_utils import get_commit_output
        addr_hex, lovelace, datum_cbor = get_commit_output(cbor_hex)
        
        self.assertIsNotNone(addr_hex)
        self.assertEqual(lovelace, 25_000_000)

    def test_get_commit_output_no_datum(self):
        """If no output has datum, return None tuple."""
        import cbor2
        import binascii
        
        address_bytes = b'\x00' + b'\x01' * 28 + b'\x02' * 28
        body = {
            0: [],
            1: [
                {0: address_bytes, 1: 10_000_000}  # No datum key
            ],
            2: 200_000
        }
        tx = [body, {}, None]
        cbor_hex = binascii.hexlify(cbor2.dumps(tx)).decode()
        
        from cli.fund_utils import get_commit_output
        addr_hex, lovelace, datum_cbor = get_commit_output(cbor_hex)
        
        self.assertIsNone(addr_hex)
        self.assertIsNone(lovelace)
        self.assertIsNone(datum_cbor)

    def test_get_commit_output_multiasset_amount(self):
        """Parse output with multi-asset amount [lovelace, assets_map]."""
        import cbor2
        import binascii
        
        address_bytes = b'\x00' + b'\x01' * 28 + b'\x02' * 28
        body = {
            0: [],
            1: [
                {
                    0: address_bytes,
                    1: [30_000_000, {b'\xFF' * 28: {b'token': 1}}],
                    2: b'\xCC\xDD'
                }
            ],
            2: 200_000
        }
        tx = [body, {}, None]
        cbor_hex = binascii.hexlify(cbor2.dumps(tx)).decode()
        
        from cli.fund_utils import get_commit_output
        addr_hex, lovelace, datum_cbor = get_commit_output(cbor_hex)
        
        self.assertEqual(lovelace, 30_000_000)


if __name__ == "__main__":
    unittest.main()


import pycardano
import binascii

def balance_commit_tx(draft_cbor_hex, fee_utxo, collateral_utxo, change_address_str):
    """
    Balances the draft commit transaction by adding fee inputs, collateral, 
    and change output.
    
    Args:
        draft_cbor_hex (str): CBOR hex of the drafted commit transaction.
        fee_utxo (dict): { 'transaction': {'id': ...}, 'index': ..., 'value': {'ada': {'lovelace': ...}} }
        collateral_utxo (dict): Similar structure for collateral (can be same as fee if pure ADA?).
        change_address_str (str): Address to send change to.
        
    Returns:
        str: Balanced transaction CBOR hex.
    """
    # 1. Deserialize Draft
    tx = pycardano.Transaction.from_cbor(draft_cbor_hex)
    
    # Check if already balanced (Fee > 0)
    if tx.transaction_body.fee > 0:
        return draft_cbor_hex
    
    # 2. Add Fee Input
    fee_tx_id_hex = fee_utxo['transaction']['id']
    fee_index = fee_utxo['index']
    fee_input = pycardano.TransactionInput(
        pycardano.TransactionId(bytes.fromhex(fee_tx_id_hex)),
        fee_index
    )
    tx.transaction_body.inputs.append(fee_input)
    
    # 3. Add Collateral
    if collateral_utxo:
        col_tx_id_hex = collateral_utxo['transaction']['id']
        col_index = collateral_utxo['index']
        col_input = pycardano.TransactionInput(
            pycardano.TransactionId(bytes.fromhex(col_tx_id_hex)),
            col_index
        )
        tx.transaction_body.collateral = [col_input]
    
    # 4. Calculate Fee and Change
    # Hardcoded fee for now (generous)
    FEE = 300000 # 0.3 ADA
    
    fee_amount = fee_utxo['value']['ada']['lovelace']
    change_amount = fee_amount - FEE
    
    if change_amount < 1000000: # MinUTXO 1 ADA
        raise Exception(f"Insufficient funds for fees/minUTXO. Fee UTXO: {fee_amount}, Fee: {FEE}")

    # Create Change Output
    # Need to convert address string to Address object
    # pycardano.Address.from_primitive(str)
    change_addr = pycardano.Address.from_primitive(change_address_str)
    
    change_output = pycardano.TransactionOutput(
        change_addr,
        pycardano.Value(change_amount)
    )
    tx.transaction_body.outputs.append(change_output)
    
    # Set Fee
    tx.transaction_body.fee = FEE
    
    # 5. Serialize
    return tx.to_cbor_hex()

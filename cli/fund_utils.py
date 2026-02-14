
import cbor2
import binascii

def get_commit_output(cbor_hex):
    """
    Parses the CBOR encoded transaction and returns the 
    address, value (lovelace), and inline datum (cbor bytes) 
    of the commit output (the one with datum).
    """
    tx_bytes = binascii.unhexlify(cbor_hex)
    tx = cbor2.loads(tx_bytes)
    
    # In Conway/Alonzo, tx is usually [body, witness, auxiliary_data, ...]
    # Body is index 0.
    body = tx[0]
    
    # Body is a map. Key 1 is inputs, Key 2 is outputs.
    # In Conway, Key 2 is outputs.
    outputs = body.get(1) # Inputs? No.
    # Map keys: 0=inputs, 1=outputs, 2=fee, ... (Wait, standard mapping?)
    # Shelley: 0=inputs, 1=outputs, 2=fee, 3=ttl
    # Alonzo/Babbage: 0=inputs, 1=outputs, 2=fee...
    
    # Let's handle generic map key for outputs (usually 1)
    outputs = body.get(1)
    
    for output in outputs:
        # Output is [Address, Amount, Datum?]
        # Address is bytes.
        # Amount is either int (Lovelace) or [Lovelace, MultiAsset]
        # Datum: Tag 24?
        
        # In Babbage/Conway, output can be a map!
        if isinstance(output, dict):
             # Map based output?
             address = output.get(0)
             amount = output.get(1)
             datum = output.get(2) # Inline datum
        elif isinstance(output, list):
             address = output[0]
             amount = output[1]
             datum = None
             if len(output) > 2:
                 datum = output[2]
        
        # If we have datum, this is likely the script output
        if datum:
             # Extract Lovelace
             lovelace = 0
             if isinstance(amount, int):
                 lovelace = amount
             elif isinstance(amount, list):
                 lovelace = amount[0] # [int, map]
             
             # Encode address to hex
             addr_hex = binascii.hexlify(address).decode()
             
             # Encode datum to CBOR bytes (to save to file)
             # The datum object itself needs to be serialized back to CBOR for CLI
             datum_cbor = cbor2.dumps(datum)
             
             return addr_hex, lovelace, datum_cbor

    return None, None, None


import re
import binascii

def parse_haskell_string(s):
    escapes = {
        'NUL': 0, 'SOH': 1, 'STX': 2, 'ETX': 3, 'EOT': 4, 'ENQ': 5, 'ACK': 6, 'BEL': 7,
        'BS': 8, 'HT': 9, 'LF': 10, 'VT': 11, 'FF': 12, 'CR': 13, 'SO': 14, 'SI': 15,
        'DLE': 16, 'DC1': 17, 'DC2': 18, 'DC3': 19, 'DC4': 20, 'NAK': 21, 'SYN': 22,
        'ETB': 23, 'CAN': 24, 'EM': 25, 'SUB': 26, 'ESC': 27, 'FS': 28, 'GS': 29,
        'RS': 30, 'US': 31, 'SP': 32, 'DEL': 127
    }
    
    out = bytearray()
    i = 0
    n = len(s)
    
    while i < n:
        c = s[i]
        if c == '\\':
            i += 1
            if i >= n: break
            
            if s[i] == '&': # null separator
                i += 1
                continue
                
            if s[i].isdigit():
                num_str = ""
                while i < n and s[i].isdigit():
                    num_str += s[i]
                    i += 1
                out.append(int(num_str))
                continue
            
            # Check for control chars (e.g. \ACK)
            # greedy match longest key
            found_ctrl = False
            for k, v in escapes.items():
                if s.startswith(k, i):
                    out.append(v)
                    i += len(k)
                    found_ctrl = True
                    break
            if found_ctrl:
                continue
                
            # Standard escapes
            if s[i] == 'n': out.append(10); i+=1; continue
            if s[i] == 'r': out.append(13); i+=1; continue
            if s[i] == 't': out.append(9); i+=1; continue
            if s[i] == '"': out.append(34); i+=1; continue
            if s[i] == '\\': out.append(92); i+=1; continue
            
            # fallback
            out.append(ord(s[i]))
            i += 1
        else:
            out.append(ord(c))
            i += 1
            
    return out

def extract():
    with open("fund.log", "r") as f:
        content = f.read()
    
    # Extract Initial Input
    # Looking for ctbrSpendInputs = fromList [..., TxIn (TxId {unTxId = SafeHash "f74f..."}) (TxIx {unTxIx = 1})]
    # Actually, the log order is not guaranteed.
    # But one input is my commit (a8bfe...), the other is Initial.
    
    # Regex for TxId
    ids = re.findall(r'SafeHash "([a-f0-9]{64})"', content)
    # ids[0] and ids[1] in ctbrSpendInputs block.
    # We know 'a8bfe...' is ours. The other is Initial.
    
    initial_txid = None
    for tid in ids:
        if tid.startswith("f74f"): # matches log
            initial_txid = tid
            break
            
    # Extract Datum
    # Datum "..."
    # The log has Datum "..."
    # We want the content inside quotes.
    # Be careful with nested quotes? Pattern: Datum "((?:[^"\\]|\\.)*)"
    match_datum = re.search(r'Datum "((?:[^"\\]|\\.)*)"', content)
    if match_datum:
        raw_datum = match_datum.group(1)
        datum_bytes = parse_haskell_string(raw_datum)
        with open("keys/commit_datum.cbor", "wb") as f:
            f.write(datum_bytes)
        print("Datum extracted to keys/commit_datum.cbor")
    else:
        print("Datum not found")

    print(f"Initial TxID: {initial_txid}")
    
    # Extract Script Hash
    # ScriptHash "6145..."
    match_script = re.search(r'ScriptHash "([a-f0-9]{56})"', content)
    if match_script:
        print(f"Script Hash: {match_script.group(1)}")

if __name__ == "__main__":
    extract()

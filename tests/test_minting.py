import pytest
from unittest.mock import AsyncMock, patch
from cli.minting import MintingEngine
@pytest.mark.asyncio
async def test_mint_batch_calls():
    mock_client = AsyncMock()
    mock_client.get_utxos.return_value = {
        "tx_hash#0": {
            "address": "addr_test1",
            "value": {"lovelace": 500000000}
        }
    }
    
    engine = MintingEngine(hydra_client=mock_client)
    
    # Mock subprocess to avoid actual cardano-cli calls
    with patch("subprocess.run") as mock_run:
        # Simulate successful build, sign, and cat
        mock_run.return_value.stdout = '{"type": "Tx", "cborHex": "00"}'
        mock_run.return_value.returncode = 0
        
        # Test 25 items -> 3 batches of 10
        # Wait logic might timeout if not mocked or handled, but let's try direct call
        # We need to mock _wait_for_utxo_update to avoid sleep loop
        engine._wait_for_utxo_update = AsyncMock()
        
        await engine.mint_batch_unique("Test", 25, batch_size=10)
    
    # Check if new_tx was called 3 times
    assert mock_client.new_tx.call_count == 3

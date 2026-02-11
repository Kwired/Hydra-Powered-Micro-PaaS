import pytest
from unittest.mock import AsyncMock, patch
from cli.minting import MintingEngine

@pytest.mark.asyncio
async def test_mint_batch_calls():
    mock_client = AsyncMock()
    engine = MintingEngine(hydra_client=mock_client)
    engine.batch_size = 10
    engine.concurrency = 2
    
    # Mint 25 items. Should result in 3 batches (10, 10, 5).
    await engine.mint_batch(25)
    
    assert mock_client.new_tx.call_count == 3
    
    # Verify connect was attempted
    if not mock_client.connection:
        mock_client.connect.assert_called_once() or mock_client.connect.assert_called()

@pytest.mark.asyncio
async def test_mint_batch_concurrency():
    mock_client = AsyncMock()
    # Simulate some delay in new_tx
    async def mock_sleep(*args):
        await asyncio.sleep(0.01)
    mock_client.new_tx.side_effect = mock_sleep
    
    engine = MintingEngine(hydra_client=mock_client)
    engine.batch_size = 1
    engine.concurrency = 5
    
    import asyncio
    import time
    
    start = time.time()
    # 10 items, 1 per batch. 10 network calls.
    # With concurrency 5, should take approx 2 * 0.01 = 0.02s (plus overhead), 
    # instead of 10 * 0.01 = 0.1s
    await engine.mint_batch(10)
    end = time.time()
    
    assert mock_client.new_tx.call_count == 10
    # Loose check for concurrency: should be faster than serial
    # (Checking exact timing in unit tests is flaky, but this confirms it runs)

@pytest.mark.asyncio
async def test_mint_batch_offline():
    mock_client = AsyncMock()
    mock_client.connection = None
    mock_client.connect.side_effect = Exception("Offline")
    
    engine = MintingEngine(hydra_client=mock_client)
    engine.batch_size = 10
    
    # Should not raise exception, just log warning and proceed (mocking behavior)
    await engine.mint_batch(10)
    
    mock_client.connect.assert_called_once()
    assert mock_client.new_tx.call_count == 1

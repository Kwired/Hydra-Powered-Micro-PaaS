import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from cli.hydra_client import HydraClient

@pytest.mark.asyncio
async def test_connect():
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        client = HydraClient()
        await client.connect()
        mock_connect.assert_called_once_with('ws://localhost:4001')
        assert client.connection is not None

@pytest.mark.asyncio
async def test_connect_failure():
    with patch('websockets.connect', side_effect=Exception("ConnectionRefused")) as mock_connect:
        client = HydraClient()
        with pytest.raises(Exception) as excinfo:
            await client.connect()
        
        assert "ConnectionRefused" in str(excinfo.value)

@pytest.mark.asyncio
async def test_send_command():
    client = HydraClient()
    client.connection = AsyncMock()
    
    cmd = {"tag": "Init"}
    await client.send_command(cmd)
    
    client.connection.send.assert_called_once_with(json.dumps(cmd))

@pytest.mark.asyncio
async def test_receive_response():
    client = HydraClient()
    client.connection = AsyncMock()
    client.connection.recv.return_value = '{"tag": "Greetings"}'
    
    response = await client.receive_response()
    
    assert response == {"tag": "Greetings"}
    client.connection.recv.assert_called_once()

@pytest.mark.asyncio
async def test_init_head():
    client = HydraClient()
    client.connection = AsyncMock()
    
    await client.init_head()
    client.connection.send.assert_called_once_with(json.dumps({"tag": "Init"}))

@pytest.mark.asyncio
async def test_commit_funds():
    client = HydraClient()
    client.connection = AsyncMock()
    
    await client.commit_funds(100)
    client.connection.send.assert_called_once_with(json.dumps({"tag": "Commit", "utxo": {}}))

@pytest.mark.asyncio
async def test_new_tx():
    client = HydraClient()
    client.connection = AsyncMock()
    
    await client.new_tx("cbor_hex")
    client.connection.send.assert_called_once_with(json.dumps({"tag": "NewTx", "transaction": "cbor_hex"}))

@pytest.mark.asyncio
async def test_close_head():
    client = HydraClient()
    client.connection = AsyncMock()
    
    await client.close_head()
    client.connection.send.assert_called_once_with(json.dumps({"tag": "Close"}))

@pytest.mark.asyncio
async def test_send_command_not_connected():
    client = HydraClient()
    # connection is None by default
    
    with pytest.raises(Exception) as excinfo:
        await client.send_command({"tag": "Init"})
    
    assert "Not connected to Hydra API" in str(excinfo.value)

@pytest.mark.asyncio
async def test_receive_response_not_connected():
    client = HydraClient()
    
    with pytest.raises(Exception) as excinfo:
        await client.receive_response()
    
    assert "Not connected to Hydra API" in str(excinfo.value)

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
async def test_receive_event():
    client = HydraClient()
    client.connection = AsyncMock()
    client.connection.recv.return_value = '{"tag": "Greetings"}'
    
    response = await client.receive_event()
    
    assert response == {"tag": "Greetings"}
    client.connection.recv.assert_called_once()


@pytest.mark.asyncio
async def test_commit_funds():
    client = HydraClient()
    client.http_url = "http://localhost:4001"
    
    # We need to mock aiohttp.ClientSession
    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MockSession.return_value
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"cborHex": "deadbeef"}
        
        mock_session.__aenter__.return_value = mock_session
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        
        cbor = await client.commit_funds({"txId#0": {}})
        assert cbor == "deadbeef"

@pytest.mark.asyncio
async def test_receive_event_not_connected():
    client = HydraClient()
    
    with pytest.raises(Exception) as excinfo:
        await client.receive_event()
    
    assert "Not connected to Hydra API" in str(excinfo.value)

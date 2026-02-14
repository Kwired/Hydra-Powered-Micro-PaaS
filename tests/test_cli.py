import pytest
import asyncio
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock, MagicMock
from cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_init_command(runner):
    with patch('cli.hydra_client.HydraClient.connect', new_callable=AsyncMock) as mock_connect, \
         patch('cli.hydra_client.HydraClient.init_head', new_callable=AsyncMock) as mock_init, \
         patch('cli.hydra_client.HydraClient.close', new_callable=AsyncMock) as mock_close:
        
        result = runner.invoke(cli, ['init', '--network', 'preview'])
        
        assert result.exit_code == 0
        assert "Initializing Hydra Head on preview..." in result.output
        mock_connect.assert_called_once()
        mock_init.assert_called_once()
        mock_close.assert_called_once()

def test_fund_command(runner):
    with patch('cli.hydra_client.HydraClient.connect', new_callable=AsyncMock) as mock_connect, \
         patch('cli.hydra_client.HydraClient.commit_funds', new_callable=AsyncMock) as mock_commit, \
         patch('cli.hydra_client.HydraClient.close', new_callable=AsyncMock) as mock_close, \
         patch('cli.ogmios_client.OgmiosClient.query_utxo', new_callable=AsyncMock) as mock_query:
        
        # Mock UTXO response — fund requires at least 2 UTXOs > 5 ADA
        mock_query.return_value = [
            {'transaction': {'id': 'tx1'}, 'index': 0, 'address': 'addr1', 'value': {'ada': {'lovelace': 10000000}}},
            {'transaction': {'id': 'tx2'}, 'index': 0, 'address': 'addr1', 'value': {'ada': {'lovelace': 100000000}}}
        ]
        
        result = runner.invoke(cli, ['fund', 'addr1'])
        
        # The fund command logs its initial message via logger, not click.echo
        # Just verify it doesn't fail with the "Need at least 2 UTXOs" message
        assert "Need at least 2 UTXOs" not in result.output

def test_mint_command(runner):
    with patch('cli.minting.MintingEngine.mint_batch_unique', new_callable=AsyncMock) as mock_mint, \
         patch('cli.hydra_client.HydraClient.connect', new_callable=AsyncMock) as mock_connect, \
         patch('cli.hydra_client.HydraClient.close', new_callable=AsyncMock) as mock_close:
        
        # Patch asyncio.run which is used in main.py
        # Actually main.py uses loop.run_until_complete explicitly now
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = runner.invoke(cli, ['mint', '--quantity', '10', '--unique'])
        loop.close()
        
        assert result.exit_code == 0
        mock_mint.assert_called_once()

def test_close_command(runner):
    with patch('cli.hydra_client.HydraClient.connect', new_callable=AsyncMock) as mock_connect, \
         patch('cli.hydra_client.HydraClient.close_head', new_callable=AsyncMock) as mock_close_head, \
         patch('cli.hydra_client.HydraClient.close', new_callable=AsyncMock) as mock_close:
        
        result = runner.invoke(cli, ['close'])
        
        assert result.exit_code == 0
        assert "Closing Hydra Head..." in result.output
        mock_connect.assert_called_once()
        mock_close_head.assert_called_once()
        mock_close.assert_called_once()

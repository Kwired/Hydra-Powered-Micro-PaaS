import pytest
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock
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
         patch('cli.hydra_client.HydraClient.close', new_callable=AsyncMock) as mock_close:
        
        result = runner.invoke(cli, ['fund', '1000000'])
        
        assert result.exit_code == 0
        assert "Funding Hydra Head with 1000000 lovelace..." in result.output
        mock_connect.assert_called_once()
        mock_commit.assert_called_once_with(1000000)
        mock_close.assert_called_once()

def test_mint_command(runner):
    with patch('cli.minting.MintingEngine.mint_batch', new_callable=AsyncMock) as mock_mint:
        
        result = runner.invoke(cli, ['mint', '--count', '10'])
        
        assert result.exit_code == 0
        assert "Minting 10 NFTs..." in result.output
        mock_mint.assert_called_once_with(10)

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

import click
import asyncio
import logging
import json
import subprocess
import os
from typing import Dict, Any, List
from .hydra_client import HydraClient
from .ogmios_client import OgmiosClient
from .minting import MintingEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def transform_utxo_ogmios_to_hydra(ogmios_utxos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transforms Ogmios UTXO format to Hydra's expected JSON format.
    Ogmios list item: 
      {
        'transaction': {'id': '...'}, 
        'index': 0, 
        'address': '...', 
        'value': {'ada': {'lovelace': 10000000}}
      }
    Hydra map format:
      {
        "TxId#Index": {
          "address": "...",
          "value": { "lovelace": 10000000 } 
        }
      }
    """
    hydra_utxo = {}
    for u in ogmios_utxos:
        tx_id = u['transaction']['id']
        index = u['index']
        key = f"{tx_id}#{index}"
        
        # Transform value
        # Ogmios: {'ada': {'lovelace': 1000}} -> Hydra/CardanoJSON: {'lovelace': 1000}
        # Note: Handling native assets would require more complex logic.
        val = u['value']
        hydra_val = {}
        if 'ada' in val and 'lovelace' in val['ada']:
            hydra_val['lovelace'] = val['ada']['lovelace']
        
        # Add other assets if present (omitted for now for simple ADA funding)
        
        hydra_utxo[key] = {
            "address": u['address'],
            "value": hydra_val,
            "datum": u.get("datum"),
            "datumHash": u.get("datumHash"),
            "inlineDatum": u.get("inlineDatum"),
            "referenceScript": u.get("script")
        }
        # Filter out None values to keep it clean
        hydra_utxo[key] = {k: v for k, v in hydra_utxo[key].items() if v is not None}
        
    return hydra_utxo

@click.group()
def cli():
    """Hydra Powered Micro-PaaS CLI for NFT Minting"""
    pass

@cli.command()
@click.option('--network', default='preprod', help='Cardano network to use')
def init(network):
    """Initialize a new Hydra Head"""
    click.echo(f"Initializing Hydra Head on {network}...")
    
    async def _init():
        client = HydraClient()
        try:
            await client.connect()
            await client.init_head()
        except Exception as e:
            logger.error(f"Error initializing head: {e}")
        finally:
            await client.close()

    asyncio.run(_init())

@cli.command()
@click.argument('address')
def fund(address):
    """Fund the Hydra Head (single-party manual balance)."""
    async def _fund():
        ogmios = OgmiosClient()
        try:
            logger.info(f"Funding Hydra Head with funds from {address}...")
            await ogmios.connect()
            
            # 1. Get UTXOs
            utxos = await ogmios.query_utxo(address)
            if not utxos:
                 click.echo("No UTXOs found.")
                 return

            # Filter dust > 5 ADA
            utxos = [u for u in utxos if u['value']['ada']['lovelace'] > 5000000]

            if len(utxos) < 2:
                 click.echo("Need at least 2 UTXOs > 5 ADA (1 commit, 1 fee/collateral).")
                 return
                 
            # Strategy (Hydra 1.2.0 - fuel marking deprecated):
            # ALL UTXOs at the signing key address are fuel.
            # Commit the SMALLEST viable UTXO (>= 10 ADA)
            # Leave larger UTXOs as fuel for L1 transaction fees.
            utxos.sort(key=lambda u: u['value']['ada']['lovelace'])
            
            commit_utxo = None
            for u in utxos:
                lovelace = u['value']['ada']['lovelace']
                if 10_000_000 <= lovelace <= 150_000_000:
                    commit_utxo = u
                    break
            if not commit_utxo:
                commit_utxo = utxos[0]
            
            # Fee UTXO: any other UTXO > 5 ADA
            commit_id = f"{commit_utxo['transaction']['id']}#{commit_utxo['index']}"
            fee_utxo = None
            for u in utxos:
                uid = f"{u['transaction']['id']}#{u['index']}"
                if uid != commit_id and u['value']['ada']['lovelace'] >= 5_000_000:
                    fee_utxo = u
                    break
            
            if not fee_utxo:
                click.echo("No suitable fee UTXO found!")
                return
            
            logger.info(f"Selected UTXO for commitment: {commit_utxo['value']['ada']['lovelace'] / 1e6:.1f} ADA")
            logger.info(f"Selected UTXO for fees/collateral: {fee_utxo['value']['ada']['lovelace'] / 1e6:.1f} ADA")

            # 2. Call POST /commit
            import requests
            # Helper to get TxID
            def get_tx_id(u):
                return u['transaction']['id']

            commit_payload = {
                f"{get_tx_id(commit_utxo)}#{commit_utxo['index']}": {
                    "address": address,
                    "value": { "lovelace": commit_utxo['value']['ada']['lovelace'] }
                }
            }
            
            url = "http://localhost:4001/commit"
            headers = {'Content-Type': 'application/json'}
            resp = requests.post(url, json=commit_payload, headers=headers)
            
            if resp.status_code != 200:
                logger.error(f"Failed to draft commit tx: {resp.text}")
                return

            draft_cbor = resp.json().get('cborHex')
            
            # 3. Balance Transaction using PyCardano
            from cli.balance_utils import balance_commit_tx
            
            try:
                balanced_cbor = balance_commit_tx(
                    draft_cbor, 
                    fee_utxo, 
                    fee_utxo, # Use same for collateral
                    address
                )
            except Exception as e:
                logger.error(f"Failed to balance transaction: {e}")
                return

            # Save balanced CBOR
            import json
            with open("keys/commit.balanced.cbor", "w") as f:
                 json.dump({"type": "Tx ConwayEra", "description": "", "cborHex": balanced_cbor}, f)
            
            # 4. Sign and Submit
            import subprocess
            logger.info("Signing commit transaction...")
            
            cmd_sign = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "conway", "transaction", "sign",
                "--tx-body-file", "/keys/commit.balanced.cbor",
                "--signing-key-file", "/keys/cardano.sk",
                "--testnet-magic", "1",
                "--out-file", "/keys/commit.signed"
            ]
            subprocess.run(cmd_sign, check=True)
            
            logger.info("Submitting commit transaction...")
            cmd_submit = [
                "docker", "compose", "exec", "cardano-node",
                "cardano-cli", "conway", "transaction", "submit",
                "--tx-file", "/keys/commit.signed",
                "--testnet-magic", "1",
                "--socket-path", "/ipc/node.socket"
            ]
            res_submit = subprocess.run(cmd_submit, capture_output=True, text=True)
            if res_submit.returncode != 0:
                logger.error(f"Submit failed: {res_submit.stderr}")
            else:
                logger.info(f"Commit transaction submitted successfully! Output: {res_submit.stdout}")

        except Exception as e:
            logger.error(f"Error funding head: {e}")
        finally:
            await ogmios.close()

    asyncio.run(_fund())



@cli.command()
def close():
    """Close the Hydra Head"""
    click.echo("Closing Hydra Head...")
    async def _close():
        client = HydraClient()
        try:
            await client.connect()
            await client.close_head()
            # await client.fanout_head() # Optional: auto-fanout
        except Exception as e:
            logger.error(f"Error closing head: {e}")
        finally:
            await client.close()

    asyncio.run(_close())

@cli.command()
def abort():
    """Abort the Hydra Head"""
    click.echo("Aborting Hydra Head...")
    async def _abort():
        client = HydraClient()
        try:
            await client.connect()
            await client.send_command({"tag": "Abort"})
            event = await client.wait_for_event("HeadIsAborted")
            if event:
                logger.info("Head aborted successfully!")
        except Exception as e:
            logger.error(f"Error aborting head: {e}")
        finally:
            await client.close()

    asyncio.run(_abort())

@cli.command()
def fanout():
    """Fanout funds from a Closed Hydra Head."""
    click.echo("Fanning out funds...")
    async def _fanout():
        client = HydraClient()
        try:
            await client.connect()
            await client.send_command({"tag": "Fanout"})
            event = await client.wait_for_event("HeadIsFinalized")
            if event:
                logger.info("Head finalized! Funds returned to L1.")
        except Exception as e:
            logger.error(f"Error fanning out: {e}")
        finally:
            await client.close()

    asyncio.run(_fanout())

@cli.command()
@click.option('--asset-name', default="HydraNFT", help="Name prefix for assets")
@click.option('--quantity', default=1, help="Total number of assets to mint")
@click.option('--batch-size', default=1, help="Assets per transaction (Batching)")
@click.option('--unique', is_flag=True, help="Mint unique assets (asset_name_{i})")
def mint(asset_name, quantity, batch_size, unique):
    """Mint NFTs inside the Hydra Head."""
    async def _mint():
        client = HydraClient()
        try:
            await client.connect()
            engine = MintingEngine(client)
            
            if unique:
                await engine.mint_batch_unique(asset_name, quantity, batch_size)
            else:
                # Legacy single-asset-name minting
                if batch_size > 1:
                    logger.warning("Batching is currently optimized for --unique mode. Minting sequentially.")
                
                await engine.mint_nft(asset_name, quantity)
        finally:
            await client.close()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_mint())

if __name__ == '__main__':
    cli()

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
    """Fund the Hydra Head with funds from ADDRESS. Commits the largest UTXO found."""
    click.echo(f"Funding Hydra Head with funds from {address}...")
    
    async def _fund():
        ogmios = OgmiosClient()
        hydra = HydraClient()
        try:
            # 1. Query Funds
            await ogmios.connect()
            utxos = await ogmios.query_utxo(address)
            if not utxos:
                click.echo(f"No funds found at {address}")
                return
            
            logger.info(f"Found {len(utxos)} UTXOs.")
            
            # Sort by lovelace ascending (Smallest first)
            utxos.sort(key=lambda u: u['value']['ada']['lovelace'], reverse=False)
            
            # Filter out very small dust (< 5 ADA) to avoid minUTXO issues
            utxos = [u for u in utxos if u['value']['ada']['lovelace'] > 5000000]

            if not utxos:
                 click.echo("No suitable UTXOs found (> 5 ADA).")
                 return

            # Commit the smallest one
            utxo_to_commit = [utxos[0]]
            logger.info(f"Selected smallest UTXO for commitment: {utxo_to_commit[0]['value']['ada']['lovelace']} lovelace")
            
            if len(utxos) > 1:
                logger.info(f"Leaving {len(utxos)-1} UTXOs for fees.")
            else:
                logger.warning("Warning: Only 1 UTXO found. Committing it might fail if no other funds exist for fees.")

            # 2. Transform to Hydra format
            hydra_utxo = transform_utxo_ogmios_to_hydra(utxo_to_commit)
            
            # 3. Build Commit Tx
            await hydra.connect()
            cbor_hex = await hydra.commit_funds(hydra_utxo)
            
            if not cbor_hex:
                logger.error("Failed to build commit transaction.")
                return

            # 4. Sign and Submit via cardano-cli (using keys volume)
            commit_raw_path = "keys/commit.raw"
            
            # Write raw tx wrapper
            with open(commit_raw_path, "w") as f:
                 json.dump({"type": "Tx ConwayEra", "description": "", "cborHex": cbor_hex}, f)
            
            logger.info("Signing commit transaction...")
            try:
                subprocess.run([
                    "docker", "compose", "exec", "cardano-node",
                    "cardano-cli", "latest", "transaction", "sign",
                    "--tx-body-file", "/keys/commit.raw",
                    "--signing-key-file", "/keys/cardano.sk",
                    "--testnet-magic", "1",
                    "--out-file", "/keys/commit.signed"
                ], check=True)
                
                logger.info("Submitting commit transaction...")
                subprocess.run([
                    "docker", "compose", "exec", "cardano-node",
                    "cardano-cli", "latest", "transaction", "submit",
                    "--tx-file", "/keys/commit.signed",
                    "--testnet-magic", "1",
                    "--socket-path", "/ipc/node.socket"
                ], check=True)
                
                logger.info("Commit transaction submitted to L1!")
                
                # Wait for events
                event = await hydra.wait_for_event("Committed")
                if event:
                    logger.info("Funds committed successfully (Confirmed by Node)!")
                    
                    # Also check if head is open
                    open_event = await hydra.wait_for_event("HeadIsOpen", timeout=10)
                    if open_event:
                        logger.info("Head is now OPEN!")
                else:
                    logger.error("Commit submitted but no confirmation received.")
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"Cardano CLI failed: {e}")
            
        except Exception as e:
            logger.error(f"Error funding head: {e}")
        finally:
            await ogmios.close()
            await hydra.close()

    asyncio.run(_fund())

@cli.command()
@click.option('--count', default=1, help='Number of NFTs to mint')
def mint(count):
    """Mint NFTs in the Hydra Head"""
    click.echo(f"Minting {count} NFTs...")
    
    async def _mint():
        engine = MintingEngine()
        await engine.mint_batch(count)

    asyncio.run(_mint())

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
                # Legacy single-asset-name minting (loops if quantity > 1 not supported effectively yet in old method)
                # Actually old method `mint_nft` takes quantity but mints SAME asset name with quantity.
                # If user wants 100 copies of same asset, use old method.
                if batch_size > 1:
                    # TODO: Implement batching for same-asset if needed
                    logger.warning("Batching only supported for --unique mode currently.")
                
                await engine.mint_nft(asset_name, quantity)
        finally:
            await client.close()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_mint())

if __name__ == '__main__':
    cli()

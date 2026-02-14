# Metadata Standards (CIP-25)

This guide covers how the Turbo Minting Engine handles NFT metadata in compliance with **CIP-25**.

## Automatic Generation

In **Turbo Mode**, metadata is automatically generated for each batch to ensure unique assets without manual JSON file creation for every single token.

### Schema
The `mint_10k_turbo` function generates metadata dynamically following this schema:

```json
{
  "721": {
    "<POLICY_ID>": {
      "<AssetPrefix>_<Index>": {
        "name": "<AssetPrefix> #<Index>",
        "image": "ipfs://QmYourDefaultCID",
        "mediaType": "image/png",
        "description": "Minted via Hydra Turbo Engine",
        "attributes": {
            "Batch": "<BatchNumber>",
            "Sequence": "<Index>"
        }
      }
    }
  }
}
```

### Batching Strategy

To optimize throughput and reduce file I/O:
1.  Metadata is **not** embedded in the transaction (to save L2 block space and avoid `TxTooLarge`).
2.  Instead, metadata is typically handled off-chain or via a separate metadata registry transaction in a production Hydra setup.
3.  For this performance benchmark, we focus on the **minting mechanies** (Policy ID + Asset Name injection). The `mint_10k_turbo` logic places the asset names directly into the transaction `mint` field.

## Customizing Metadata

To customize the metadata generated during the turbo mint:

1.  Open `cli/minting.py`.
2.  Locate the `_generate_metadata` method (if enabled) or the loop where `full_mint_str` is constructed.
3.  Modify the asset name generation logic:
    ```python
    asset_name = f"{prefix}_{batch_start_index + i:05d}"
    ```

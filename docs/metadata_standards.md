# Metadata Standards (CIP-25)

This guide covers the metadata standards required for minting NFTs with the Hydra-Powered NFT Drop Engine.

## CIP-25 Compliance
The engine enforces [CIP-25](https://cips.cardano.org/cips/cip25/) standards for NFT metadata.

## JSON Structure
Metadata should be structured as follows:

```json
{
  "721": {
    "<policy_id>": {
      "<asset_name>": {
        "name": "NFT Name",
        "image": "ipfs://<ipfs_cid>",
        "mediaType": "image/png",
        "description": "Description of the NFT",
        "files": [
          {
            "name": "High Res Image",
            "mediaType": "image/png",
            "src": "ipfs://<ipfs_cid>"
          }
        ],
        "attributes": {
            "Background": "Blue",
            "Rarity": "Common"
        }
      }
    }
  }
}
```

## Automating Metadata Generation
The CLI tool supports a template-based metadata generation. Place a `metadata_template.json` in your working directory, and the tool will dynamically populate fields like `name` and `image` index.

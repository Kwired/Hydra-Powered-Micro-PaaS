# Asset Policy Configuration

This guide explains how to configure minting policies for the Hydra-Powered NFT Drop Engine.

## Overview
A minting policy script defines the rules for minting and burning assets. In Cardano, this is typically a Plutus script or a native script.

## Configuration Steps
1. **Define Policy Script**: Create a file named `policy.script` (native) or `policy.plutus` (Plutus V2).
2. **Generate Policy ID**: Use the Cardano CLI or the provided tool to hash the script and generate the Policy ID.
3. **Environment Variable**: Set the `MINTING_POLICY_ID` environment variable in your `.env` file or Docker configuration.

## Example Native Script
```json
{
  "type": "all",
  "scripts": [
    {
      "type": "sig",
      "keyHash": "..."
    },
    {
      "type": "before",
      "slot": 123456789
    }
  ]
}
```

## Using with the CLI
When running the `mint` command, you can specify the policy script path:
```bash
python cli/main.py mint --count 10 --policy-script ./policy.script
```

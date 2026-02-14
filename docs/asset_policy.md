# Asset Policy Configuration

This guide explains how the minting policy is configured for the **Hydra-Powered Turbo Minting Engine**.

## Overview

In the Turbo Mint pipeline, we use a **Native Script** (Phase 1) to ensure high-speed compatibility with `cardano-cli` transaction building.

## Default Configuration

The project comes with a pre-configured policy script located at `keys/policy.script`.

### Policy Script (`keys/policy.script`)
The current policy is a simple "signature-based" policy, meaning only the owner of `keys/cardano.sk` can mint assets.

```json
{
  "keyHash": "YOUR_KEY_HASH_HERE",
  "type": "sig"
}
```

> **Note:** The `manual_e2e.py` script automatically generates this file corresponding to your `cardano.sk` signing key during the setup phase.

## Customizing the Policy

To use a different policy (e.g., time-locked):

1.  **Edit the Script**: Modify `keys/policy.script` with your desired rules (e.g., `before` slot).
2.  **Regenerate Policy ID**:
    ```bash
    cardano-cli transaction policyid --script-file keys/policy.script > keys/policy.id
    ```
3.  **Update Config**:
    open `cli/minting.py` and update the `POLICY_ID` constant to match your new Policy ID.

## Plutus Support

While the Turbo Engine is optimized for Native Scripts (due to their smaller transaction size, allowing more assets per batch), Plutus scripts are supported by the underlying Hydra node. To use Plutus:
1.  Reference your `.plutus` script in the `cardano-cli` build command commands in `cli/minting.py`.
2.  Add the necessary collateral inputs and redeemer arguments.

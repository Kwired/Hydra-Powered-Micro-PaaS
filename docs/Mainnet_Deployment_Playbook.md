# Mainnet Deployment Playbook

Deploying a Hydra Head to the Cardano Mainnet introduces significant financial risk. This playbook outlines the strict security procedures and configuration checks required before deploying HydraLite templates on mainnet.

> [!CAUTION]
> Do not skip any steps in this playbook. Deploying to mainnet means you are locking real, financial ADA into a Layer-2 state channel. Errors in UTXO management or exposed WebSocket endpoints can result in permanent loss of funds.

## 1. Network Configuration Switch

By default, HydraLite is configured for `preprod`. To switch to Mainnet, you must update both the `.env` file and your Docker configuration.

1. Open your `.env` file.
2. Change the network variable:
   ```env
   CARDANO_NETWORK=mainnet
   ```
3. In your `docker-compose.yml`, ensure the `hydra-node` and `cardano-node` commands are pointing to the mainnet topology and genesis files.

## 2. Infrastructure Security Checklist

Before booting the Docker containers on a production server, verify the following:

- [ ] **Firewall Ports:** Ensure that port `4001` (Hydra API) and `1337` (Ogmios) are **blocked** from public internet access. These should only be accessible internally by the FastAPI middleware engine.
- [ ] **CORS Configuration:** Verify that `ALLOWED_ORIGINS` in your `.env` file is strictly set to your production frontend domain (e.g., `https://my-dapp.com`). Never use `*` on mainnet.
- [ ] **SSL/TLS:** The FastAPI engine must be hosted behind a reverse proxy (like Nginx or Traefik) equipped with an SSL certificate. Never send mainnet API requests over plain HTTP.

## 3. Funding the Head

Mainnet Hydra Heads require real ADA. We strongly recommend testing your template logic with small amounts of ADA before committing massive liquidity.

1. Generate your production keys locally and back them up securely. Never leave the `.skey` file on a publicly accessible web server.
2. Transfer exactly 50 ADA to the generated payment address.
3. Wait for the transaction to reach at least 5 confirmations before executing the `fund` command.

## 4. Closing the Head Safely

The most critical phase of a Hydra lifecycle is the Head closure. 

> [!IMPORTANT]  
> A Hydra Head requires a "Contestation Period" to close safely. Ensure your server will remain online and connected to the Cardano Mainnet for at least 12 hours after triggering the `close` command. If your node goes offline during the contestation period, your funds could be trapped.

Always utilize the HydraLite CLI to close the head safely:
```bash
python -m cli.main close
```
Monitor the logs until you see the `FanoutTx` successfully broadcasted to Layer 1.

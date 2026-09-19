# System Architecture

The HydraLite system consists of a multi-tiered architecture designed to isolate blockchain heavy-lifting from standard web application operations.

## Components

### 1. Hydra Infrastructure Layer
- **Cardano Node**: Maintains connection to the Cardano network (L1).
- **Mithril Client**: Accelerates initial node syncing.
- **Ogmios**: A lightweight bridge interface for Cardano node.
- **Hydra Node**: The state channel node (L2) that processes off-chain transactions at high speed.

### 2. Application Layer
- **API (FastAPI)**: Serves HTTP requests from clients, interfacing with the Hydra node to submit transactions.
- **Minting Engine (CLI)**: A Python engine that utilizes parallel workers to construct, sign, and submit large batches of transactions to the Hydra Node.

### 3. Frontend Layer
- **Dashboard**: A React application providing an interface to interact with the minting engine and monitor Hydra Head state.

## Interaction Flow
1. The **Dashboard** sends a mint request to the **API**.
2. The **API/CLI** queries the **Hydra Node** for available UTXOs inside the Head.
3. The **Minting Engine** splits the UTXOs and uses multiple parallel workers to build and sign transactions using `cardano-cli`.
4. The signed transactions are submitted back to the **Hydra Node** via WebSockets.
5. Once confirmed in the L2 state, the transaction is considered finalized off-chain.

# API & WebSocket Reference

The HydraLite application layer provides an asynchronous REST and WebSocket API built on FastAPI. It abstracts Cardano Layer 2 state channel submission, balance verification, and telemetry streams into standard HTTP/JSON contracts.

---

## Service Endpoints & Conventions

- **Base URL**: `http://localhost:8000` (Local) or `https://your-domain.com` (Production)
- **API Prefix**: `/api/v1`
- **Default Content-Type**: `application/json`
- **Interactive Documentation**: Swagger UI is accessible at `GET /docs` and OpenAPI JSON schema at `GET /openapi.json`.

---

## Health & Diagnostics

### `GET /health`
Returns the operational state of the API gateway.

#### Request
```bash
curl -X GET http://localhost:8000/health
```

#### Response (`200 OK`)
```json
{
  "status": "ok",
  "service": "hydra-micro-paas",
  "version": "1.0.0"
}
```

---

## Payment & State Operations

### `POST /api/v1/pay`
Constructs, signs, and broadcasts a state channel transaction for a registered action. Action costs and constraints are resolved server-side against `pricing.yaml`.

#### Headers
| Header | Value | Required |
|:---|:---|:---:|
| `Content-Type` | `application/json` | Yes |

#### Request Body
```json
{
  "user_id": "usr_99842a1b",
  "action": "mint_nft"
}
```

#### Field Specifications
| Field | Type | Description |
|:---|:---|:---|
| `user_id` | `string` | Unique identifier for the initiating user or client account |
| `action` | `string` | Action identifier mapped to an on-chain fee structure in `pricing.yaml` (e.g., `mint_nft`, `send_tip`, `place_order`) |

#### Successful Response (`200 OK`)
```json
{
  "status": "success",
  "tx_id": "7f19cb8d9e2a1bb5920d321588647acae34a36287c8d9e1f10c4a8e2b801a91c",
  "latency_ms": 14.8,
  "amount_lovelace": 1000000
}
```

#### Error Responses
- **`400 Bad Request`**: Unrecognized action identifier.
  ```json
  {
    "detail": "Action 'invalid_action' is not registered in pricing.yaml"
  }
  ```
- **`503 Service Unavailable`**: The underlying Hydra Head is not in the `Open` state.
  ```json
  {
    "detail": "Hydra Head is currently in 'Closed' or 'Final' state. Transaction cannot be submitted."
  }
  ```

---

### `GET /api/v1/verify/{tx_id}`
Checks whether a transaction hash has been validated and included in the current Hydra snapshot.

#### Request
```bash
curl -X GET http://localhost:8000/api/v1/verify/7f19cb8d9e2a1bb5920d321588647acae34a36287c8d9e1f10c4a8e2b801a91c
```

#### Response (`200 OK`)
```json
{
  "status": "confirmed",
  "tx_id": "7f19cb8d9e2a1bb5920d321588647acae34a36287c8d9e1f10c4a8e2b801a91c",
  "snapshot_number": 421,
  "confirmed_at": "2026-10-15T23:55:01Z"
}
```

---

## Telemetry & Metrics

### `GET /api/v1/metrics`
Returns current point-in-time throughput, active socket counts, and resource load.

#### Request
```bash
curl -X GET http://localhost:8000/api/v1/metrics
```

#### Response (`200 OK`)
```json
{
  "tps": 542.4,
  "active_connections": 36,
  "head_load_percentage": 48.2,
  "total_tx_processed": 184920
}
```

---

## WebSocket Interfaces

### 1. Telemetry Stream: `WS /api/v1/ws/metrics`
Broadcasts system performance frames every 1,000 milliseconds.

#### Connection Example (Node.js / Browser)
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/metrics');

ws.onopen = () => {
  console.log('Connected to HydraLite metrics stream');
};

ws.onmessage = (event) => {
  const metrics = JSON.parse(event.data);
  console.log(`Current TPS: ${metrics.tps} | Average Latency: ${metrics.latency_ms}ms`);
};

ws.onerror = (err) => {
  console.error('WebSocket connection error:', err);
};
```

#### Frame Schema
```json
{
  "timestamp": 1729036500,
  "tx_total": 184920,
  "tps": 542.4,
  "latency_ms": 14.8,
  "connected_clients": 36
}
```

---

### 2. Session Channel: `WS /api/v1/ws/gaming/{player_id}`
A persistent, duplex WebSocket channel for interactive applications (such as on-chain gaming turns, micropayment streams, or rapid auctions) requiring sub-10ms roundtrips.

#### Client Action Frame
```json
{
  "action": "execute_turn",
  "payload": {
    "coord_x": 12,
    "coord_y": 48,
    "session_nonce": 994
  }
}
```

#### Server Acknowledgment Frame
```json
{
  "status": "confirmed",
  "tx_id": "3d82a1e0440e7f19cb8d9e2a1bb5920d321588647acae34a36287c8d9e1f10c4",
  "latency_ms": 6.2
}
```

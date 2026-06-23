# API Reference

The HydraLite Engine provides a RESTful API and a persistent WebSocket connection designed for ultra-low latency microtransactions and Layer 2 state tracking.

## Base URL
All API requests should be prefixed with `/api/v1`.
If running locally, the default endpoint is `http://127.0.0.1:8000/api/v1`.

---

## REST Endpoints

### 1. Process Micropayment
Initiates a Layer-2 transaction based on the user's action and the configured `pricing.yaml` rules.

**Endpoint:** `POST /pay`  
**Headers:** `Content-Type: application/json`

**Request Body:**
```json
{
  "user_id": "string",
  "action": "string"
}
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "tx_id": "8a3f...",
  "latency_ms": 12.4,
  "amount_lovelace": 1000000
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Invalid action: unlock_premium"
}
```

### 2. Verify Transaction
Checks if a specific Transaction ID was successfully processed and confirmed inside the Hydra Head.

**Endpoint:** `GET /verify/{tx_id}`

**Success Response (200 OK):**
```json
{
  "status": "confirmed",
  "tx_id": "8a3f..."
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Transaction not found or unconfirmed"
}
```

### 3. Server Metrics
Returns real-time load and throughput metrics for the active Hydra Head.

**Endpoint:** `GET /metrics`

**Success Response (200 OK):**
```json
{
  "tps": 518.7,
  "active_connections": 50,
  "head_load_percentage": 42.5
}
```

---

## WebSocket Endpoints

HydraLite supports persistent WebSocket connections for real-time applications where standard HTTP handshakes would introduce too much latency.

### 1. Global Metrics Stream
Subscribes the client to a live feed of system metrics, updating every 1000ms.

**Endpoint:** `WS /ws/metrics`

**Stream Output:**
```json
{
  "tx_total": 14502,
  "tps": 45.2,
  "latency_ms": 11.8
}
```

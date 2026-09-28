import time
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set

router = APIRouter()
logger = logging.getLogger("gaming_ws")
logger.setLevel(logging.INFO)

# In-memory session state manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.player_states: Dict[str, dict] = {}
        self.metrics = {"messages_processed": 0, "total_latency_ms": 0.0}

    async def connect(self, player_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        self.player_states[player_id] = {"balance": 1000, "position": [0,0]} # Mock state
        logger.info(f"Player {player_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
        if player_id in self.player_states:
            del self.player_states[player_id]
        logger.info(f"Player {player_id} disconnected.")

    async def broadcast_state(self, exclude: str = None):
        # In a real game, only broadcast to players in same instance/room
        state_dump = json.dumps({"type": "state_sync", "players": self.player_states})
        for pid, ws in list(self.active_connections.items()):
            if pid != exclude:
                try:
                    await ws.send_text(state_dump)
                except Exception:
                    pass

    async def process_message(self, player_id: str, message: str) -> dict:
        start_time = time.time()
        try:
            data = json.loads(message)
            action = data.get("action")
            
            # Simple game loop action
            if action == "move":
                pos = data.get("position", [0, 0])
                self.player_states[player_id]["position"] = pos
            elif action == "micro_action":
                # Simulated microtransaction execution linked to game action (e.g. buying ammo)
                cost = data.get("cost", 10)
                if self.player_states[player_id]["balance"] >= cost:
                    self.player_states[player_id]["balance"] -= cost
                
            response = {"status": "ok", "ack_action": action, "balance": self.player_states[player_id]["balance"]}
        except Exception as e:
            response = {"status": "error", "error": str(e)}
            
        latency_ms = (time.time() - start_time) * 1000
        self.metrics["messages_processed"] += 1
        self.metrics["total_latency_ms"] += latency_ms
        
        return response

manager = ConnectionManager()

@router.websocket("/ws/gaming/{player_id}")
async def gaming_endpoint(websocket: WebSocket, player_id: str):
    await manager.connect(player_id, websocket)
    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            # Process and calculate turnaround time
            response = await manager.process_message(player_id, data)
            # Send ACK back
            await websocket.send_json(response)
            
            # Optionally broadcast new state to all (rate limited in real life)
            # await manager.broadcast_state(exclude=player_id)
            
    except WebSocketDisconnect:
        manager.disconnect(player_id)

import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.routes.payments import engine
from api.routes.gaming import manager

router = APIRouter()

@router.websocket("/ws/metrics")
async def metrics_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    last_tx_count = engine.metrics["tx_count"]
    last_msg_count = manager.metrics["messages_processed"]
    last_time = time.time()
    
    try:
        while True:
            await asyncio.sleep(1.0)
            
            now = time.time()
            dt = now - last_time
            if dt <= 0:
                continue
                
            current_tx = engine.metrics["tx_count"]
            current_msg = manager.metrics["messages_processed"]
            
            tx_diff = current_tx - last_tx_count
            msg_diff = current_msg - last_msg_count
            
            total_tps = (tx_diff + msg_diff) / dt
            
            # Simple average latency calculation across all recorded events so far
            total_events = current_tx + current_msg
            avg_latency = 0
            if total_events > 0:
                avg_latency = (engine.metrics["total_latency_ms"] + manager.metrics["total_latency_ms"]) / total_events
                
            payload = {
                "timestamp": now,
                "tps": total_tps,
                "latency_ms": avg_latency,
                "tx_total": current_tx,
                "gaming_total": current_msg
            }
            
            await websocket.send_json(payload)
            
            last_tx_count = current_tx
            last_msg_count = current_msg
            last_time = now
            
    except WebSocketDisconnect:
        pass

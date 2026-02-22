import asyncio
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from api.engine import PaymentEngine

router = APIRouter()
engine = PaymentEngine()

class PaymentRequest(BaseModel):
    user_id: str
    action: str
    
class PaymentResponse(BaseModel):
    status: str
    tx_id: str
    latency_ms: float
    amount_lovelace: int

@router.post("/pay", response_model=PaymentResponse)
async def process_payment(request: Request, payload: PaymentRequest):
    start_time = time.time()
    pricing = request.app.state.pricing
    
    # Determine amount based on action
    amount = pricing["tiers"].get(payload.action)
    if not amount:
        raise HTTPException(status_code=400, detail=f"Invalid action: {payload.action}")
        
    # Process payment via Engine (Hydra)
    try:
        tx_id = await engine.process_microtransaction(payload.user_id, amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    latency_ms = (time.time() - start_time) * 1000
    return PaymentResponse(
        status="success",
        tx_id=tx_id,
        latency_ms=latency_ms,
        amount_lovelace=amount
    )

@router.get("/verify/{tx_id}")
async def verify_payment(tx_id: str):
    is_valid = await engine.verify_transaction(tx_id)
    if is_valid:
        return {"status": "confirmed", "tx_id": tx_id}
    raise HTTPException(status_code=404, detail="Transaction not found or unconfirmed")

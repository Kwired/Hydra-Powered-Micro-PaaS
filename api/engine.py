import asyncio
import uuid
import random

class PaymentEngine:
    """
    Manages microtransactions via the Hydra Head.
    For Phase 1 high-speed load testing (1,000 txs/sec), we use a simulated
    delay representing the L2 confirmation time (typically 50-150ms).
    """
    def __init__(self):
        self.tx_store = set()
        self.metrics = {"tx_count": 0, "total_latency_ms": 0.0}
        
    async def process_microtransaction(self, user_id: str, amount_lovelace: int) -> str:
        # Simulate network and L2 processing delay (Hydra TPS allows extremely low latency)
        # Average latency is expected to be well under 1 second.
        delay = random.uniform(0.05, 0.15)
        await asyncio.sleep(delay)
        tx_id = f"tx_hydra_{uuid.uuid4().hex[:12]}"
        self.tx_store.add(tx_id)
        self.metrics["tx_count"] += 1
        self.metrics["total_latency_ms"] += (delay * 1000)
        return tx_id
        
    async def verify_transaction(self, tx_id: str) -> bool:
        return tx_id in self.tx_store

import asyncio
import time
import httpx
import argparse

async def submit_payment(client, action="unlock_post"):
    payload = {"user_id": "user_123", "action": action}
    start = time.time()
    try:
        response = await client.post("http://127.0.0.1:8000/api/v1/pay", json=payload)
        latency = time.time() - start
        return response.status_code == 200, latency
    except Exception:
        return False, time.time() - start

async def run_load_test(total_txs=1000, concurrency=50):
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Starting load test: {total_txs} microtransactions at concurrency {concurrency}...")
        start_time = time.time()
        
        sem = asyncio.Semaphore(concurrency)
        
        async def bounded_submit():
            async with sem:
                return await submit_payment(client)
                
        tasks = [bounded_submit() for _ in range(total_txs)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        success_count = sum(1 for r, _ in results if r)
        latencies = [l for r, l in results if r]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        total_time = end_time - start_time
        tps = total_txs / total_time
        
        print("\n=== LOAD TEST RESULTS ===")
        print(f"Total Transactions: {total_txs}")
        print(f"Successful:         {success_count}")
        print(f"Total Time:         {total_time:.2f}s")
        print(f"Throughput:         {tps:.2f} TPS")
        print(f"Avg Latency:        {avg_latency*1000:.2f} ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test API load")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=100)
    args = parser.parse_args()
    
    asyncio.run(run_load_test(args.count, args.concurrency))

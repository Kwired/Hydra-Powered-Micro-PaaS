import yaml
from fastapi import FastAPI
from api.routes import payments, gaming, metrics

app = FastAPI(title="Hydra Micro-PaaS API", version="0.2.0")

# Load configuration
with open("api/pricing.yaml", "r") as f:
    app.state.pricing = yaml.safe_load(f)

app.include_router(payments.router, prefix="/api/v1")
app.include_router(gaming.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hydra-micro-paas"}

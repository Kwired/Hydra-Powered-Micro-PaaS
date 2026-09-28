import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import payments, metrics, gaming

import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="HydraLite Ecosystem API", version="0.9.0")

# SECURITY AUDIT FIX: Locked down CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load configuration
with open("api/pricing.yaml", "r") as f:
    app.state.pricing = yaml.safe_load(f)

app.include_router(payments.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(gaming.router, prefix="/api/v1")
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hydra-micro-paas"}

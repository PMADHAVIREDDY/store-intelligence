import json
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import init_db, load_pos_transactions
from app.ingestion import router as ingestion_router
from app.metrics import heatmap_router, metrics_router
from app.funnel import funnel_router
from app.anomalies import router as anomalies_router
from app.health import health_router
from app.models import *

DATA_DIR = Path("data")
POS_CSV_PATH = Path("dataset") / "Brigade_Bangalore_10_April_26 (1)bc6219c.csv"

app = FastAPI()


@app.on_event("startup")
async def startup_event() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    await load_pos_transactions(str(POS_CSV_PATH))


@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid4())
    start_time = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status_code = response.status_code if response is not None else 500
        print(json.dumps({
            "trace_id": trace_id,
            "endpoint": request.url.path,
            "method": request.method,
            "latency_ms": latency_ms,
            "status_code": status_code,
        }))


@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )


app.include_router(ingestion_router)
app.include_router(metrics_router)
app.include_router(heatmap_router)
app.include_router(funnel_router)
app.include_router(anomalies_router)
app.include_router(health_router)

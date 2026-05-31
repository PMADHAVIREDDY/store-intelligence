from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter

from app.database import get_db
from app.models import HealthResponse

health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse)
async def get_health():
    status = "ok"
    last_event_per_store: Dict[str, str] = {}
    stale_feeds: List[str] = []

    try:
        async with get_db() as db:
            cursor = await db.execute("SELECT 1 FROM events LIMIT 1")
            await cursor.fetchone()

            cursor = await db.execute(
                """
                SELECT store_id, MAX(timestamp) AS last_ts
                FROM events
                GROUP BY store_id
                """
            )
            store_rows = await cursor.fetchall()
            if store_rows:
                for row in store_rows:
                    store_id = row["store_id"]
                    last_ts_str = row["last_ts"]
                    last_event_per_store[store_id] = last_ts_str

                    try:
                        last_ts = datetime.fromisoformat(last_ts_str)
                        if last_ts < datetime.utcnow() - timedelta(minutes=10):
                            stale_feeds.append(store_id)
                    except (ValueError, TypeError):
                        pass
    except Exception:
        status = "degraded"

    return HealthResponse(
        status=status,
        last_event_per_store=last_event_per_store,
        stale_feeds=stale_feeds,
    )

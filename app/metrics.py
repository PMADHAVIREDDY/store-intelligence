from typing import List
from fastapi import APIRouter
from app.database import get_db
from app.models import HeatmapResponse, HeatmapZone, StoreMetrics, ZoneMetrics

metrics_router = APIRouter(prefix="/stores")
heatmap_router = APIRouter(prefix="/stores")


@metrics_router.get("/{store_id}/metrics", response_model=StoreMetrics)
async def get_store_metrics(store_id: str):
    async with get_db() as db:

        # Unique visitors
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id=? AND UPPER(event_type)='ENTRY' AND is_staff=0",
            (store_id,)
        )
        row = await cursor.fetchone()
        unique_visitors = int(row[0]) if row and row[0] else 0

        # Conversion rate
        cursor = await db.execute(
            "SELECT CAST(SUM(is_converted) AS FLOAT), COUNT(*) FROM sessions WHERE store_id=?",
            (store_id,)
        )
        row = await cursor.fetchone()
        if row and row[1] and row[1] > 0:
            conversion_rate = float(row[0] or 0) / float(row[1])
        else:
            conversion_rate = 0.0

        # Zone dwell
        cursor = await db.execute(
            """SELECT zone_id, AVG(dwell_ms), COUNT(*) 
               FROM events 
               WHERE store_id=? AND zone_id IS NOT NULL AND is_staff=0
               GROUP BY zone_id""",
            (store_id,)
        )
        zone_rows = await cursor.fetchall()
        avg_dwell_per_zone = []
        for r in zone_rows:
            avg_dwell_per_zone.append(ZoneMetrics(
                zone_id=str(r[0]),
                avg_dwell_ms=float(r[1] or 0.0),
                visit_count=int(r[2] or 0)
            ))

        # Queue depth
        cursor = await db.execute(
            """SELECT queue_depth FROM events 
               WHERE store_id=? AND queue_depth IS NOT NULL 
               ORDER BY timestamp DESC LIMIT 1""",
            (store_id,)
        )
        row = await cursor.fetchone()
        queue_depth = int(row[0]) if row and row[0] else 0

        # Abandonment rate
        cursor = await db.execute(
            """SELECT 
               SUM(CASE WHEN UPPER(event_type) IN ('BILLING_QUEUE_ABANDON','QUEUE_ABANDONED') THEN 1 ELSE 0 END),
               SUM(CASE WHEN UPPER(event_type) IN ('BILLING_QUEUE_JOIN','QUEUE_JOIN') THEN 1 ELSE 0 END)
               FROM events WHERE store_id=?""",
            (store_id,)
        )
        row = await cursor.fetchone()
        if row and row[1] and row[1] > 0:
            abandonment_rate = float(row[0] or 0) / float(row[1])
        else:
            abandonment_rate = 0.0

    return StoreMetrics(
        store_id=store_id,
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        avg_dwell_per_zone=avg_dwell_per_zone,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate
    )


@heatmap_router.get("/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_store_heatmap(store_id: str):
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT zone_id, COUNT(*), AVG(dwell_ms)
               FROM events
               WHERE store_id=? AND zone_id IS NOT NULL
               GROUP BY zone_id""",
            (store_id,)
        )
        zone_rows = await cursor.fetchall()

        cursor = await db.execute(
            "SELECT COUNT(*) FROM sessions WHERE store_id=?",
            (store_id,)
        )
        row = await cursor.fetchone()
        session_count = int(row[0]) if row and row[0] else 0

        if not zone_rows:
            return HeatmapResponse(store_id=store_id, zones=[])

        max_count = max(int(r[1] or 0) for r in zone_rows) or 1

        zones = []
        for r in zone_rows:
            count = int(r[1] or 0)
            zones.append(HeatmapZone(
                zone_id=str(r[0]),
                frequency=round((count / max_count) * 100, 2),
                avg_dwell_ms=float(r[2] or 0.0),
                data_confidence=session_count >= 20
            ))

    return HeatmapResponse(store_id=store_id, zones=zones)
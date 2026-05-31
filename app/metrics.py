from typing import List

from fastapi import APIRouter

from app.database import get_db
from app.models import HeatmapResponse, HeatmapZone, StoreMetrics, ZoneMetrics

metrics_router = APIRouter(prefix="/stores")
heatmap_router = APIRouter(prefix="/stores")


@metrics_router.get("/{store_id}/metrics", response_model=StoreMetrics)
async def get_store_metrics(store_id: str):
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) AS unique_visitors
            FROM events
            WHERE store_id = ?
              AND event_type = 'ENTRY'
              AND is_staff = 0
              AND date(timestamp) >= date('2026-04-10')
            """,
            (store_id,),
        )
        unique_row = await cursor.fetchone()
        unique_visitors = unique_row["unique_visitors"] if unique_row else 0

        cursor = await db.execute(
            """
            SELECT
                CAST(SUM(is_converted) AS FLOAT) / NULLIF(COUNT(*), 0) AS conversion_rate
            FROM sessions
            WHERE store_id = ?
            """,
            (store_id,),
        )
        conversion_row = await cursor.fetchone()
        conversion_rate = conversion_row["conversion_rate"] if conversion_row else None
        conversion_rate = float(conversion_rate) if conversion_rate is not None else 0.0

        cursor = await db.execute(
            """
            SELECT zone_id,
                   AVG(dwell_ms) AS avg_dwell_ms,
                   COUNT(*) AS visit_count
            FROM events
            WHERE store_id = ?
              AND zone_id IS NOT NULL
            GROUP BY zone_id
            """,
            (store_id,),
        )
        zone_rows = await cursor.fetchall()
        avg_dwell_per_zone: List[ZoneMetrics] = []
        for row in zone_rows:
            avg_dwell_per_zone.append(
                ZoneMetrics(
                    zone_id=row["zone_id"],
                    avg_dwell_ms=float(row["avg_dwell_ms"] or 0.0),
                    visit_count=int(row["visit_count"] or 0),
                )
            )

        cursor = await db.execute(
            """
            SELECT queue_depth
            FROM events
            WHERE store_id = ?
              AND queue_depth IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (store_id,),
        )
        queue_row = await cursor.fetchone()
        queue_depth = int(queue_row["queue_depth"]) if queue_row and queue_row["queue_depth"] is not None else 0

        cursor = await db.execute(
            """
            SELECT
                CAST(SUM(CASE WHEN event_type = 'BILLING_QUEUE_ABANDON' THEN 1 ELSE 0 END) AS FLOAT) /
                NULLIF(SUM(CASE WHEN event_type = 'BILLING_QUEUE_JOIN' THEN 1 ELSE 0 END), 0) AS abandonment_rate
            FROM events
            WHERE store_id = ?
            """,
            (store_id,),
        )
        abandonment_row = await cursor.fetchone()
        abandonment_rate = abandonment_row["abandonment_rate"] if abandonment_row else None
        abandonment_rate = float(abandonment_rate) if abandonment_rate is not None else 0.0

    return StoreMetrics(
        store_id=store_id,
        unique_visitors=int(unique_visitors or 0),
        conversion_rate=conversion_rate,
        avg_dwell_per_zone=avg_dwell_per_zone,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate,
    )


@heatmap_router.get("/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_store_heatmap(store_id: str):
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT zone_id,
                   COUNT(*) AS event_count,
                   AVG(dwell_ms) AS avg_dwell_ms
            FROM events
            WHERE store_id = ?
              AND zone_id IS NOT NULL
            GROUP BY zone_id
            """,
            (store_id,),
        )
        zone_rows = await cursor.fetchall()

        cursor = await db.execute(
            """
            SELECT COUNT(*) AS total_count
            FROM events
            WHERE store_id = ?
              AND zone_id IS NOT NULL
            """,
            (store_id,),
        )
        total_events_row = await cursor.fetchone()
        total_count = int(total_events_row["total_count"] or 0) if total_events_row else 0

        zones: List[HeatmapZone] = []
        for row in zone_rows:
            event_count = int(row["event_count"] or 0)
            frequency = float(event_count) / total_count if total_count > 0 else 0.0
            zones.append(
                HeatmapZone(
                    zone_id=row["zone_id"],
                    frequency=frequency,
                    avg_dwell_ms=float(row["avg_dwell_ms"] or 0.0),
                    data_confidence=event_count >= 5,
                )
            )

    return HeatmapResponse(store_id=store_id, zones=zones)

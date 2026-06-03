from fastapi import APIRouter
from app.database import get_db
from app.models import FunnelResponse, FunnelStage

funnel_router = APIRouter()


@funnel_router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def get_funnel(store_id: str):
    async with get_db() as db:

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id=? AND UPPER(event_type)='ENTRY' AND is_staff=0",
            (store_id,)
        )
        row = await cursor.fetchone()
        stage1 = row[0] if row and row[0] else 0

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id=? AND UPPER(event_type) IN ('ZONE_ENTER','ZONE_ENTERED') AND is_staff=0",
            (store_id,)
        )
        row = await cursor.fetchone()
        stage2 = row[0] if row and row[0] else 0

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id=? AND UPPER(event_type) IN ('BILLING_QUEUE_JOIN','QUEUE_JOIN') AND is_staff=0",
            (store_id,)
        )
        row = await cursor.fetchone()
        stage3 = row[0] if row and row[0] else 0

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT visitor_id) FROM sessions WHERE store_id=? AND is_converted=1",
            (store_id,)
        )
        row = await cursor.fetchone()
        stage4 = row[0] if row and row[0] else 0

        def calc_dropoff(prev, curr):
            if prev == 0:
                return 0.0
            result = ((prev - curr) / prev) * 100
            return round(max(0.0, result), 2)

        stages = [
            FunnelStage(stage="ENTRY", count=stage1, dropoff_pct=0.0),
            FunnelStage(stage="ZONE_VISIT", count=stage2, dropoff_pct=calc_dropoff(stage1, stage2)),
            FunnelStage(stage="BILLING_QUEUE", count=stage3, dropoff_pct=calc_dropoff(stage2, stage3)),
            FunnelStage(stage="PURCHASE", count=stage4, dropoff_pct=calc_dropoff(stage3, stage4)),
        ]

        return FunnelResponse(store_id=store_id, stages=stages)
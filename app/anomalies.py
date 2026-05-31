from datetime import datetime
from typing import List

from fastapi import APIRouter

from app.database import get_db
from app.models import Anomaly, AnomalyResponse

router = APIRouter(prefix="/stores")


@router.get("/{store_id}/anomalies", response_model=AnomalyResponse)
async def get_store_anomalies(store_id: str):
    anomalies: List[Anomaly] = []
    now = datetime.utcnow()

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT MAX(queue_depth) AS max_queue
            FROM events
            WHERE store_id = ?
              AND event_type = 'BILLING_QUEUE_JOIN'
              AND timestamp >= datetime('now', '-5 minutes')
              AND queue_depth IS NOT NULL
            """,
            (store_id,),
        )
        max_queue_row = await cursor.fetchone()
        max_queue = int(max_queue_row["max_queue"]) if max_queue_row and max_queue_row["max_queue"] is not None else 0
        if max_queue > 10:
            anomalies.append(
                Anomaly(
                    anomaly_type="BILLING_QUEUE_SPIKE",
                    severity="CRITICAL",
                    description=f"Billing queue depth spiked to {max_queue} in the last 5 minutes.",
                    suggested_action="Deploy additional billing staff immediately - queue critical",
                    detected_at=now,
                )
            )
        elif max_queue > 5:
            anomalies.append(
                Anomaly(
                    anomaly_type="BILLING_QUEUE_SPIKE",
                    severity="WARN",
                    description=f"Billing queue depth reached {max_queue} in the last 5 minutes.",
                    suggested_action="Consider opening additional billing counter",
                    detected_at=now,
                )
            )

        cursor = await db.execute(
            """
            SELECT CAST(SUM(is_converted) AS FLOAT) / NULLIF(COUNT(*), 0) AS conversion_rate
            FROM sessions
            WHERE store_id = ?
              AND date(entry_time) = date('now')
            """,
            (store_id,),
        )
        conversion_row = await cursor.fetchone()
        today_rate = float(conversion_row["conversion_rate"]) if conversion_row and conversion_row["conversion_rate"] is not None else 0.0

        cursor = await db.execute(
            """
            SELECT CAST(SUM(is_converted) AS FLOAT) / NULLIF(COUNT(*), 0) AS conversion_rate
            FROM sessions
            WHERE store_id = ?
              AND date(entry_time) >= date('now', '-7 days')
              AND date(entry_time) < date('now')
            """,
            (store_id,),
        )
        avg_7day_row = await cursor.fetchone()
        avg_7day = float(avg_7day_row["conversion_rate"]) if avg_7day_row and avg_7day_row["conversion_rate"] is not None else None

        if avg_7day is not None and avg_7day > 0:
            if today_rate < avg_7day - 0.10:
                anomalies.append(
                    Anomaly(
                        anomaly_type="CONVERSION_DROP",
                        severity="CRITICAL",
                        description=(
                            f"Today's conversion rate {today_rate:.2f} is significantly below the 7-day average "
                            f"of {avg_7day:.2f}."
                        ),
                        suggested_action="Investigate checkout and billing flow to restore conversion performance.",
                        detected_at=now,
                    )
                )
            elif today_rate < avg_7day - 0.05:
                anomalies.append(
                    Anomaly(
                        anomaly_type="CONVERSION_DROP",
                        severity="WARN",
                        description=(
                            f"Today's conversion rate {today_rate:.2f} is below the 7-day average "
                            f"of {avg_7day:.2f}."
                        ),
                        suggested_action="Monitor checkout conversion and improve customer flow toward purchase.",
                        detected_at=now,
                    )
                )

        cursor = await db.execute(
            """
            SELECT
                CAST(SUM(CASE WHEN event_type = 'BILLING_QUEUE_ABANDON' THEN 1 ELSE 0 END) AS FLOAT) /
                NULLIF(SUM(CASE WHEN event_type = 'BILLING_QUEUE_JOIN' THEN 1 ELSE 0 END), 0) AS abandonment_rate
            FROM events
            WHERE store_id = ?
              AND date(timestamp) = date('now')
            """,
            (store_id,),
        )
        abandonment_row = await cursor.fetchone()
        abandonment_rate = float(abandonment_row["abandonment_rate"]) if abandonment_row and abandonment_row["abandonment_rate"] is not None else 0.0
        if abandonment_rate > 0.5:
            anomalies.append(
                Anomaly(
                    anomaly_type="QUEUE_ABANDONMENT_SPIKE",
                    severity="CRITICAL",
                    description=(
                        f"Billing queue abandonment rate is {abandonment_rate:.2f} today, indicating large checkout leakage."
                    ),
                    suggested_action="Review queue handling and customer assistance at billing to reduce abandonments.",
                    detected_at=now,
                )
            )
        elif abandonment_rate > 0.25:
            anomalies.append(
                Anomaly(
                    anomaly_type="QUEUE_ABANDONMENT_SPIKE",
                    severity="WARN",
                    description=(
                        f"Billing queue abandonment rate is {abandonment_rate:.2f} today, which is elevated."
                    ),
                    suggested_action="Consider improving queue signage and staffing to reduce abandonment.",
                    detected_at=now,
                )
            )

    return AnomalyResponse(store_id=store_id, anomalies=anomalies)

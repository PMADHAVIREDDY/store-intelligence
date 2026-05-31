import json
from datetime import timedelta
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.database import get_db
from app.models import EventType, IngestRequest, IngestResponse, StoreEvent

router = APIRouter(prefix="/events")


def _validate_event(event_data: Any) -> StoreEvent:
    if not isinstance(event_data, dict):
        raise ValidationError(
            [
                {
                    "loc": ("event",),
                    "msg": "event must be an object",
                    "type": "type_error.dict",
                }
            ],
            StoreEvent,
        )
    return StoreEvent.model_validate(event_data)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict) or "events" not in payload or not isinstance(payload["events"], list):
        raise HTTPException(status_code=422, detail="Payload must contain an events list")

    raw_events = payload["events"]
    if len(raw_events) > 500:
        raise HTTPException(status_code=422, detail="Maximum of 500 events allowed")

    validated_events: List[StoreEvent] = []
    errors: List[Dict[str, Any]] = []

    for event_data in raw_events:
        try:
            event = _validate_event(event_data)
            validated_events.append(event)
        except ValidationError as exc:
            event_id = event_data.get("event_id") if isinstance(event_data, dict) else None
            errors.append(
                {
                    "event_id": event_id or "unknown",
                    "reason": "validation_failed: " + str(exc),
                }
            )

    accepted = 0
    rejected = len(errors)

    async with get_db() as db:
        await db.execute("BEGIN")
        for event in validated_events:
            try:
                cursor = await db.execute(
                    "SELECT 1 FROM events WHERE event_id = ?",
                    (event.event_id,),
                )
                existing = await cursor.fetchone()
                if existing:
                    continue

                await db.execute(
                    """
                    INSERT INTO events (
                        event_id,
                        store_id,
                        camera_id,
                        visitor_id,
                        event_type,
                        timestamp,
                        zone_id,
                        dwell_ms,
                        is_staff,
                        confidence,
                        queue_depth,
                        sku_zone,
                        session_seq,
                        raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.store_id,
                        event.camera_id,
                        event.visitor_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        event.zone_id,
                        event.dwell_ms,
                        int(event.is_staff),
                        event.confidence,
                        event.metadata.queue_depth,
                        event.metadata.sku_zone,
                        event.metadata.session_seq,
                        event.model_dump_json(),
                    ),
                )

                if event.event_type == EventType.ENTRY:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO sessions (
                            session_id,
                            store_id,
                            visitor_id,
                            entry_time,
                            is_converted,
                            reentry_count
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            event.store_id,
                            event.visitor_id,
                            event.timestamp.isoformat(),
                            0,
                            0,
                        ),
                    )
                elif event.event_type == EventType.EXIT:
                    await db.execute(
                        """
                        UPDATE sessions
                        SET exit_time = ?
                        WHERE visitor_id = ? AND exit_time IS NULL
                        """,
                        (event.timestamp.isoformat(), event.visitor_id),
                    )
                elif event.event_type == EventType.REENTRY:
                    await db.execute(
                        """
                        UPDATE sessions
                        SET reentry_count = reentry_count + 1
                        WHERE session_id = (
                            SELECT session_id
                            FROM sessions
                            WHERE visitor_id = ?
                            ORDER BY entry_time DESC
                            LIMIT 1
                        )
                        """,
                        (event.visitor_id,),
                    )
                elif event.event_type == EventType.BILLING_QUEUE_JOIN:
                    window_end = (event.timestamp + timedelta(minutes=5)).isoformat()
                    cursor = await db.execute(
                        """
                        SELECT 1
                        FROM pos_transactions
                        WHERE store_id = ?
                          AND timestamp >= ?
                          AND timestamp <= ?
                        LIMIT 1
                        """,
                        (event.store_id, event.timestamp.isoformat(), window_end),
                    )
                    conversion = await cursor.fetchone()
                    if conversion:
                        await db.execute(
                            """
                            UPDATE sessions
                            SET is_converted = 1
                            WHERE visitor_id = ?
                            """,
                            (event.visitor_id,),
                        )

                accepted += 1
            except Exception as exc:
                rejected += 1
                errors.append(
                    {"event_id": event.event_id, "reason": f"processing_failed: {exc}"}
                )
        await db.commit()

    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)

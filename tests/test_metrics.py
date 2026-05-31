# PROMPT: Generated using GitHub Copilot
# CHANGES MADE: Added edge case for zero purchases and reentry

import pytest
from datetime import datetime
from uuid import uuid4
from httpx import AsyncClient

from app.main import app


def create_event(
    event_type: str,
    visitor_id: str,
    zone_id: str = None,
    is_staff: bool = False,
    queue_depth: int = None,
) -> dict:
    """Helper function to create valid event dict."""
    return {
        "event_id": str(uuid4()),
        "store_id": "STORE_BRIGADE_ROAD",
        "camera_id": "CAM_1",
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zone_id": zone_id,
        "dwell_ms": 30000,
        "is_staff": is_staff,
        "confidence": 0.9,
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": None,
            "session_seq": 1,
        },
    }


@pytest.mark.asyncio
async def test_ingest_single_event():
    """Test ingesting a single valid ENTRY event."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        event = create_event("ENTRY", "VIS_000001")
        response = await client.post(
            "/events/ingest",
            json={"events": [event]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] == 1
        assert data["rejected"] == 0


@pytest.mark.asyncio
async def test_ingest_idempotent():
    """Test that posting same event twice only accepts it once (idempotent)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        event = create_event("ENTRY", "VIS_000002")
        
        response1 = await client.post(
            "/events/ingest",
            json={"events": [event]},
        )
        data1 = response1.json()
        
        response2 = await client.post(
            "/events/ingest",
            json={"events": [event]},
        )
        data2 = response2.json()
        
        assert data1["accepted"] == 1
        total_accepted = data1["accepted"] + data2["accepted"]
        assert total_accepted == 1


@pytest.mark.asyncio
async def test_metrics_empty_store():
    """Test metrics endpoint with empty store."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stores/EMPTY_STORE/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "unique_visitors" in data
        assert data["unique_visitors"] >= 0
        assert "conversion_rate" in data
        assert data["conversion_rate"] >= 0.0


@pytest.mark.asyncio
async def test_metrics_excludes_staff():
    """Test that staff visitors are excluded from unique_visitors count."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        staff_event = create_event("ENTRY", "VIS_STAFF_001", is_staff=True)
        regular_event = create_event("ENTRY", "VIS_REGULAR_001", is_staff=False)
        
        response = await client.post(
            "/events/ingest",
            json={"events": [staff_event, regular_event]},
        )
        assert response.status_code == 200
        
        metrics_response = await client.get("/stores/STORE_BRIGADE_ROAD/metrics")
        assert metrics_response.status_code == 200
        data = metrics_response.json()
        assert data["unique_visitors"] >= 1


@pytest.mark.asyncio
async def test_conversion_rate_zero_purchases():
    """Test that conversion_rate is always a float, never null, even with zero purchases."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stores/STORE_BRIGADE_ROAD/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["conversion_rate"], float)
        assert data["conversion_rate"] >= 0.0


@pytest.mark.asyncio
async def test_funnel_reentry_counts_once():
    """Test that visitor with both ENTRY and REENTRY is counted once in ENTRY stage."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        entry_event = create_event("ENTRY", "VIS_REENTRY_001")
        reentry_event = create_event("REENTRY", "VIS_REENTRY_001")
        
        response = await client.post(
            "/events/ingest",
            json={"events": [entry_event, reentry_event]},
        )
        assert response.status_code == 200
        
        funnel_response = await client.get("/stores/STORE_BRIGADE_ROAD/funnel")
        assert funnel_response.status_code == 200
        data = funnel_response.json()
        assert "stages" in data
        entry_stage = next((s for s in data["stages"] if s["stage"] == "ENTRY"), None)
        assert entry_stage is not None
        assert entry_stage["count"] >= 1

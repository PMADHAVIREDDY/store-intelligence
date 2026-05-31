import requests, uuid
from datetime import datetime, timedelta

base = datetime(2026, 4, 10, 10, 0, 0)
events = []

# Match visitor IDs from floor cameras
for i in range(1, 50):
    t = base + timedelta(minutes=i*2)
    events.append({
        "event_id": str(uuid.uuid4()),
        "store_id": "STORE_BRIGADE_ROAD",
        "camera_id": "CAM_1",
        "visitor_id": f"VIS_{i:06d}",
        "event_type": "ENTRY",
        "timestamp": t.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.88,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    })

resp = requests.post('http://localhost:8000/events/ingest', json={'events': events})
print(resp.json())

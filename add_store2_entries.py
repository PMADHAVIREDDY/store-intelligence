import requests, uuid
from datetime import datetime, timedelta

base = datetime(2026, 6, 1, 10, 0, 0)
events = []

for i in range(1, 20):
    t = base + timedelta(minutes=i*3)
    events.append({
        "event_id": str(uuid.uuid4()),
        "store_id": "STORE_2",
        "camera_id": "CAM_ENTRY_1",
        "visitor_id": f"VIS_S2_{i:04d}",
        "event_type": "entry",
        "timestamp": t.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.88,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    })

resp = requests.post('http://localhost:8000/events/ingest', json={'events': events})
print('Store 2 entries:', resp.json())

import requests
from datetime import datetime, timedelta
import uuid

base_time = datetime(2026, 4, 10, 10, 0, 0)
events = []

for i in range(1, 16):
    t = base_time + timedelta(minutes=i*3)
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
        "confidence": 0.85,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    })

resp = requests.post('http://localhost:8000/events/ingest', json={'events': events})
print('Result:', resp.json())

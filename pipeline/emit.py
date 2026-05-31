import uuid
import json
import os
from datetime import datetime
import numpy as np

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        return super().default(obj)

def emit_event(store_id, camera_id, visitor_id, event_type,
               timestamp, zone_id=None, dwell_ms=0, is_staff=False,
               confidence=0.9, queue_depth=None, sku_zone=None, session_seq=1):
    
    if isinstance(timestamp, datetime):
        timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": str(store_id),
        "camera_id": str(camera_id),
        "visitor_id": str(visitor_id),
        "event_type": str(event_type),
        "timestamp": str(timestamp),
        "zone_id": zone_id,
        "dwell_ms": int(dwell_ms),
        "is_staff": bool(is_staff),
        "confidence": round(float(confidence), 4),
        "metadata": {
            "queue_depth": int(queue_depth) if queue_depth is not None else None,
            "sku_zone": sku_zone,
            "session_seq": int(session_seq)
        }
    }

def append_event(event_dict, output_path):
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'a') as f:
        f.write(json.dumps(event_dict, cls=SafeEncoder) + '\n')
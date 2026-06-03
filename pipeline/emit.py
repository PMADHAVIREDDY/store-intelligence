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
            return obj.strftime('%Y-%m-%dT%H:%M:%S.%f')
        return super().default(obj)


def emit_event(store_id, camera_id, visitor_id, event_type,
               timestamp, zone_id=None, dwell_ms=0, is_staff=False,
               confidence=0.9, queue_depth=None, sku_zone=None,
               session_seq=1, zone_name=None, group_id=None,
               group_size=None):

    if isinstance(timestamp, datetime):
        timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')

    # Map event types to match sample_events format
    event_type_map = {
        'ENTRY': 'entry',
        'EXIT': 'exit',
        'ZONE_ENTER': 'zone_entered',
        'ZONE_EXIT': 'zone_exited',
        'ZONE_DWELL': 'zone_dwell',
        'BILLING_QUEUE_JOIN': 'queue_join',
        'BILLING_QUEUE_ABANDON': 'queue_abandoned',
        'REENTRY': 'reentry'
    }

    normalized_type = event_type_map.get(
        event_type.upper(), event_type.lower()
    )

    return {
        "event_id": str(uuid.uuid4()),
        "event_type": normalized_type,
        "id_token": visitor_id,
        "store_id": store_id,
        "store_code": store_id,
        "camera_id": camera_id,
        "event_timestamp": str(timestamp),
        "zone_id": zone_id,
        "zone_name": zone_name or zone_id,
        "dwell_ms": int(dwell_ms),
        "is_staff": bool(is_staff),
        "confidence": round(float(confidence), 4),
        "group_id": group_id,
        "group_size": group_size,
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
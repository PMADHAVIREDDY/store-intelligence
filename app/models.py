from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    ZONE_ENTERED = "zone_entered"
    ZONE_EXITED = "zone_exited"
    ZONE_DWELL = "zone_dwell"
    QUEUE_JOIN = "queue_join"
    QUEUE_ABANDONED = "queue_abandoned"
    REENTRY = "reentry"
     # Keep old names as aliases
    BILLING_QUEUE_JOIN = "queue_join"
    BILLING_QUEUE_ABANDON = "queue_abandoned"
    ZONE_ENTER = "zone_entered"
    ZONE_EXIT = "zone_exited"


class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int = 1


class StoreEvent(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: EventType
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float
    id_token: Optional[str] = None
    store_code: Optional[str] = None
    event_timestamp: Optional[str] = None
    zone_name: Optional[str] = None
    group_id: Optional[str] = None
    group_size: Optional[int] = None
    metadata: EventMetadata


class IngestRequest(BaseModel):
    events: Annotated[List[StoreEvent], Field(max_length=500)]


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: List[Dict]


class ZoneMetrics(BaseModel):
    zone_id: str
    avg_dwell_ms: float
    visit_count: int


class StoreMetrics(BaseModel):
    store_id: str
    unique_visitors: int
    conversion_rate: float
    avg_dwell_per_zone: List[ZoneMetrics]
    queue_depth: int
    abandonment_rate: float


class FunnelStage(BaseModel):
    stage: str
    count: int
    dropoff_pct: float


class FunnelResponse(BaseModel):
    store_id: str
    stages: List[FunnelStage]


class HeatmapZone(BaseModel):
    zone_id: str
    frequency: float
    avg_dwell_ms: float
    data_confidence: bool


class HeatmapResponse(BaseModel):
    store_id: str
    zones: List[HeatmapZone]


class Anomaly(BaseModel):
    anomaly_type: str
    severity: str
    description: str
    suggested_action: str
    detected_at: datetime


class AnomalyResponse(BaseModel):
    store_id: str
    anomalies: List[Anomaly]


class HealthResponse(BaseModel):
    status: str
    last_event_per_store: Dict
    stale_feeds: List[str]

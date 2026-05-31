from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


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

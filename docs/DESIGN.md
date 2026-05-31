# Store Intelligence System — Design Document

## Architecture Overview

This system processes raw CCTV footage from Brigade Road Purplle store 
and converts it into real-time retail analytics via a REST API.

The pipeline has 4 stages:
### Stage 1: Detection Pipeline (pipeline/)
- YOLOv8n model detects persons (class 0) in each video frame
- ByteTrack tracker assigns persistent track IDs across frames
- Entry/exit determined by centroid crossing a horizontal threshold line
- Zone assignment based on camera type and x-position of centroid
- Staff detection via HSV blue color ratio in bounding box crop
- Re-entry detected by checking if track_id exited within 30 minutes
- Events emitted as structured JSONL using emit.py

### Stage 2: Event Schema
Each event follows a strict schema with:
- event_id: UUID v4 (globally unique)
- visitor_id: VIS_{track_id:06d} (per-session token)
- event_type: ENTRY/EXIT/ZONE_ENTER/ZONE_EXIT/ZONE_DWELL/BILLING_QUEUE_JOIN/BILLING_QUEUE_ABANDON/REENTRY
- is_staff: boolean from HSV uniform detection
- confidence: YOLO detection confidence score

### Stage 3: Intelligence API (app/)
- FastAPI with async SQLite via aiosqlite
- POST /events/ingest: idempotent batch ingest by event_id
- GET /stores/{id}/metrics: real-time visitor and conversion metrics
- GET /stores/{id}/funnel: session-based conversion funnel
- GET /stores/{id}/heatmap: zone frequency normalised 0-100
- GET /stores/{id}/anomalies: queue spike, conversion drop, dead zone
- GET /health: service status and stale feed detection

### Stage 4: Storage
- SQLite chosen for simplicity and zero-dependency deployment
- Three tables: events, sessions, pos_transactions
- Indexes on store_id+timestamp and visitor_id for query performance

## Edge Case Handling

| Edge Case | Approach |
|-----------|----------|
| Group entry | ByteTrack assigns separate track IDs per person |
| Staff movement | HSV blue ratio > 60% threshold flags staff |
| Re-entry | exited_visitors dict tracks recent exits per track_id |
| Partial occlusion | YOLO confidence reported, not suppressed |
| Empty store | All endpoints return zeros not null |
| Camera overlap | visitor_id is camera-scoped, dedup by event_id |

## AI-Assisted Decisions

### 1. ByteTrack over DeepSORT
Claude suggested ByteTrack as it requires no separate Re-ID model 
and handles occlusion better in retail environments. I agreed after 
reading the ByteTrack paper — it uses IoU matching which works well 
for fixed camera angles.

### 2. SQLite over PostgreSQL
Claude initially suggested PostgreSQL for production scalability. 
I overrode this decision and chose SQLite because the challenge 
runs on a single machine and SQLite eliminates a dependency. 
For 40 stores in production I would revisit this.

### 3. HSV Staff Detection
Claude suggested using a VLM (GPT-4V) for staff detection. I 
chose rule-based HSV color matching instead because it runs 
locally without API costs and latency. The trade-off is it 
only works for stores with distinct uniform colors.
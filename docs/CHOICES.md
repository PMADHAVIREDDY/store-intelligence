# Engineering Choices

## Decision 1: Detection Model — YOLOv8n

### Options Considered
- YOLOv8n (nano) — fast, good accuracy, runs on CPU
- YOLOv8s (small) — better accuracy, slower
- RT-DETR — transformer-based, requires GPU
- MediaPipe — lightweight but less accurate for crowds

### What AI Suggested
Claude suggested starting with YOLOv8n for CPU environments and 
upgrading to YOLOv8s if accuracy was insufficient. It also 
suggested RT-DETR for GPU environments.

### What I Chose and Why
YOLOv8n with ByteTrack. Reasons:
1. Runs on CPU without GPU requirement
2. Processes frames at ~110ms per frame — acceptable for 15fps video
3. ultralytics library includes ByteTrack built-in — no extra dependency
4. Detection accuracy sufficient for retail (persons are large objects)

Trade-off: misses some partial occlusions but confidence score 
is always reported so downstream can filter if needed.

## Decision 2: Event Schema Design

### Options Considered
- Flat schema — all fields at top level
- Nested schema — metadata object for optional fields
- Separate tables per event type

### What AI Suggested
Claude suggested the nested metadata object for optional fields 
like queue_depth and sku_zone, arguing it keeps the core schema 
clean while allowing extensibility.

### What I Chose and Why
Adopted the nested metadata approach exactly. Reasoning:
1. Core fields (event_id, visitor_id, timestamp) always present
2. Optional fields in metadata avoid null columns at top level
3. raw_json column in DB stores full event for audit/replay
4. Schema matches the challenge specification exactly

The session_seq field in metadata tracks event order within 
a visitor session — useful for funnel reconstruction.

## Decision 3: API Architecture — Sync SQLite vs Async

### Options Considered
- Synchronous SQLite with sqlite3
- Async SQLite with aiosqlite
- PostgreSQL with asyncpg
- In-memory store with Redis

### What AI Suggested
Claude suggested aiosqlite for async SQLite access, noting that 
synchronous SQLite would block the FastAPI event loop under 
concurrent requests.

### What I Chose and Why
aiosqlite with FastAPI async endpoints. Reasons:
1. Non-blocking — FastAPI can handle concurrent requests
2. SQLite file persists across restarts — no data loss
3. Zero external dependencies — docker compose up just works
4. Single-node deployment matches challenge requirements

Trade-off: SQLite has write lock contention under high concurrency.
At 40 live stores sending events simultaneously this would require 
migration to PostgreSQL with connection pooling.
# Store Intelligence API

Real-time retail analytics from CCTV footage for Brigade Road Purplle store.

## Setup in 5 Commands

```bash
git clone <your-repo-url>
cd store-intelligence
docker compose up --build
# In a new terminal:
python pipeline/run.sh
curl http://localhost:8000/health
```

## Manual Setup (without Docker)

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Run Detection Pipeline

```bash
# Set Python path
export PYTHONPATH=.   # Linux/Mac
$env:PYTHONPATH = "." # Windows PowerShell

# Process entry camera
python pipeline/detect.py \
  --video "dataset/CAM 1.mp4" \
  --store-id STORE_BRIGADE_ROAD \
  --camera-id CAM_1 \
  --camera-type entry \
  --output events/cam1_events.jsonl \
  --clip-start-time "2026-04-10T10:00:00Z"

# Process floor cameras (CAM 2, CAM 3)
# Process billing cameras (CAM 4, CAM 5)
# See pipeline/run.sh for full script
```

## Ingest Events into API

```bash
python ingest.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET /health | Service status |
| POST /events/ingest | Ingest detection events |
| GET /stores/{id}/metrics | Visitor and conversion metrics |
| GET /stores/{id}/funnel | Conversion funnel |
| GET /stores/{id}/heatmap | Zone heatmap |
| GET /stores/{id}/anomalies | Active anomalies |

## Store ID
## Architecture
See docs/DESIGN.md for full architecture overview.
See docs/CHOICES.md for engineering decision rationale.
## Live Dashboard

Run the terminal dashboard while API is running:

```bash
python dashboard.py
```

Shows real-time: unique visitors, conversion rate, zone dwell, funnel, anomalies.
Updates every 2 seconds.
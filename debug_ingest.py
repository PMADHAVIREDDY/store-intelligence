import json, requests

with open('events/store2_zone.jsonl', 'r') as f:
    events = [json.loads(line) for line in f if line.strip()]

# Try just 1 event
resp = requests.post('http://localhost:8000/events/ingest', json={'events': [events[0]]})
print('Response:', resp.json())
print('Event sent:', json.dumps(events[0], indent=2))

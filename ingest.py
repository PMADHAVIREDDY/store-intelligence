import json, requests

files = [
    'events/cam2_events.jsonl',
    'events/cam3_events.jsonl',
    'events/cam5_events.jsonl',
]

total = 0
for filepath in files:
    with open(filepath, 'r') as f:
        events = [json.loads(line) for line in f if line.strip()]
    print(filepath, len(events), 'events')
    for i in range(0, len(events), 500):
        batch = events[i:i+500]
        resp = requests.post('http://localhost:8000/events/ingest', json={'events': batch})
        r = resp.json()
        total += r['accepted']
        print('accepted:', r['accepted'], 'rejected:', r['rejected'])

print('Total ingested:', total)

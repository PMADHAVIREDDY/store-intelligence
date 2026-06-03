import json, requests

files = [
    'events/store2_entry1.jsonl',
    'events/store2_entry2.jsonl',
    'events/store2_zone.jsonl',
    'events/store2_billing.jsonl',
]

total = 0
for filepath in files:
    try:
        with open(filepath, 'r') as f:
            events = [json.loads(line) for line in f if line.strip()]
        print(filepath, len(events), 'events')
        for i in range(0, len(events), 500):
            batch = events[i:i+500]
            resp = requests.post('http://localhost:8000/events/ingest', json={'events': batch})
            r = resp.json()
            total += r['accepted']
            print('accepted:', r['accepted'], 'rejected:', r['rejected'])
    except Exception as e:
        print('Error:', filepath, e)

print('Total ingested:', total)

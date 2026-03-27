import json

# Check match data structure
f = "output/match_data/shard_0/match_details.json"
with open(f, 'r', encoding='utf-8') as fh:
    data = json.load(fh)

print("Type:", type(data).__name__)
if isinstance(data, list):
    print("List length:", len(data))
    m = data[0]
    print("First item type:", type(m).__name__)
    print("First item keys:", list(m.keys()) if isinstance(m, dict) else "N/A")
    if isinstance(m, dict):
        print("Sample:", json.dumps(m, ensure_ascii=False)[:1000])
elif isinstance(data, dict):
    keys = list(data.keys())[:3]
    print("Keys sample:", keys)
    print("First value type:", type(data[keys[0]]).__name__)

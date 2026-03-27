import json

# Check match data - look for rank info in player_summaries and round_records
f = "output/match_data/shard_0/match_details.json"
with open(f, 'r', encoding='utf-8') as fh:
    data = json.load(fh)

m = data[0]

# Check player_summaries
ps = m.get("player_summaries", [])
print("=== Player Summary sample ===")
if ps:
    p = ps[0]
    print("Keys:", list(p.keys()))
    # Check for rank-related fields
    for k in p.keys():
        if "rank" in k.lower() or "mmr" in k.lower() or "elo" in k.lower():
            print(f"  RANK FIELD: {k} = {p[k]}")

# Check round_records
rr = m.get("round_records", [])
print("\n=== Round Records sample ===")
if rr:
    r = rr[0]
    print("Round keys:", list(r.keys()))
    # Check players in round
    rp = r.get("players", r.get("player_stats", []))
    if rp:
        print("Round player keys:", list(rp[0].keys()) if isinstance(rp[0], dict) else type(rp[0]))
        # Check for rank fields
        for k in rp[0].keys():
            if "rank" in k.lower() or "mmr" in k.lower():
                print(f"  RANK FIELD: {k} = {rp[0][k]}")

# Deep search for rank info
print("\n=== Deep search for rank-related fields ===")
def find_rank_fields(obj, path="", depth=0):
    if depth > 5:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "rank" in k.lower() or "mmr" in k.lower() or "elo" in k.lower() or "tier" in k.lower():
                print(f"  {path}.{k} = {repr(v)[:100]}")
            find_rank_fields(v, f"{path}.{k}", depth+1)
    elif isinstance(obj, list) and obj:
        find_rank_fields(obj[0], f"{path}[0]", depth+1)

find_rank_fields(m, "match")

# Also check extra match data
print("\n=== Extra match data structure ===")
try:
    f2 = "output/extra_match_data/shard_0/match_details.json"
    with open(f2, 'r', encoding='utf-8') as fh:
        data2 = json.load(fh)
    print("Type:", type(data2).__name__)
    if isinstance(data2, list):
        print("Length:", len(data2))
        if data2:
            m2 = data2[0]
            print("Keys:", list(m2.keys()) if isinstance(m2, dict) else "N/A")
            find_rank_fields(m2, "extra_match")
    elif isinstance(data2, dict):
        keys = list(data2.keys())[:3]
        print("Keys:", keys)
        v = data2[keys[0]]
        print("First value type:", type(v).__name__)
        if isinstance(v, list) and v:
            find_rank_fields(v[0], "extra_match_item")
except Exception as e:
    print(f"Error: {e}")

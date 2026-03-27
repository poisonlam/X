import json, glob, os

BASE = os.path.join(os.path.dirname(__file__), "output/extra_match_data")

# 检查 progress 文件格式
prog = os.path.join(BASE, "_shard_0_progress.json")
d = json.load(open(prog, "r", encoding="utf-8"))
cp = d.get("completed_players", [])
print(f"Progress completed_players type: {type(cp)}, count: {len(cp)}")
if cp:
    print(f"  Sample[0] type: {type(cp[0])}")
    if isinstance(cp[0], dict):
        print(f"  Sample[0] keys: {list(cp[0].keys())}")
        print(f"  Sample[0]: {cp[0]}")
    else:
        print(f"  Sample[0]: {cp[0]}")
    if len(cp) > 1:
        print(f"  Sample[1]: {cp[1]}")

# 检查 extra_players 文件格式
ep = os.path.join(BASE, "_extra_players.json")
d2 = json.load(open(ep, "r", encoding="utf-8"))
print(f"\nExtra players type: {type(d2)}, count: {len(d2)}")
if d2:
    print(f"  Sample[0] type: {type(d2[0])}")
    if isinstance(d2[0], dict):
        print(f"  Sample[0] keys: {list(d2[0].keys())}")
        print(f"  Sample[0]: {d2[0]}")
    else:
        print(f"  Sample[0]: {d2[0]}")
    if len(d2) > 1:
        print(f"  Sample[1]: {d2[1]}")

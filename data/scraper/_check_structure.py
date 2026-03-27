"""检查Extra比赛数据的实际结构"""
import json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))

# 看一场Extra比赛的数据结构
for sf in sorted(glob.glob(os.path.join(BASE, "output/extra_match_data/shard_*/match_details.json")))[:1]:
    with open(sf, "r", encoding="utf-8") as f:
        matches = json.load(f)
    
    if matches:
        m = matches[0]
        print(f"Match keys: {list(m.keys())}")
        print(f"Match sample (truncated):")
        for k, v in m.items():
            if isinstance(v, (list, dict)):
                print(f"  {k}: type={type(v).__name__}, len={len(v)}")
                if isinstance(v, list) and v:
                    print(f"    [0] type={type(v[0]).__name__}")
                    if isinstance(v[0], dict):
                        print(f"    [0] keys={list(v[0].keys())}")
                        # 进一步检查
                        for k2, v2 in v[0].items():
                            if isinstance(v2, (list, dict)):
                                print(f"      {k2}: type={type(v2).__name__}, len={len(v2)}")
                                if isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                                    print(f"        [0] keys={list(v2[0].keys())[:10]}")
                            else:
                                sv = str(v2)[:80]
                                print(f"      {k2}: {sv}")
                elif isinstance(v, dict):
                    print(f"    keys={list(v.keys())[:10]}")
            else:
                sv = str(v)[:100]
                print(f"  {k}: {sv}")

# 也看一场PC比赛
print("\n\n--- PC Match ---")
for sf in sorted(glob.glob(os.path.join(BASE, "output/match_data/shard_*/match_details.json")))[:1]:
    with open(sf, "r", encoding="utf-8") as f:
        matches = json.load(f)
    
    if matches:
        m = matches[0]
        print(f"Match keys: {list(m.keys())}")
        for k, v in m.items():
            if isinstance(v, (list, dict)):
                print(f"  {k}: type={type(v).__name__}, len={len(v)}")
                if isinstance(v, list) and v:
                    print(f"    [0] type={type(v[0]).__name__}")
                    if isinstance(v[0], dict):
                        print(f"    [0] keys={list(v[0].keys())}")
            else:
                sv = str(v)[:100]
                print(f"  {k}: {sv}")

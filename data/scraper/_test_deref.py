"""测试deref函数是否能正确解析新格式的NUXT数据"""
import requests
import re
import json
import sys
sys.path.insert(0, ".")

# 导入实际的deref和parse_nuxt_page
from parallel_collect import parse_nuxt_page, deref

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

# 用一个已经成功的玩家的UUID测试
target = lb[50]
dn = target["displayName"]
pid = target["profileId"]
url = f"https://stats.cc/siege/{dn}/{pid}"
print(f"Testing: {dn} / {pid}")

r = session.get(url, timeout=(10, 25))
print(f"Status: {r.status_code}")

nuxt = parse_nuxt_page(r.text)
if nuxt is None:
    print("parse_nuxt_page returned None!")
    exit(1)

print(f"NUXT entries: {len(nuxt)}")

# 用代码中的逻辑找match items
matches = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
        match = deref(nuxt, i, max_depth=20)
        print(f"\n=== Match at index {i} ===")
        print(f"Before deref: {json.dumps(item, default=str)[:200]}")
        if match:
            print(f"After deref: {json.dumps(match, default=str)[:400]}")
            match_id = match.get('id')
            print(f"  id type: {type(match_id).__name__}, value: {match_id}")
            print(f"  map: {match.get('map')}")
            print(f"  playlist: {match.get('playlist')}")
            print(f"  started_at: {match.get('started_at')}")
            
            # 检查条件: isinstance(match.get('id'), str) and len(match.get('id', '')) > 10
            mid = match.get('id')
            passes = isinstance(mid, str) and len(mid) > 10
            print(f"  Passes filter (id is str and len>10): {passes}")
            
            if passes:
                matches.append({
                    'match_id': match.get('id'),
                    'map': match.get('map'),
                    'playlist': match.get('playlist'),
                })
        else:
            print("deref returned None/falsy!")
        
        if len(matches) >= 3:
            break

print(f"\n=== Summary ===")
print(f"Total matches that passed filter: {len(matches)}")
for m in matches:
    print(f"  {m['match_id'][:30]}... | {m['playlist']} | {m['map']}")

# 如果没有通过过滤器的，看看id到底是什么
if not matches:
    print("\nNO matches passed! Checking id values:")
    for i in range(len(nuxt)):
        item = nuxt[i]
        if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
            match = deref(nuxt, i, max_depth=20)
            if match:
                mid = match.get('id')
                print(f"  index {i}: id={mid} (type={type(mid).__name__})")
            if i > 2900:
                break

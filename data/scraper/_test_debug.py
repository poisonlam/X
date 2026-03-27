"""调试fetch_player_matches：看看到底哪一步返回了None"""
import sys
sys.path.insert(0, ".")
import requests
import json
import re

# 手动重现fetch_player_matches的逻辑
from parallel_collect import parse_nuxt_page, deref, get_session

with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

target = lb[50]
player_name = target["displayName"]
profile_id = target["profileId"]

print(f"Player: {player_name} / {profile_id}")

session = get_session()
url = f"https://stats.cc/siege/{player_name}/{profile_id}"
print(f"URL: {url}")

# Session headers
print(f"Session headers: {dict(session.headers)}")

r = session.get(url, timeout=(10, 25))
print(f"Status: {r.status_code}")
print(f"Content-Length: {len(r.text)}")

# Step 1: 检查状态码走哪个分支
if r.status_code == 429:
    print("HIT: 429 Rate Limited")
elif r.status_code == 404:
    print("HIT: 404 Not Found -> returns None")
elif r.status_code == 500 or r.status_code == 200:
    print(f"HIT: {r.status_code} -> trying parse_nuxt_page")
    
    nuxt = parse_nuxt_page(r.text)
    print(f"  parse_nuxt_page result: {'None' if nuxt is None else f'list({len(nuxt)})'}")
    
    if nuxt:
        matches = []
        for i in range(len(nuxt)):
            item = nuxt[i]
            if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
                match = deref(nuxt, i, max_depth=20)
                if match and isinstance(match.get('id'), str) and len(match.get('id', '')) > 10:
                    matches.append({
                        'match_id': match.get('id'),
                        'map': match.get('map'),
                        'playlist': match.get('playlist'),
                    })
        
        print(f"  Matches found: {len(matches)}")
        if matches:
            if r.status_code == 500:
                print(f"  -> HTTP 500 but got {len(matches)} matches -> RETURN matches")
            else:
                print(f"  -> RETURN matches")
        elif r.status_code == 500:
            print(f"  -> HTTP 500 no data -> RETURN []")
        elif r.status_code == 200:
            print(f"  -> HTTP 200 no data -> RETURN []")
    else:
        print(f"  nuxt is None/empty")
        if r.status_code != 200:
            print(f"  -> status != 200, would continue retry loop")
        else:
            print(f"  -> status == 200, RETURN None (line 239)")
else:
    print(f"HIT: HTTP {r.status_code} (not 200/500)")

# 对比：直接用新的session（不复用）
print(f"\n\n=== 使用全新的session ===")
session2 = requests.Session()
session2.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})
r2 = session2.get(url, timeout=(10, 25))
print(f"Status: {r2.status_code}")
print(f"Content-Length: {len(r2.text)}")
nuxt2 = parse_nuxt_page(r2.text)
print(f"parse_nuxt_page result: {'None' if nuxt2 is None else f'list({len(nuxt2)})'}")

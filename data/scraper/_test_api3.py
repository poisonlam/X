"""查看排行榜5680-5695号位的玩家数据，并做API测试"""
import json
import requests
import re
import time

# 检查排行榜数据
with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

print(f"Total leaderboard entries: {len(lb)}")

# 看5680-5695的玩家数据
print("\n=== Leaderboard entries 5680-5695 ===")
for i in range(5680, 5695):
    e = lb[i]
    dn = e.get("displayName", "N/A")
    pid = e.get("profileId", "N/A")
    rank = e.get("rank", "N/A")
    rp = e.get("rankPoints", "N/A")
    pos = e.get("leaderboardPosition", "N/A")
    print(f"  [{i}] pos={pos} | {dn} | pid={pid[:24]}... | {rank} | RP:{rp}")

# 用真正的profileId访问一个之前FAIL的玩家
target = lb[5687]
dn = target["displayName"]
pid = target["profileId"]
print(f"\n=== Testing: {dn} / {pid} ===")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

url = f"https://stats.cc/siege/{dn}/{pid}"
print(f"URL: {url}")
r = session.get(url, timeout=(10, 25))
print(f"Status: {r.status_code}")
print(f"Content-Length: {len(r.text)}")

# 解析NUXT
pattern = r'<script type="application/json" id="__NUXT_DATA__"[^>]*>(.*?)</script>'
match = re.search(pattern, r.text, re.DOTALL)
if match:
    nuxt = json.loads(match.group(1))
    print(f"NUXT entries: {len(nuxt)}")
    
    # 查找match-like items
    match_count = 0
    for idx, item in enumerate(nuxt):
        if isinstance(item, dict) and "map" in item and "playlist" in item:
            match_count += 1
            if match_count <= 3:
                print(f"  Match item [{idx}]: {json.dumps(item, default=str)[:200]}")
    print(f"Total match items: {match_count}")
    
    # 查找任何错误信息
    for idx, item in enumerate(nuxt):
        if isinstance(item, str) and len(item) > 20 and ("error" in item.lower() or "fail" in item.lower()):
            print(f"  Error string [{idx}]: {item[:200]}")
        if isinstance(item, dict) and ("error" in str(item).lower() or "statusCode" in item):
            print(f"  Error dict [{idx}]: {json.dumps(item, default=str)[:200]}")
else:
    print("No NUXT data found!")
    # 检查页面内容
    if "bug-outline" in r.text:
        print("Page contains error indicator (bug-outline icon)")
    if "500" in r.text[:500]:
        print("Page contains '500' in header area")
    # 尝试其他NUXT模式
    alt_pattern = r'window\.__NUXT__\s*=\s*(.+?)\s*</script>'
    alt_match = re.search(alt_pattern, r.text, re.DOTALL)
    if alt_match:
        print("Found window.__NUXT__ pattern")
    else:
        print("No alternative NUXT pattern found either")
    
    # 看看script标签
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text[:5000], re.DOTALL)
    print(f"\nScript tags in first 5000 chars: {len(scripts)}")
    for i, s in enumerate(scripts[:5]):
        print(f"  Script {i}: {s[:150]}")

# 对比一个成功的玩家
print("\n\n=== 对比测试：排行榜前100的玩家 ===")
target2 = lb[50]
dn2 = target2["displayName"]
pid2 = target2["profileId"]
print(f"Player: {dn2} / {pid2}")
url2 = f"https://stats.cc/siege/{dn2}/{pid2}"
r2 = session.get(url2, timeout=(10, 25))
print(f"Status: {r2.status_code}")
match2 = re.search(pattern, r2.text, re.DOTALL)
if match2:
    nuxt2 = json.loads(match2.group(1))
    mc2 = sum(1 for item in nuxt2 if isinstance(item, dict) and "map" in item and "playlist" in item)
    print(f"NUXT entries: {len(nuxt2)}, Match items: {mc2}")
else:
    print("No NUXT data found for reference player either!")

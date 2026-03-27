"""深入测试：解析stats.cc返回的NUXT数据，看看500页面到底有什么"""
import requests
import re
import json

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
})

def parse_nuxt_page(html):
    """解析页面中的__NUXT_DATA__"""
    pattern = r'<script type="application/json" id="__NUXT_DATA__"[^>]*>(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return None
    return None

# 测试一个排行榜上的FAIL玩家
url = "https://stats.cc/siege/fz.sakura/5687"
print(f"Testing: {url}")
r = session.get(url, timeout=(10, 25))
print(f"Status: {r.status_code}")

nuxt = parse_nuxt_page(r.text)
if nuxt:
    print(f"NUXT data entries: {len(nuxt)}")
    # 查找包含match/map/playlist的条目
    match_count = 0
    for i, item in enumerate(nuxt):
        if isinstance(item, dict):
            if 'map' in item and 'playlist' in item and 'scores' in item:
                match_count += 1
                if match_count <= 3:
                    print(f"  Match-like item at index {i}: {list(item.keys())}")
    print(f"  Total match-like items: {match_count}")
    
    # 看看所有dict类型的项有哪些键
    key_sets = {}
    for i, item in enumerate(nuxt):
        if isinstance(item, dict) and len(item) > 0:
            keys = tuple(sorted(item.keys()))
            if keys not in key_sets:
                key_sets[keys] = []
            key_sets[keys].append(i)
    
    print(f"\n  Unique dict key patterns: {len(key_sets)}")
    for keys, indices in sorted(key_sets.items(), key=lambda x: -len(x[1])):
        print(f"    {keys}: {len(indices)} items (first at idx {indices[0]})")
        if len(indices) <= 3:
            for idx in indices:
                print(f"      [{idx}]: {str(nuxt[idx])[:200]}")

    # 看看是否有error相关的信息
    for i, item in enumerate(nuxt):
        if isinstance(item, dict):
            if 'error' in item or 'statusCode' in item or 'message' in item:
                print(f"\n  Error/Status item at {i}: {item}")
        elif isinstance(item, str) and ('error' in item.lower() or 'not found' in item.lower()):
            print(f"\n  Error string at {i}: {item[:200]}")
else:
    print("No NUXT data found!")

# 对比：用正确的UUID格式测试一个已成功的玩家
print("\n\n=== 对比测试：用UUID格式的profile_id ===")
# 从leaderboard数据获取一个真实的玩家信息
with open("output/match_data/_shard_0_progress.json", "r") as f:
    prog = json.load(f)

# 取第一个完成的玩家UUID
first_uuid = prog["completed_players"][0]
print(f"First completed player UUID: {first_uuid}")

# 看看排行榜文件获取这个玩家的名字
with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

if isinstance(lb, list) and len(lb) > 0:
    print(f"Leaderboard entries: {len(lb)}")
    print(f"First entry keys: {list(lb[0].keys()) if isinstance(lb[0], dict) else 'not dict'}")
    # 查找这个UUID
    found = None
    for entry in lb:
        if isinstance(entry, dict) and entry.get("profile_id") == first_uuid:
            found = entry
            break
    if found:
        print(f"Found: name={found.get('name')}, profile_id={found.get('profile_id')}")
    else:
        print(f"UUID {first_uuid} not found in leaderboard")
    
    # 看看排行榜5600+的玩家
    if len(lb) > 5680:
        for i in range(5685, 5695):
            entry = lb[i]
            if isinstance(entry, dict):
                print(f"  [{i}] name={entry.get('name')}, profile_id={entry.get('profile_id', 'N/A')[:36]}")

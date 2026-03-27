"""对比分析：检查NUXT数据格式是否变了"""
import requests
import re
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

# 排行榜第50名
with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

target = lb[50]
dn = target["displayName"]
pid = target["profileId"]
url = f"https://stats.cc/siege/{dn}/{pid}"
print(f"Testing: {url}")

r = session.get(url, timeout=(10, 25))
print(f"Status: {r.status_code}")

# 获取application/json的script内容
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"Found {len(json_blocks)} JSON blocks")

if json_blocks:
    raw = json_blocks[0]
    print(f"Block 0 length: {len(raw)}")
    
    try:
        nuxt = json.loads(raw)
        print(f"Parsed! Type: {type(nuxt).__name__}")
        
        if isinstance(nuxt, list):
            print(f"Array length: {len(nuxt)}")
            print(f"\nFirst 5 items:")
            for i, item in enumerate(nuxt[:5]):
                print(f"  [{i}]: {type(item).__name__} = {str(item)[:200]}")
            
            # 查找map/playlist/scores类型的dict
            match_items = []
            for i, item in enumerate(nuxt):
                if isinstance(item, dict) and "map" in item and "playlist" in item and "scores" in item:
                    match_items.append((i, item))
            
            print(f"\nMatch-like items (map+playlist+scores): {len(match_items)}")
            for i, (idx, item) in enumerate(match_items[:3]):
                print(f"  [{idx}]: {json.dumps(item, default=str)[:300]}")
            
            # 新格式的标记
            if len(nuxt) > 0:
                first = nuxt[0]
                if isinstance(first, list) and len(first) == 2 and first[0] == "ShallowReactive":
                    print(f"\n!!! NEW FORMAT DETECTED: ShallowReactive wrapper !!!")
                    print(f"This is Nuxt 3.x payload format with Turbo/ShallowReactive markers")
                    print(f"The old parse_nuxt_page + deref logic may not work with this format")
                    
                    # 看看能不能找到比赛数据
                    # 在新格式中，数据通常是嵌套的引用结构
                    print(f"\n=== 扫描新格式中的关键数据 ===")
                    for i, item in enumerate(nuxt):
                        if isinstance(item, str) and item in ("map", "playlist", "scores", "match_id", "started_at"):
                            print(f"  Key string at [{i}]: {item}")
                            # 前后5个元素
                            context = nuxt[max(0,i-2):i+5]
                            print(f"    Context: {[str(x)[:60] for x in context]}")
                            if i < 20:
                                break
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"First 200 chars: {raw[:200]}")

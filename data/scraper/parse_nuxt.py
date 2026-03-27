"""
解析 stats.cc __NUXT_DATA__ 获取排行榜玩家数据
并测试 r6.stats.cc API
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# =========================================
# Part 1: 解析 __NUXT_DATA__ 
# =========================================
print("=" * 70)
print("Part 1: Parsing __NUXT_DATA__ from stats.cc leaderboard")
print("=" * 70)

r = requests.get('https://stats.cc/siege/leaderboards/pc/ranked/rankPoints', headers=headers, timeout=30)
print(f"HTTP {r.status_code}, {len(r.text)} bytes")

# 找到 __NUXT_DATA__ script block
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"Found {len(json_blocks)} JSON blocks")

if json_blocks:
    raw = json_blocks[0]
    print(f"NUXT data: {len(raw)} chars")
    
    try:
        nuxt_data = json.loads(raw)
        print(f"Parsed as: {type(nuxt_data).__name__}")
        if isinstance(nuxt_data, list):
            print(f"Array length: {len(nuxt_data)}")
            # Nuxt 3 __NUXT_DATA__ 是一个扁平数组，需要解引用
            # 打印前100个元素看结构
            print("\nFirst 50 elements:")
            for i, item in enumerate(nuxt_data[:50]):
                print(f"  [{i}] {repr(item)[:120]}")
            
            # 搜索看起来像玩家数据的元素
            print("\n\nSearching for player-like data...")
            player_data_indices = []
            for i, item in enumerate(nuxt_data):
                if isinstance(item, str) and ('nameOnPlatform' in item or 'rankPoints' in item or 'profileId' in item):
                    print(f"  [{i}] {repr(item)[:200]}")
                    player_data_indices.append(i)
                elif isinstance(item, dict):
                    keys = list(item.keys())
                    if any(k in keys for k in ['nameOnPlatform', 'rankPoints', 'profileId', 'name', 'rank', 'level']):
                        print(f"  [{i}] dict keys: {keys}")
                        print(f"       values: {json.dumps(item, ensure_ascii=False)[:300]}")
                        player_data_indices.append(i)
            
            # 搜索 Champion、段位名、玩家名
            print("\n\nSearching for rank names...")
            for i, item in enumerate(nuxt_data):
                if isinstance(item, str) and item in ['champion', 'diamond-i', 'diamond-ii', 'emerald-i']:
                    ctx_start = max(0, i-5)
                    ctx_end = min(len(nuxt_data), i+5)
                    print(f"  [{i}] '{item}' context: {nuxt_data[ctx_start:ctx_end]}")
            
            # 搜索看起来是 rankPoints 数值的高分（>5000）
            print("\n\nSearching for high rankPoints values...")
            high_vals = []
            for i, item in enumerate(nuxt_data):
                if isinstance(item, (int, float)) and 5000 < item < 100000:
                    ctx_start = max(0, i-3)
                    ctx_end = min(len(nuxt_data), i+3)
                    high_vals.append((i, item, nuxt_data[ctx_start:ctx_end]))
            print(f"  Found {len(high_vals)} values > 5000")
            for idx, val, ctx in high_vals[:10]:
                print(f"  [{idx}] {val} context: {ctx}")
                
        elif isinstance(nuxt_data, dict):
            print(f"Dict keys: {list(nuxt_data.keys())[:20]}")
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"First 200 chars: {raw[:200]}")

# =========================================
# Part 2: 测试 r6.stats.cc API
# =========================================
print("\n\n" + "=" * 70)
print("Part 2: Testing r6.stats.cc API")
print("=" * 70)

api_headers = {
    'User-Agent': headers['User-Agent'],
    'Accept': 'application/json',
    'Origin': 'https://stats.cc',
    'Referer': 'https://stats.cc/',
}

api_tests = [
    'https://r6.stats.cc/',
    'https://r6.stats.cc/leaderboards/pc/ranked/rankPoints',
    'https://r6.stats.cc/leaderboard/pc/ranked/rankPoints',
    'https://r6.stats.cc/api/leaderboards/pc/ranked/rankPoints',
    'https://r6.stats.cc/v1/leaderboards/pc/ranked/rankPoints',
    'https://r6.stats.cc/leaderboards?stat=rankPoints&page=1&mode=ranked&platform=pc',
    'https://r6.stats.cc/player/Beaulo',
    'https://r6.stats.cc/search?q=Beaulo',
    'https://r6.stats.cc/stats/Beaulo',
]

for url in api_tests:
    try:
        r = requests.get(url, headers=api_headers, timeout=10)
        print(f"\n  {url}")
        print(f"  HTTP {r.status_code}, Len={len(r.text)}")
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, dict):
                    print(f"  [JSON] Keys: {list(data.keys())[:15]}")
                elif isinstance(data, list):
                    print(f"  [JSON] Array of {len(data)}")
                print(f"  Preview: {json.dumps(data, ensure_ascii=False)[:300]}")
            except:
                print(f"  [Not JSON] {r.text[:200]}")
        else:
            print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"\n  {url} -> Error: {e}")

# =========================================
# Part 3: 分析 stats.cc Nuxt JS bundle 中的 API 路由
# =========================================
print("\n\n" + "=" * 70)
print("Part 3: Deep analysis of stats.cc JS bundle for API routes")
print("=" * 70)

r = requests.get('https://stats.cc/_nuxt/DaeC7Zk9.js', headers=headers, timeout=30)
if r.status_code == 200:
    text = r.text
    print(f"JS bundle: {len(text)} bytes")
    
    # 搜索 r6.stats.cc 相关的路径
    patterns = [
        r'r6\.stats\.cc[^"\'`\s]{0,200}',
        r'leaderboard[^"\'`\s]{0,200}',
        r'/leaderboard[^"\'`\s]{0,100}',
        r'statsapi\.net[^"\'`\s]{0,200}',
    ]
    
    for pattern in patterns:
        matches = list(set(re.findall(pattern, text, re.IGNORECASE)))
        if matches:
            print(f"\n  Pattern: {pattern}")
            for m in sorted(matches)[:10]:
                print(f"    {m[:200]}")

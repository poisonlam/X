"""
检查 r6data.eu 是否有玩家地图统计数据的端点
以及 stats.cc 页面是否有地图数据
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}

# =========================================
# Part 1: 测试 r6data.eu 地图统计端点
# =========================================
print("=" * 70)
print("Part 1: Testing r6data.eu map stats endpoints")
print("=" * 70)

test_endpoints = [
    '/api/stats?type=mapStats&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=map&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=maps&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=mapBans&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=gameStats&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=matchHistory&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=matches&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=generalStats&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=weaponStats&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=seasonalMapStats&nameOnPlatform=Beaulo&platformType=uplay',
]

for endpoint in test_endpoints:
    url = f'https://r6data.eu{endpoint}'
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"\n  {endpoint.split('type=')[1].split('&')[0]}")
        print(f"    HTTP {r.status_code}, Len={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 10:
            try:
                data = r.json()
                if isinstance(data, dict):
                    print(f"    Keys: {list(data.keys())[:10]}")
                    # 检查是否有地图相关数据
                    for key in data.keys():
                        val = data[key]
                        if isinstance(val, list):
                            print(f"    {key}: list[{len(val)}]")
                            if val:
                                first = val[0]
                                if isinstance(first, dict):
                                    print(f"      First item keys: {list(first.keys())[:10]}")
                        elif isinstance(val, dict):
                            print(f"    {key}: dict keys={list(val.keys())[:8]}")
                elif isinstance(data, list):
                    print(f"    List of {len(data)}")
                    if data:
                        print(f"    First: {json.dumps(data[0], ensure_ascii=False)[:300]}")
                print(f"    Full preview: {json.dumps(data, ensure_ascii=False)[:300]}")
            except:
                print(f"    Not JSON: {r.text[:200]}")
        else:
            print(f"    Response: {r.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")

# =========================================
# Part 2: 看看 r6data.eu 的 operatorStats 中是否包含地图数据
# =========================================
print("\n\n" + "=" * 70)
print("Part 2: Checking operatorStats for map data")
print("=" * 70)

r = requests.get('https://r6data.eu/api/stats', headers=headers, params={
    'type': 'operatorStats',
    'nameOnPlatform': 'Beaulo',
    'platformType': 'uplay',
    'modes': 'ranked',
}, timeout=30)

if r.status_code == 200:
    data = r.json()
    print(f"operatorStats: {type(data).__name__}")
    if isinstance(data, dict):
        print(f"Top-level keys: {list(data.keys())}")
        for key in data.keys():
            val = data[key]
            if isinstance(val, list) and len(val) > 0:
                print(f"\n  {key}: list[{len(val)}]")
                first = val[0]
                if isinstance(first, dict):
                    print(f"    Keys: {list(first.keys())}")
                    print(f"    Sample: {json.dumps(first, ensure_ascii=False)[:400]}")
                    # 检查是否有 map 字段
                    if 'maps' in first or 'mapStats' in first or 'map' in first:
                        print(f"    *** FOUND MAP DATA! ***")

# =========================================
# Part 3: 搜索 r6data.eu JS 中的地图统计相关代码
# =========================================
print("\n\n" + "=" * 70)
print("Part 3: Searching r6data.eu JS for map stats")
print("=" * 70)

# 下载玩家页面的 JS（应该包含地图统计的加载逻辑）
for js_path in ['/dist/7ecb0e295c61.js', '/dist/d049bc0ae957.js', '/dist/7f781d51eaf3.js']:
    r = requests.get(f'https://r6data.eu{js_path}', headers=headers, timeout=15)
    if r.status_code != 200:
        continue
    text = r.text
    # 搜索 mapStats, mapBans, mapData 等
    for kw in ['mapStat', 'mapBan', 'mapData', 'type=map', 'operatorMap', 'operator_map']:
        if kw.lower() in text.lower():
            idx = text.lower().find(kw.lower())
            ctx = text[max(0,idx-100):idx+200]
            print(f"\n  {js_path} [{kw}]: ...{ctx}...")

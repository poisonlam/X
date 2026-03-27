"""
从 stats.cc 玩家个人页面解析 NUXT 数据，提取地图统计
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 获取 Beaulo 的 stats.cc 页面
# 先从排行榜获取第1名的 profileId
r = requests.get('https://stats.cc/siege/exolt2turNt/3bae0298-8f3f-4fe2-ac96-91e12d31d381', headers=headers, timeout=30)
print(f"Player page: HTTP {r.status_code}, {len(r.text)} bytes")

# 解析 NUXT DATA
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"JSON blocks: {len(json_blocks)}")

if json_blocks:
    nuxt = json.loads(json_blocks[0])
    print(f"NUXT data: array of {len(nuxt)} elements")
    
    # 找到根数据结构
    root = nuxt[3] if len(nuxt) > 3 and isinstance(nuxt[3], dict) else None
    if root:
        print(f"\nRoot keys:")
        for k in root.keys():
            print(f"  {k}: -> index {root[k]}")
    
    # 搜索包含地图名的元素
    print("\n\nSearching for map statistics data...")
    map_data_indices = []
    for i, item in enumerate(nuxt):
        if isinstance(item, str) and item in ['oregon', 'coastline', 'club-house', 'kafe-dostoyevsky', 'bank', 'villa', 'border', 'consulate', 'nighthaven-labs', 'chalet']:
            # 看看附近的数据
            start = max(0, i-5)
            end = min(len(nuxt), i+10)
            print(f"\n  [{i}] '{item}'")
            for j in range(start, end):
                elem = nuxt[j]
                if isinstance(elem, dict):
                    print(f"    [{j}] dict keys: {list(elem.keys())[:15]}")
                elif isinstance(elem, (int, float)):
                    print(f"    [{j}] {elem}")
                elif isinstance(elem, str):
                    print(f"    [{j}] '{elem[:80]}'")
                elif isinstance(elem, list):
                    print(f"    [{j}] list: {repr(elem)[:100]}")
                else:
                    print(f"    [{j}] {type(elem).__name__}: {repr(elem)[:80]}")
            
            map_data_indices.append(i)
            if len(map_data_indices) >= 5:
                break
    
    # 搜索包含 wins/losses/rounds 的 dict（可能是地图级统计）
    print("\n\n--- Searching for map-level stats dicts ---")
    for i, item in enumerate(nuxt):
        if isinstance(item, dict):
            keys = set(item.keys())
            # 地图统计应该有 wins/losses 或 rounds/won
            if ('wins' in keys and 'losses' in keys) or ('rounds' in keys):
                # 检查附近是否有地图名
                nearby = nuxt[max(0,i-10):i+10]
                nearby_strs = [x for x in nearby if isinstance(x, str)]
                map_names = ['oregon', 'coastline', 'club-house', 'kafe-dostoyevsky', 'bank', 'villa', 'border', 'consulate']
                has_map = any(m in nearby_strs for m in map_names)
                if has_map or 'map' in str(keys).lower():
                    print(f"\n  [{i}] {keys}")
                    vals = {k: nuxt[v] if isinstance(v, int) and v < len(nuxt) else v for k, v in item.items()}
                    print(f"    Values: {json.dumps(vals, ensure_ascii=False, default=str)[:300]}")
    
    # 搜索 "maps" 或 "mapStats" 类的 key 在任何 dict 中
    print("\n\n--- Searching for 'maps' key in dicts ---")
    for i, item in enumerate(nuxt):
        if isinstance(item, dict):
            for k in item.keys():
                if 'map' in k.lower():
                    print(f"  [{i}] has key '{k}' -> {item[k]}")
                    # 解引用看值
                    val_idx = item[k]
                    if isinstance(val_idx, int) and val_idx < len(nuxt):
                        val = nuxt[val_idx]
                        if isinstance(val, dict):
                            print(f"    -> dict keys: {list(val.keys())[:15]}")
                        elif isinstance(val, list):
                            print(f"    -> list[{len(val)}]")
                        else:
                            print(f"    -> {repr(val)[:100]}")

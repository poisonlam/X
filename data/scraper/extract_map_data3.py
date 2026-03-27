"""
完整解析 stats.cc 玩家页面中的地图统计和比赛历史
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def deref(data, idx, depth=0, max_depth=20, cache=None):
    if cache is None:
        cache = {}
    if idx in cache:
        return cache[idx]
    if depth > max_depth or idx >= len(data):
        return None
    item = data[idx]
    if isinstance(item, (str, float, bool)) or item is None:
        return item
    if isinstance(item, int):
        return item
    if isinstance(item, list):
        if len(item) == 2 and isinstance(item[0], str) and item[0] in ('ShallowReactive', 'Reactive', 'ShallowRef', 'Ref', 'Set'):
            result = deref(data, item[1], depth+1, max_depth, cache)
            cache[idx] = result
            return result
        result = [deref(data, i, depth+1, max_depth, cache) if isinstance(i, int) else i for i in item]
        cache[idx] = result
        return result
    if isinstance(item, dict):
        result = {}
        for k, v in item.items():
            result[k] = deref(data, v, depth+1, max_depth, cache) if isinstance(v, int) else v
        cache[idx] = result
        return result
    return item

r = requests.get('https://stats.cc/siege/exolt2turNt/3bae0298-8f3f-4fe2-ac96-91e12d31d381', headers=headers, timeout=30)
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
nuxt = json.loads(json_blocks[0])

# 1. 解析完整的比赛历史
print("=" * 70)
print("1. Match History (with map data)")
print("=" * 70)

matches = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
        match = deref(nuxt, i, max_depth=15)
        matches.append(match)

print(f"Found {len(matches)} matches")
if matches:
    print(f"\nFirst match (fully resolved):")
    print(json.dumps(matches[0], ensure_ascii=False, indent=2, default=str)[:1000])
    
    # 按地图统计
    map_stats = {}
    for m in matches:
        map_name = m.get('map', 'unknown')
        if map_name not in map_stats:
            map_stats[map_name] = {'wins': 0, 'losses': 0, 'total': 0}
        map_stats[map_name]['total'] += 1
        # 判断胜负: scores[1] > scores[0] 通常是赢（但需要看 player_summary）
    
    print(f"\nMatches per map:")
    for map_name, stats in sorted(map_stats.items()):
        print(f"  {map_name}: {stats['total']} matches")

# 2. 解析 maps 聚合数据
print("\n\n" + "=" * 70)
print("2. Maps aggregate data (from pinia_colada)")
print("=" * 70)

# 找到 pinia_colada 中的 maps 数据
root = nuxt[3]
state_root = nuxt[1765] if 1765 < len(nuxt) and isinstance(nuxt[1765], dict) else {}

for k, v_idx in state_root.items():
    if 'maps' in k:
        print(f"\nKey: {k[:120]}...")
        if isinstance(v_idx, int) and v_idx < len(nuxt):
            target_list = nuxt[v_idx]
            if isinstance(target_list, list) and len(target_list) >= 1:
                data_idx = target_list[0]
                if isinstance(data_idx, int) and data_idx < len(nuxt):
                    maps_data = deref(nuxt, data_idx, max_depth=15)
                    print(f"Maps data type: {type(maps_data).__name__}")
                    if isinstance(maps_data, dict):
                        print(f"Keys: {list(maps_data.keys())}")
                        print(json.dumps(maps_data, ensure_ascii=False, indent=2, default=str)[:2000])
                    elif isinstance(maps_data, list):
                        print(f"List of {len(maps_data)}")
                        for item in maps_data[:3]:
                            print(json.dumps(item, ensure_ascii=False, indent=2, default=str)[:500])
                else:
                    print(f"  data_idx: {data_idx}")
            else:
                print(f"  target type: {type(target_list).__name__}")

# 保存所有比赛历史
with open('data/scraper/output/sample_match_history.json', 'w', encoding='utf-8') as f:
    json.dump(matches, f, ensure_ascii=False, indent=2, default=str)
print(f"\nSaved {len(matches)} matches to sample_match_history.json")

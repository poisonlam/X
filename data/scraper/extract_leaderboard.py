"""
从 stats.cc 排行榜页面的 __NUXT_DATA__ 中提取完整的排行榜数据
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}

# 获取排行榜页面
r = requests.get('https://stats.cc/siege/leaderboards/pc/ranked/rankPoints', headers=headers, timeout=30)
print(f"HTTP {r.status_code}, {len(r.text)} bytes")

# 解析 NUXT DATA
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
nuxt_data = json.loads(json_blocks[0])

# 找到排行榜数据的入口
# 从 nuxt_data[3] 可以看到有个 key: 'leaderboards-{"stat":"rankPoints","page":1,"mode":"ranked","platform":"pc"}'
# 这个 key 对应的值是一个索引
root = nuxt_data[3]
print(f"\nRoot keys: {list(root.keys())[:10]}")

# 找到 leaderboard 相关的 key
lb_key = None
lb_index = None
for key, val in root.items():
    if 'leaderboard' in key.lower():
        lb_key = key
        lb_index = val
        print(f"\nLeaderboard key: {key}")
        print(f"  Points to index: {val}")
        break

# Nuxt 3 的 __NUXT_DATA__ 是一个扁平数组，用索引来互相引用
# 让我递归解引用
def deref(data, idx, depth=0, max_depth=15, cache=None):
    """递归解引用 Nuxt 3 __NUXT_DATA__ 中的数据"""
    if cache is None:
        cache = {}
    if idx in cache:
        return cache[idx]
    if depth > max_depth:
        return f"[MAX_DEPTH at {idx}]"
    
    item = data[idx]
    
    if isinstance(item, (str, int, float, bool)) or item is None:
        return item
    
    if isinstance(item, list):
        if len(item) == 2 and item[0] in ('ShallowReactive', 'Reactive', 'ShallowRef', 'Ref'):
            result = deref(data, item[1], depth + 1, max_depth, cache)
            cache[idx] = result
            return result
        elif len(item) == 2 and item[0] == 'Set':
            result = deref(data, item[1], depth + 1, max_depth, cache)
            cache[idx] = result
            return result
        else:
            result = [deref(data, i, depth + 1, max_depth, cache) for i in item if isinstance(i, int)]
            if not result:
                result = item
            cache[idx] = result
            return result
    
    if isinstance(item, dict):
        result = {}
        for key, val_idx in item.items():
            if isinstance(val_idx, int):
                result[key] = deref(data, val_idx, depth + 1, max_depth, cache)
            else:
                result[key] = val_idx
        cache[idx] = result
        return result
    
    return item

# 解引用排行榜数据
if lb_index is not None:
    print(f"\nDereferencing index {lb_index}...")
    lb_data = deref(nuxt_data, lb_index, max_depth=20)
    
    # 保存完整解引用数据
    with open('data/scraper/output/statscc_leaderboard_raw.json', 'w', encoding='utf-8') as f:
        json.dump(lb_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\nLeaderboard data type: {type(lb_data).__name__}")
    if isinstance(lb_data, dict):
        print(f"Keys: {list(lb_data.keys())}")
        for k, v in lb_data.items():
            if isinstance(v, list):
                print(f"  {k}: list of {len(v)}")
                if len(v) > 0:
                    print(f"    First item: {json.dumps(v[0], ensure_ascii=False, default=str)[:300]}")
            elif isinstance(v, dict):
                print(f"  {k}: dict with keys {list(v.keys())[:10]}")
            else:
                print(f"  {k}: {repr(v)[:200]}")
    elif isinstance(lb_data, list):
        print(f"List of {len(lb_data)} items")
        if len(lb_data) > 0:
            print(f"First item: {json.dumps(lb_data[0], ensure_ascii=False, default=str)[:500]}")

# 也看看直接的 nuxt_data[1745] (之前找到的玩家数据)
print("\n\n--- Direct player data at index 1745 ---")
player_sample = nuxt_data[1745]
print(f"Type: {type(player_sample).__name__}")
if isinstance(player_sample, dict):
    print(f"Keys: {list(player_sample.keys())}")
    print(json.dumps({k: nuxt_data[v] if isinstance(v, int) and v < len(nuxt_data) else v for k, v in player_sample.items()}, ensure_ascii=False, default=str)[:500])

# 手动查看 1742-1760 范围
print("\n\n--- Data around leaderboard (1742-1760) ---")
for i in range(1742, min(1770, len(nuxt_data))):
    item = nuxt_data[i]
    if isinstance(item, dict):
        print(f"  [{i}] dict keys: {list(item.keys())[:15]}")
    elif isinstance(item, list):
        print(f"  [{i}] list len={len(item)}: {repr(item)[:200]}")
    elif isinstance(item, str) and len(item) > 30:
        print(f"  [{i}] str: {item[:100]}")
    else:
        print(f"  [{i}] {repr(item)[:150]}")

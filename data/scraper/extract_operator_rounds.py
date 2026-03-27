"""
深入解析 stats.cc 玩家页面 NUXT 数据中的干员 + 对局 + 回合信息
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}

def deref(data, idx, depth=0, max_depth=25, cache=None):
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

# 获取排行榜第1名玩家页面
r = requests.get('https://stats.cc/siege/exolt2turNt/3bae0298-8f3f-4fe2-ac96-91e12d31d381', 
                  headers=HEADERS, timeout=30)
print(f"HTTP {r.status_code}, {len(r.text)} bytes")

json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
nuxt = json.loads(json_blocks[0])
print(f"NUXT items: {len(nuxt)}")

# 1. 找到包含 operator 相关字段的 dict
print("\n" + "=" * 70)
print("1. Finding all dicts with 'operator' keys")
print("=" * 70)

operator_dicts = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict):
        keys_str = str(list(item.keys()))
        if 'operator' in keys_str.lower():
            operator_dicts.append((i, list(item.keys())))
            if len(operator_dicts) <= 20:
                print(f"  [{i}] keys: {list(item.keys())[:15]}")

print(f"\nTotal dicts with 'operator' fields: {len(operator_dicts)}")

# 2. 找到 rounds 数据（每回合信息）
print("\n" + "=" * 70)
print("2. Finding round-level data")
print("=" * 70)

round_dicts = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict):
        keys = set(item.keys())
        # 回合数据通常有 round/outcome/operator 字段
        if 'round' in keys or ('outcome' in keys and 'operator' in keys):
            round_dicts.append(i)
            if len(round_dicts) <= 10:
                resolved = deref(nuxt, i, max_depth=10)
                print(f"  [{i}] {json.dumps(resolved, ensure_ascii=False, default=str)[:300]}")

print(f"\nTotal round-like dicts: {len(round_dicts)}")

# 3. 搜索 pinia_colada 中的数据查询 keys
print("\n" + "=" * 70)
print("3. Searching pinia_colada state for match/operator queries")
print("=" * 70)

# 找到 pinia_colada state root
nuxt_str = json.dumps(nuxt)
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and len(item) > 5:
        keys_joined = ' '.join(item.keys())
        if 'r6' in keys_joined and ('match' in keys_joined or 'operator' in keys_joined):
            print(f"\n  [{i}] State dict with r6+match/operator keys:")
            for k in sorted(item.keys()):
                if 'match' in k.lower() or 'operator' in k.lower() or 'round' in k.lower() or 'map' in k.lower():
                    v_idx = item[k]
                    print(f"    {k[:120]} -> idx {v_idx}")

# 4. 直接找包含 operators 字段 + match/round 的数据
print("\n" + "=" * 70)
print("4. Finding operator usage per match/round")
print("=" * 70)

# 从 NUXT 找 operator_positions, operator_sides, operators 引用的位置
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict):
        if 'operator_positions' in item or 'operators' in item or 'operator_sides' in item:
            print(f"\n  [{i}] Dict with operator fields:")
            for k, v in item.items():
                print(f"    {k}: {v}")
            
            # 解引用整个对象
            resolved = deref(nuxt, i, max_depth=15)
            print(f"\n  Resolved:")
            print(json.dumps(resolved, ensure_ascii=False, indent=2, default=str)[:2000])
            
            # 保存到文件
            with open('data/scraper/output/statscc_operator_data.json', 'w', encoding='utf-8') as f:
                json.dump(resolved, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n  Saved to statscc_operator_data.json")

# 5. 看看比赛历史数据中是否有 round-level operator
print("\n" + "=" * 70)
print("5. Match history - checking for round-level operators")
print("=" * 70)

matches = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
        match = deref(nuxt, i, max_depth=20)
        matches.append(match)

print(f"Found {len(matches)} matches")

# 详细查看第一场比赛
if matches:
    first = matches[0]
    print(f"\nFirst match full data:")
    print(json.dumps(first, ensure_ascii=False, indent=2, default=str))
    
    # 检查是否有 rounds 子数据
    for key in first:
        if 'round' in str(key).lower() or 'operator' in str(key).lower():
            print(f"\n  Key '{key}' found in match!")

# 6. 搜索 stats.cc 是否有单独的 match detail 页面
print("\n" + "=" * 70)
print("6. Checking for match detail pages on stats.cc")
print("=" * 70)

# 使用第一场比赛的ID
if matches:
    match_id = matches[0].get('id', '')
    test_urls = [
        f'https://stats.cc/siege/match/{match_id}',
        f'https://stats.cc/siege/matches/{match_id}',
        f'https://stats.cc/match/{match_id}',
    ]
    for url in test_urls:
        try:
            r2 = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            print(f"  {url}")
            print(f"    HTTP {r2.status_code}, {len(r2.text)} bytes")
            if r2.status_code == 200 and len(r2.text) > 1000:
                # 搜索干员数据
                for kw in ['operator', 'Ash', 'Jager', 'Thermite']:
                    count = r2.text.lower().count(kw.lower())
                    if count > 0:
                        print(f"    Found '{kw}': {count} times")
        except Exception as e:
            print(f"  {url} -> Error: {e}")

"""
解析 stats.cc 比赛详情页面 - 提取所有玩家每回合的干员选择
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

# 获取比赛详情页面
match_id = '5441e056-6d6c-4480-bbb5-6eec3b439cf3'
r = requests.get(f'https://stats.cc/siege/matches/{match_id}', headers=HEADERS, timeout=30)
print(f"Match detail page: HTTP {r.status_code}, {len(r.text)} bytes")

json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
if not json_blocks:
    print("No NUXT data found!")
    sys.exit(1)

nuxt = json.loads(json_blocks[0])
print(f"NUXT items: {len(nuxt)}")

# 1. 找到所有包含干员信息的 round 数据
print("\n" + "=" * 70)
print("1. Finding round data with operator info")
print("=" * 70)

# 搜索包含 operator 字段的 dict
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'operator' in item and 'outcome' in item:
        resolved = deref(nuxt, i, max_depth=12)
        print(f"\n  [{i}] Round data:")
        print(f"    {json.dumps(resolved, ensure_ascii=False, default=str)[:500]}")

# 2. 找主要的比赛数据
print("\n" + "=" * 70)
print("2. Main match data structure")
print("=" * 70)

# 找 pinia_colada state
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and len(item) > 3:
        keys_str = ' '.join(item.keys())
        if 'match' in keys_str.lower() and ('round' in keys_str or 'team' in keys_str or 'player' in keys_str):
            print(f"\n  [{i}] Match-like dict:")
            print(f"    Keys: {list(item.keys())[:20]}")
            resolved = deref(nuxt, i, max_depth=8)
            print(f"    Preview: {json.dumps(resolved, ensure_ascii=False, default=str)[:500]}")

# 3. 找包含 teams/players 的数据
print("\n" + "=" * 70)  
print("3. Looking for teams/players structure")
print("=" * 70)

for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict):
        keys = set(item.keys())
        if ('teams' in keys or 'players' in keys) and ('map' in keys or 'rounds' in keys or 'match' in keys):
            print(f"\n  [{i}] Teams/Players dict:")
            print(f"    Keys: {list(item.keys())}")

# 4. 逐项扫描 nuxt 找到关键结构
print("\n" + "=" * 70)
print("4. Scanning NUXT for key structures")
print("=" * 70)

# 找大的list（可能包含回合数据或玩家数据）
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, list) and len(item) > 5:
        # 检查列表中的第一个元素是否引用了 dict
        first_ref = item[0] if isinstance(item[0], int) else None
        if first_ref and first_ref < len(nuxt) and isinstance(nuxt[first_ref], dict):
            sample_keys = set(nuxt[first_ref].keys())
            if 'operator' in sample_keys or 'kills' in sample_keys or 'username' in sample_keys:
                print(f"\n  [{i}] List of {len(item)} items, first ref={first_ref}")
                print(f"    First item keys: {list(nuxt[first_ref].keys())[:15]}")
                # 解引用前3个
                for j in range(min(3, len(item))):
                    if isinstance(item[j], int):
                        r_item = deref(nuxt, item[j], max_depth=10)
                        print(f"    [{j}]: {json.dumps(r_item, ensure_ascii=False, default=str)[:300]}")

# 5. 找 rounds 数据（直接搜索包含 round number + operator 的数据）
print("\n" + "=" * 70)
print("5. Finding round-by-round operator data")
print("=" * 70)

# 搜索特定干员名在 nuxt 中的位置
for i in range(len(nuxt)):
    if nuxt[i] == 'ash' or nuxt[i] == 'Ash':
        # 看看周围的数据
        context_start = max(0, i-5)
        context_end = min(len(nuxt), i+5)
        print(f"\n  'ash' found at [{i}], context [{context_start}:{context_end}]:")
        for j in range(context_start, context_end):
            print(f"    [{j}] {repr(nuxt[j])[:150]}")
        break

# 6. 直接完整解引用根数据
print("\n" + "=" * 70)
print("6. Full match detail data")
print("=" * 70)

# nuxt[3] 通常是 pinia_colada 的 state root
root = nuxt[3] if len(nuxt) > 3 else None
if isinstance(root, dict):
    print(f"Root keys: {list(root.keys())[:20]}")
    for key in root.keys():
        if 'match' in key.lower():
            print(f"\n  Key: {key[:150]}")
            val_idx = root[key]
            if isinstance(val_idx, int):
                resolved = deref(nuxt, val_idx, max_depth=20)
                # 保存到文件
                filename = f'data/scraper/output/statscc_match_detail.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(resolved, f, ensure_ascii=False, indent=2, default=str)
                print(f"  Saved to {filename}")
                
                # 打印摘要
                if isinstance(resolved, dict):
                    print(f"  Type: dict, keys: {list(resolved.keys())[:20]}")
                    print(f"  Preview: {json.dumps(resolved, ensure_ascii=False, default=str)[:1000]}")
                elif isinstance(resolved, list):
                    print(f"  Type: list, length: {len(resolved)}")
                    if resolved:
                        print(f"  First: {json.dumps(resolved[0], ensure_ascii=False, default=str)[:500]}")
                else:
                    print(f"  Value: {repr(resolved)[:300]}")

# 7. 解引用 index 4 (constants 包含干员定义)
print("\n" + "=" * 70)
print("7. Constants with operator list (index 4)")
print("=" * 70)

if isinstance(nuxt[4], dict) and 'operators' in nuxt[4]:
    ops_idx = nuxt[4]['operators']
    if isinstance(ops_idx, int):
        ops_list = deref(nuxt, ops_idx, max_depth=10)
        if isinstance(ops_list, list):
            print(f"  Found {len(ops_list)} operators")
            for op in ops_list[:5]:
                if isinstance(op, dict):
                    print(f"    {op.get('name', 'N/A')} ({op.get('id', 'N/A')}, {op.get('side', 'N/A')})")

"""
深入解析 stats.cc 玩家页面中的地图统计数据结构
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

r = requests.get('https://stats.cc/siege/exolt2turNt/3bae0298-8f3f-4fe2-ac96-91e12d31d381', headers=headers, timeout=30)
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
nuxt = json.loads(json_blocks[0])

# 查看 index 3026 附近的完整结构（有 'map' key 的 dict）
print("=" * 70)
print("Examining map data entries (indices 3020-3180)")
print("=" * 70)

for i in range(3020, min(3180, len(nuxt))):
    item = nuxt[i]
    if isinstance(item, dict) and 'map' in item:
        print(f"\n  [{i}] dict keys: {list(item.keys())}")
        # 解引用所有值
        resolved = {}
        for k, v in item.items():
            if isinstance(v, int) and v < len(nuxt):
                resolved[k] = nuxt[v]
                # 如果引用的值也是 dict/int，再解一层
                if isinstance(nuxt[v], dict):
                    inner = {}
                    for ik, iv in nuxt[v].items():
                        if isinstance(iv, int) and iv < len(nuxt):
                            inner[ik] = nuxt[iv]
                        else:
                            inner[ik] = iv
                    resolved[k] = inner
            else:
                resolved[k] = v
        print(f"    Resolved: {json.dumps(resolved, ensure_ascii=False, default=str)[:500]}")

# 查看 pinia_colada 数据 (index 1765) 的完整结构
print("\n\n" + "=" * 70)
print("Examining pinia_colada maps data (index 1765)")
print("=" * 70)

item_1765 = nuxt[1765]
if isinstance(item_1765, dict):
    for k, v in item_1765.items():
        if 'map' in k.lower():
            print(f"\n  Key: {k[:100]}...")
            print(f"  Points to index: {v}")
            if isinstance(v, int) and v < len(nuxt):
                target = nuxt[v]
                print(f"  Target type: {type(target).__name__}")
                if isinstance(target, list):
                    print(f"  List length: {len(target)}")
                    for j, elem_idx in enumerate(target):
                        if isinstance(elem_idx, int) and elem_idx < len(nuxt):
                            elem = nuxt[elem_idx]
                            if isinstance(elem, dict):
                                print(f"    [{j}] keys: {list(elem.keys())[:10]}")
                            else:
                                print(f"    [{j}] {type(elem).__name__}: {repr(elem)[:100]}")
                        else:
                            print(f"    [{j}] {repr(elem_idx)[:100]}")
                elif isinstance(target, dict):
                    print(f"  Dict keys: {list(target.keys())[:15]}")
                else:
                    print(f"  Value: {repr(target)[:200]}")

# 查看 index 3179 (maps API 结果)
print("\n\n" + "=" * 70)
print("Examining maps API result (index 3179)")
print("=" * 70)

item_3179 = nuxt[3179]
print(f"Type: {type(item_3179).__name__}")
if isinstance(item_3179, list):
    print(f"Length: {len(item_3179)}")
    for j, elem_idx in enumerate(item_3179):
        if isinstance(elem_idx, int) and elem_idx < len(nuxt):
            elem = nuxt[elem_idx]
            if isinstance(elem, dict):
                # 解引用
                resolved = {}
                for k, v in elem.items():
                    if isinstance(v, int) and v < len(nuxt):
                        val = nuxt[v]
                        if isinstance(val, dict):
                            inner = {}
                            for ik, iv in val.items():
                                inner[ik] = nuxt[iv] if isinstance(iv, int) and iv < len(nuxt) else iv
                            resolved[k] = inner
                        elif isinstance(val, list):
                            resolved[k] = f"list[{len(val)}]"
                        else:
                            resolved[k] = val
                    else:
                        resolved[k] = v
                print(f"\n  [{j}] (idx={elem_idx}) keys: {list(elem.keys())[:15]}")
                print(f"    Resolved: {json.dumps(resolved, ensure_ascii=False, default=str)[:400]}")
            elif isinstance(elem, str):
                print(f"  [{j}] (idx={elem_idx}) str: '{elem[:80]}'")
            else:
                print(f"  [{j}] (idx={elem_idx}) {type(elem).__name__}: {repr(elem)[:100]}")
        else:
            print(f"  [{j}] raw: {repr(elem_idx)[:100]}")

# 查看 index 3185 (second maps query)
print("\n\n--- Index 3185 ---")
item_3185 = nuxt[3185]
print(f"Type: {type(item_3185).__name__}")
if isinstance(item_3185, list):
    print(f"Length: {len(item_3185)}")

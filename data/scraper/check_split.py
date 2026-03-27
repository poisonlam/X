"""
深入查看 operatorStats 的 split 字段，看是否包含地图数据
"""
import requests
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 获取 operatorStats 完整数据
r = requests.get('https://r6data.eu/api/stats', headers=headers, params={
    'type': 'operatorStats',
    'nameOnPlatform': 'Beaulo',
    'platformType': 'uplay',
    'modes': 'ranked',
}, timeout=30)

data = r.json()
print(f"Top keys: {list(data.keys())}")
print(f"Total JSON size: {len(json.dumps(data))} chars")

# 深入查看 split
split = data.get('split', None)
if split is not None:
    print(f"\nsplit type: {type(split).__name__}")
    if isinstance(split, dict):
        print(f"split keys: {list(split.keys())}")
        for k, v in split.items():
            if isinstance(v, dict):
                print(f"\n  {k}: dict keys={list(v.keys())[:15]}")
                # 看看子结构
                for sk, sv in list(v.items())[:3]:
                    print(f"    {sk}: {type(sv).__name__}")
                    if isinstance(sv, dict):
                        print(f"      keys: {list(sv.keys())[:15]}")
                        print(f"      preview: {json.dumps(sv, ensure_ascii=False)[:400]}")
                    elif isinstance(sv, list):
                        print(f"      len: {len(sv)}")
                        if sv:
                            print(f"      first: {json.dumps(sv[0], ensure_ascii=False)[:400]}")
                    else:
                        print(f"      value: {repr(sv)[:200]}")
            elif isinstance(v, list):
                print(f"\n  {k}: list[{len(v)}]")
                if v:
                    print(f"    first: {json.dumps(v[0], ensure_ascii=False)[:400]}")
            else:
                print(f"\n  {k}: {repr(v)[:200]}")
    elif isinstance(split, list):
        print(f"split length: {len(split)}")
        if split:
            first = split[0]
            print(f"first type: {type(first).__name__}")
            if isinstance(first, dict):
                print(f"first keys: {list(first.keys())}")
                print(f"first: {json.dumps(first, ensure_ascii=False)[:500]}")
    else:
        print(f"split value: {repr(split)[:500]}")
else:
    print("split is None")
    # 可能数据在别处，打印完整结构
    print("\n完整数据摘要:")
    def summarize(obj, prefix="", depth=0):
        if depth > 4:
            return
        if isinstance(obj, dict):
            for k, v in list(obj.items())[:20]:
                if isinstance(v, dict):
                    print(f"{prefix}{k}: dict[{len(v)} keys]")
                    summarize(v, prefix + "  ", depth + 1)
                elif isinstance(v, list):
                    print(f"{prefix}{k}: list[{len(v)}]")
                    if v and depth < 3:
                        summarize(v[0], prefix + "  [0].", depth + 1)
                else:
                    val_str = repr(v)[:80]
                    print(f"{prefix}{k}: {val_str}")
        elif isinstance(obj, list):
            if obj:
                summarize(obj[0], prefix + "[0].", depth + 1)
    summarize(data)

# 也试试 stats (段位数据)，看看是否有地图信息
print("\n\n" + "=" * 70)
print("Checking 'stats' type for map data")
print("=" * 70)

r2 = requests.get('https://r6data.eu/api/stats', headers=headers, params={
    'type': 'stats',
    'nameOnPlatform': 'Beaulo',
    'platformType': 'uplay',
    'platform_families': 'pc',
}, timeout=30)

data2 = r2.json()
print(f"stats keys: {list(data2.keys()) if isinstance(data2, dict) else type(data2).__name__}")

# 保存完整数据供分析
with open('data/scraper/output/beaulo_operatorStats_full.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nSaved full operatorStats: {len(json.dumps(data))} chars")

with open('data/scraper/output/beaulo_stats_full.json', 'w', encoding='utf-8') as f:
    json.dump(data2, f, ensure_ascii=False, indent=2)
print(f"Saved full stats: {len(json.dumps(data2))} chars")

# 搜索整个 operatorStats JSON 中是否有地图名称
print("\n\n--- Searching for map names in operatorStats ---")
text = json.dumps(data)
map_names = ['Oregon', 'Clubhouse', 'Coastline', 'Kafe', 'Bank', 'Chalet', 'Theme Park', 'Border', 'Consulate', 'Villa', 'Outback', 'Emerald Plains', 'Nighthaven', 'Lair']
for name in map_names:
    if name.lower() in text.lower():
        idx = text.lower().find(name.lower())
        print(f"  FOUND '{name}' at pos {idx}: ...{text[max(0,idx-50):idx+100]}...")
    
print("\n--- Searching for map names in stats ---")
text2 = json.dumps(data2)
for name in map_names:
    if name.lower() in text2.lower():
        idx = text2.lower().find(name.lower())
        print(f"  FOUND '{name}' at pos {idx}: ...{text2[max(0,idx-50):idx+100]}...")

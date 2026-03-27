"""
查看 r6data.eu 前端在玩家个人页面上展示的地图统计数据来源
以及 stats.cc 玩家页面是否有地图数据
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}

# =========================================
# Part 1: 搜索 r6data.eu JS 中的地图统计相关代码
# =========================================
print("=" * 70)
print("Part 1: Deep search in ALL r6data.eu JS files for map stats")
print("=" * 70)

# 获取主页列出所有JS
r = requests.get('https://r6data.eu/', headers=headers, timeout=15)
js_files = re.findall(r'<script[^>]*src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
dist_files = [f for f in js_files if '/dist/' in f]
print(f"Found {len(dist_files)} dist JS files")

for path in dist_files:
    url = f'https://r6data.eu{path}'
    try:
        r2 = requests.get(url, headers=headers, timeout=10)
        if r2.status_code != 200:
            continue
        text = r2.text
        # 搜索 map 相关的数据加载
        for kw in ['mapStats', 'map_stats', 'mapBan', 'map_ban', 'operatorMap', 'operator_map', 
                    'mapWinRate', 'map_win_rate', 'mapKd', 'map_kd', 
                    'byMap', 'by_map', 'perMap', 'per_map',
                    'Oregon', 'Clubhouse', 'Coastline']:
            if kw in text:
                idx = text.find(kw)
                ctx = text[max(0,idx-150):idx+200].replace('\n', ' ')
                print(f"\n  {path} [{kw}]: ...{ctx}...")
    except:
        pass

# =========================================
# Part 2: 检查 stats.cc 玩家个人页面是否有地图数据
# =========================================
print("\n\n" + "=" * 70)
print("Part 2: Checking stats.cc player page for map data")
print("=" * 70)

# 从我们之前获取的排行榜数据中取一个玩家
player_url = 'https://stats.cc/siege/Beaulo/3cc51897-49c4-45f6-af9d-66507b8ef0e1'
r = requests.get(player_url, headers=headers, timeout=30)
print(f"Player page: HTTP {r.status_code}, {len(r.text)} bytes")

if r.status_code == 200:
    # 搜索地图名称
    text = r.text
    map_names = ['Oregon', 'Clubhouse', 'Coastline', 'Kafe', 'Bank', 'Chalet', 
                 'Theme Park', 'Border', 'Consulate', 'Villa', 'Outback', 
                 'Emerald Plains', 'Nighthaven', 'Lair', 'Close Quarter']
    print("\nSearching for map names:")
    for name in map_names:
        count = text.lower().count(name.lower())
        if count > 0:
            idx = text.lower().find(name.lower())
            ctx = text[max(0,idx-30):idx+50]
            print(f"  {name}: {count} times, first: ...{ctx}...")
    
    # 检查 NUXT data
    json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', text, re.DOTALL)
    if json_blocks:
        nuxt = json_blocks[0]
        print(f"\nNUXT data: {len(nuxt)} chars")
        for name in map_names:
            if name.lower() in nuxt.lower():
                idx = nuxt.lower().find(name.lower())
                print(f"  NUXT has {name}: ...{nuxt[max(0,idx-50):idx+100]}...")

# 也尝试 exolt2turNt (排行榜第1)
player_url2 = 'https://stats.cc/siege/exolt2turNt/3bae0298-8f3f-4fe2-ac96-91e12d31d381'
r2 = requests.get(player_url2, headers=headers, timeout=30)
print(f"\nTop player page: HTTP {r2.status_code}, {len(r2.text)} bytes")
if r2.status_code == 200:
    for name in ['Oregon', 'Clubhouse', 'mapStats', 'maps']:
        count = r2.text.lower().count(name.lower())
        print(f"  {name}: {count} occurrences")

# =========================================
# Part 3: 查看 r6data.eu 已有的项目数据文件中的地图统计
# =========================================
print("\n\n" + "=" * 70)
print("Part 3: Existing operator_map_stats in project")
print("=" * 70)

# 之前项目中有 operator_map_stats.js
try:
    with open('data/operator_map_stats.js', 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"operator_map_stats.js: {len(content)} chars")
    print(f"First 500 chars: {content[:500]}")
except Exception as e:
    print(f"Error: {e}")

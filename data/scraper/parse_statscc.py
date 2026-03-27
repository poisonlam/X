"""
解析 stats.cc 排行榜页面数据 + 探索 api.stats.cc
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
# Part 1: 解析 stats.cc 排行榜 HTML
# =========================================
print("=" * 70)
print("Part 1: Parsing stats.cc leaderboard HTML (423KB)")
print("=" * 70)

url = 'https://stats.cc/siege/leaderboards/pc/ranked/rankPoints'
r = requests.get(url, headers=headers, timeout=30)
print(f"HTTP {r.status_code}, Length: {len(r.text)} bytes")

text = r.text

# 1. 搜索 __NUXT__ 或 __NEXT_DATA__ 之类的 SSR 数据
ssr_patterns = [
    (r'window\.__NUXT__\s*=\s*', '__NUXT__'),
    (r'__NEXT_DATA__\s*=\s*', '__NEXT_DATA__'),
    (r'window\.__DATA__\s*=\s*', '__DATA__'),
    (r'<script id="__NUXT_DATA__"[^>]*>', '__NUXT_DATA__'),
]

for pattern, label in ssr_patterns:
    matches = list(re.finditer(pattern, text))
    if matches:
        print(f"\n[FOUND] {label} at position {matches[0].start()}")
        # 提取数据
        start = matches[0].end()
        # 尝试找到闭合的 </script>
        end = text.find('</script>', start)
        if end > 0:
            data_str = text[start:end]
            print(f"  Data length: {len(data_str)} chars")
            print(f"  First 500 chars: {data_str[:500]}")
            print(f"  Last 200 chars: ...{data_str[-200:]}")
        else:
            print(f"  Could not find end of script tag")

# 2. 搜索 JSON 数据块
print("\n\n--- Searching for embedded JSON data ---")
json_pattern = r'<script[^>]*type="application/json"[^>]*>(.*?)</script>'
json_blocks = re.findall(json_pattern, text, re.DOTALL)
print(f"Found {len(json_blocks)} JSON script blocks")
for i, block in enumerate(json_blocks):
    print(f"\n  Block {i}: {len(block)} chars")
    print(f"  Preview: {block[:300]}")

# 3. 搜索玩家名模式（排行榜应该有玩家名）
print("\n\n--- Searching for player data patterns ---")
# 找 champion/diamond 等段位关键字
for kw in ['Champion', 'Diamond', 'Emerald', 'Platinum', 'rankPoints', 'profile_id', 'nameOnPlatform']:
    count = text.lower().count(kw.lower())
    if count > 0:
        idx = text.lower().find(kw.lower())
        ctx = text[max(0, idx-50):idx+100]
        print(f"  {kw}: {count} occurrences, first at: ...{ctx}...")

# 4. 提取所有 <a> 标签中包含玩家链接的模式
player_links = re.findall(r'href="(/siege/[^/]+/pc)"', text)
if not player_links:
    player_links = re.findall(r'href="(/siege/[^"]+)"', text)
print(f"\n  Player-like links: {len(player_links)} total")
if player_links:
    unique_links = list(set(player_links))[:20]
    for link in sorted(unique_links):
        print(f"    {link}")

# 5. 搜索表格或列表结构
print("\n\n--- HTML structure analysis ---")
# 查找所有 script src
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', text)
print(f"External scripts: {len(scripts)}")
for s in scripts[:10]:
    print(f"  {s}")

# =========================================
# Part 2: 探索 api.stats.cc
# =========================================
print("\n\n" + "=" * 70)
print("Part 2: Exploring api.stats.cc")
print("=" * 70)

api_tests = [
    'https://api.stats.cc/v1/siege/leaderboards/pc/ranked/rankPoints',
    'https://api.stats.cc/v2/siege/leaderboards/pc/ranked/rankPoints',
    'https://api.stats.cc/v1/siege/leaderboard/pc/ranked/rankPoints',
    'https://api.stats.cc/v1/siege/player/Beaulo',
    'https://api.stats.cc/v2/siege/player/Beaulo',
    'https://api.stats.cc/',
    'https://api.stats.cc/v1/',
    'https://api.stats.cc/v2/',
]

for url in api_tests:
    try:
        r = requests.get(url, headers={'User-Agent': headers['User-Agent'], 'Accept': 'application/json'}, timeout=10)
        print(f"\n  {url}")
        print(f"  HTTP {r.status_code}, Len={len(r.text)}")
        content = r.text[:300]
        print(f"  Content: {content}")
    except Exception as e:
        print(f"\n  {url} -> Error: {e}")

# =========================================  
# Part 3: 查看 stats.cc 页面的 JS bundle 中的 API 调用
# =========================================
print("\n\n" + "=" * 70)
print("Part 3: Analyzing stats.cc JS bundles for API calls")
print("=" * 70)

# 从 stats.cc 页面中提取 JS 文件
r = requests.get('https://stats.cc/siege/leaderboards/pc/ranked/rankPoints', headers=headers, timeout=30)
js_files = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', r.text)
# 只看 stats.cc 自己的 JS
own_js = [f for f in js_files if 'stats.cc' in f or f.startswith('/') or f.startswith('_')]
print(f"Own JS files: {len(own_js)}")
for f in own_js:
    print(f"  {f}")

# 下载前几个JS查找API调用
for path in own_js[:5]:
    url = path if path.startswith('http') else f'https://stats.cc{path}'
    try:
        r2 = requests.get(url, headers=headers, timeout=10)
        if r2.status_code == 200:
            # 搜索 API 调用
            api_refs = re.findall(r'["\'](?:https?://[^"\']*api[^"\']*|/api/[^"\']+)["\']', r2.text)
            fetch_refs = re.findall(r'fetch\(["\']([^"\']+)["\']', r2.text)
            if api_refs or fetch_refs:
                print(f"\n  --- {path} ({len(r2.text)} bytes) ---")
                for a in sorted(set(api_refs))[:10]:
                    print(f"    [API ref] {a}")
                for f in sorted(set(fetch_refs))[:10]:
                    print(f"    [fetch] {f}")
    except:
        pass

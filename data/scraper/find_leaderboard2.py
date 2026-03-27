"""
深入分析 r6data.eu 前端JS中的排行榜相关代码，
同时测试 stats.cc 排行榜 API
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}

# =========================================
# Part 1: 深入分析 r6data.eu 前端 JS
# =========================================
print("=" * 70)
print("Part 1: Deep analysis of r6data.eu JS files for leaderboard logic")
print("=" * 70)

# 下载 leaderboard 页面，找到它使用的JS chunk
r = requests.get('https://r6data.eu/leaderboard', headers=headers, timeout=15)
print(f"Leaderboard page: HTTP {r.status_code}, {len(r.text)} bytes")

# 提取所有 script src
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', r.text)
print(f"Script tags: {len(scripts)}")

# 找到所有 dist/ JS 文件
dist_files = [s for s in scripts if '/dist/' in s]
print(f"Dist JS files: {len(dist_files)}")

# 下载每一个 dist JS 文件，搜索任何跟 leaderboard/ranking/top 相关的逻辑
for path in dist_files:
    url = path if path.startswith('http') else f'https://r6data.eu{path}'
    try:
        r2 = requests.get(url, headers=headers, timeout=10)
        if r2.status_code != 200:
            continue
        text = r2.text
        # 检查是否包含排行榜相关的路由或API
        patterns = [
            (r'leaderboard', 'leaderboard'),
            (r'/api/leaderboard', '/api/leaderboard'),
            (r'ranking', 'ranking'),
            (r'topPlayer', 'topPlayer'),
            (r'boardType', 'boardType'),
            (r'mmr', 'mmr (case sensitive)'),
        ]
        found_any = False
        for pattern, label in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches and 'mmr' != label:  # skip mmr noise
                if not found_any:
                    print(f"\n--- {path} ({len(text)} bytes) ---")
                    found_any = True
                for m in matches[:3]:
                    start = max(0, m.start() - 80)
                    end = min(len(text), m.end() + 120)
                    ctx = text[start:end].replace('\n', ' ').replace('\r', '')
                    print(f"  [{label}] ...{ctx}...")
    except:
        pass

# =========================================
# Part 2: 测试 stats.cc 排行榜
# =========================================
print("\n\n" + "=" * 70)
print("Part 2: Testing stats.cc leaderboard")
print("=" * 70)

# 尝试直接访问 stats.cc 的排行榜页面和API
test_urls = [
    ('stats.cc leaderboard page (PC)', 'https://stats.cc/siege/leaderboards/pc/ranked/rankPoints'),
    ('stats.cc leaderboard page (global)', 'https://stats.cc/siege/leaderboards/global/ranked/rankPoints'),
    ('stats.cc API attempt 1', 'https://stats.cc/api/siege/leaderboards/pc/ranked/rankPoints'),
    ('stats.cc API attempt 2', 'https://api.stats.cc/siege/leaderboards/pc/ranked/rankPoints'),
]

for label, url in test_urls:
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"\n{label}")
        print(f"  URL: {url}")
        print(f"  HTTP {r.status_code}, Length: {len(r.text)}")
        if r.status_code == 200:
            # 检查是否为JSON
            try:
                data = r.json()
                print(f"  [JSON] Keys: {list(data.keys()) if isinstance(data, dict) else f'Array of {len(data)}'}")
                print(f"  First 300 chars: {json.dumps(data, ensure_ascii=False)[:300]}")
            except:
                # HTML - 搜索 API 端点
                api_matches = re.findall(r'(?:fetch|axios|get|post)\s*\(["\']([^"\']+)["\']', r.text)
                api_paths = re.findall(r'["\'](/api/[^"\']+)["\']', r.text)
                print(f"  [HTML] Fetch calls: {api_matches[:5]}")
                print(f"  [HTML] API paths: {api_paths[:5]}")
                # 搜索 leaderboard 相关 JS 逻辑
                lb_matches = re.findall(r'leaderboard[^"\']{0,200}', r.text, re.IGNORECASE)
                for m in lb_matches[:3]:
                    print(f"  [HTML] leaderboard ref: ...{m[:150]}...")
        else:
            print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"\n{label} -> Error: {e}")

# =========================================
# Part 3: 测试 r6data.eu 是否有通过 Ubisoft API 的排行榜
# =========================================
print("\n\n" + "=" * 70)
print("Part 3: Additional r6data.eu endpoint tests")
print("=" * 70)

# r6data.eu 的 API 文档提到了一些端点，看看有没有 leaderboard 相关的
more_endpoints = [
    '/api/stats?type=topPlayers&platform_families=pc',
    '/api/stats?type=leaderboard&platform_families=pc',
    '/api/top',
    '/api/top?platform=pc',
    '/api/players/top',
    '/api/players?sort=rank&limit=100',
]

for endpoint in more_endpoints:
    url = f'https://r6data.eu{endpoint}'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  {endpoint} -> HTTP {r.status_code}, Len={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 10:
            print(f"    Content: {r.text[:200]}")
    except Exception as e:
        print(f"  {endpoint} -> Error: {e}")

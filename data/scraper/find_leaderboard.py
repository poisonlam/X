"""
搜索 r6data.eu 前端JS文件中的排行榜(leaderboard)相关 API 端点
"""
import requests
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. 先获取主页面找到所有JS文件
print("=== Step 1: Finding all JS files ===")
r = requests.get('https://r6data.eu/', headers=headers, timeout=15)
js_files = re.findall(r'(?:src|href)=["\']([^"\']*\.js[^"\']*)["\']', r.text)
print(f"Found {len(js_files)} JS files on main page")

# 也检查 leaderboard 页面
for page in ['/leaderboard', '/leaderboards', '/rankings']:
    try:
        r2 = requests.get(f'https://r6data.eu{page}', headers=headers, timeout=10)
        if r2.status_code == 200:
            more_js = re.findall(r'(?:src|href)=["\']([^"\']*\.js[^"\']*)["\']', r2.text)
            js_files.extend(more_js)
            print(f"  Page {page}: HTTP {r2.status_code}, found {len(more_js)} more JS files")
    except:
        pass

js_files = list(set(js_files))
print(f"Total unique JS files: {len(js_files)}")
for f in sorted(js_files):
    print(f"  {f}")

# 2. 在每个JS文件中搜索 leaderboard 相关的API
print("\n=== Step 2: Searching for leaderboard-related API endpoints ===")
keywords = ['leaderboard', 'ranking', 'top_players', 'topPlayers', 'top-players', 'leaders']
all_apis = set()

for path in js_files:
    url = path if path.startswith('http') else f'https://r6data.eu{path}'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            continue
        
        text = r.text
        # 搜索排行榜关键字
        found_keywords = False
        for kw in keywords:
            if kw.lower() in text.lower():
                if not found_keywords:
                    print(f"\n--- {path} ({len(text)} bytes) ---")
                    found_keywords = True
                # 找到关键字附近的上下文
                for m in re.finditer(kw, text, re.IGNORECASE):
                    start = max(0, m.start() - 100)
                    end = min(len(text), m.end() + 100)
                    ctx = text[start:end].replace('\n', ' ')
                    print(f"  [{kw}] ...{ctx}...")
        
        # 搜索所有 /api/ 相关的路径
        api_paths = re.findall(r'["`\'](/api/[^"`\']+)["`\']', text)
        template_apis = re.findall(r'`([^`]*/api/[^`]*)`', text)
        all_found = set(api_paths + template_apis)
        for a in all_found:
            if any(kw in a.lower() for kw in keywords):
                print(f"  [API] {a}")
                all_apis.add(a)
    except Exception as e:
        pass

# 3. 直接测试一些可能的排行榜端点
print("\n\n=== Step 3: Testing possible leaderboard endpoints ===")
test_endpoints = [
    '/api/leaderboard',
    '/api/leaderboards',
    '/api/leaderboard?platform=pc',
    '/api/leaderboard?platform=pc&region=emea',
    '/api/rankings',
    '/api/ranking',
    '/api/top-players',
    '/api/topPlayers',
    '/api/stats?type=leaderboard',
    '/api/stats?type=rankings',
    '/api/stats?type=topPlayers',
    '/api/stats?type=leaderboard&platform=pc',
    '/api/leaderboard?type=ranked',
    '/api/leaderboard?type=ranked&platform=pc',
    '/api/leaderboard?boardId=ranked&platform=pc',
    '/api/leaderboard?region=global&board=ranked',
]

for endpoint in test_endpoints:
    url = f'https://r6data.eu{endpoint}'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        content = r.text[:300] if r.status_code == 200 else r.text[:150]
        status = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
        print(f"  {endpoint}")
        print(f"    [{status}] Len={len(r.text)} Content: {content}")
        print()
    except Exception as e:
        print(f"  {endpoint} -> Error: {e}")
        print()

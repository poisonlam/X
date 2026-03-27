"""测试 stats.cc 的替代 API 路径"""
import requests
import json
import re
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

# Test 1: 用 profile ID 而不是用户名
print("=" * 60)
print("测试不同 URL 格式")
print("=" * 60)

test_urls = [
    # Standard player page
    'https://stats.cc/siege/pengu/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e',
    # Try matches sub-path
    'https://stats.cc/siege/pengu/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e/matches',
    # Try API endpoint
    'https://stats.cc/api/siege/pengu/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e',
    # Try without profile ID
    'https://stats.cc/siege/pengu',
    # Try internal API format
    'https://stats.cc/_nuxt/api/siege/profile/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e',
]

for url in test_urls:
    try:
        r = s.get(url, timeout=10, allow_redirects=True)
        print(f"\n  {url}")
        print(f"    Status: {r.status_code}, Size: {len(r.text)}, Final URL: {r.url[:80]}")
        
        if r.status_code == 200:
            # Check nuxt data
            json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if json_blocks:
                nuxt = json.loads(json_blocks[0])
                match_count = 0
                for i in range(len(nuxt)):
                    item = nuxt[i]
                    if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
                        match_count += 1
                print(f"    Nuxt items: {len(nuxt)}, Match items: {match_count}")
            elif r.headers.get('content-type', '').startswith('application/json'):
                data = r.json()
                print(f"    JSON response: {str(data)[:200]}")
    except Exception as e:
        print(f"\n  {url}")
        print(f"    ERROR: {e}")
    time.sleep(1)

# Test 2: 直接通过 stats.cc 的 Nuxt API 获取数据
print("\n" + "=" * 60)
print("测试 Nuxt SSR API")
print("=" * 60)

# Nuxt 3 typically has __nuxt_island__ or __nuxt_data__ endpoints
nuxt_urls = [
    'https://stats.cc/_payload.json',
    'https://stats.cc/api/siege/profile/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e',
    'https://stats.cc/api/v1/siege/profile/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e',
]

for url in nuxt_urls:
    try:
        r = s.get(url, timeout=10, allow_redirects=True)
        print(f"\n  {url}")
        print(f"    Status: {r.status_code}, Size: {len(r.text)}")
        if r.status_code == 200:
            ct = r.headers.get('content-type', '')
            print(f"    Content-Type: {ct}")
            if 'json' in ct:
                print(f"    Data: {r.text[:300]}")
    except Exception as e:
        print(f"\n  {url}")
        print(f"    ERROR: {e}")
    time.sleep(0.5)

# Test 3: Try a different player to confirm it's global, not player-specific
print("\n" + "=" * 60)
print("测试不同玩家确认是全局问题")
print("=" * 60)

# Get a player from our progress file
import os
progress_file = os.path.join('output', 'match_data', '_shard_0_progress.json')
if os.path.exists(progress_file):
    with open(progress_file, 'r', encoding='utf-8') as f:
        prog = json.load(f)
    completed = prog.get('completed_players', [])
    if completed:
        pid = completed[-1]
        # We need to find the display name. Try leaderboard file
        lb_file = os.path.join('output', 'leaderboard', 'leaderboard_full.json')
        if os.path.exists(lb_file):
            with open(lb_file, 'r', encoding='utf-8') as f:
                lb = json.load(f)
            for p in lb:
                if p['profileId'] == pid:
                    name = p['displayName']
                    url = f'https://stats.cc/siege/{name}/{pid}'
                    r = s.get(url, timeout=15)
                    print(f"  {name}: Status={r.status_code}, Size={len(r.text)}")
                    
                    nuxt = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
                    if nuxt:
                        data = json.loads(nuxt[0])
                        match_items = sum(1 for i in range(len(data)) if isinstance(data[i], dict) and 'map' in data[i] and 'playlist' in data[i] and 'scores' in data[i])
                        # Check for error
                        for i in range(len(data)):
                            if isinstance(data[i], str) and 'error' in data[i].lower():
                                print(f"    Error string: {data[i]}")
                        print(f"    Match items: {match_items}")
                    break

print("\n完成")

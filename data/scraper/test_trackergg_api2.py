"""
用多种方式尝试访问 tracker.gg API
"""
import requests
import sys
import io
import json
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 方法1: 模拟完整的浏览器请求（包含TRN header）
HEADERS_V1 = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Origin': 'https://r6.tracker.network',
    'Referer': 'https://r6.tracker.network/',
    'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
}

# 方法2: 不同的 API base
API_URLS = [
    'https://api.tracker.gg/api/v2/r6siege/standard/matches/uplay/Beaulo',
    'https://public-api.tracker.gg/v2/r6siege/standard/matches/uplay/Beaulo',
    'https://r6.tracker.network/api/v1/matches/uplay/Beaulo',
    'https://r6.tracker.network/r6siege/profile/uplay/Beaulo/matches?__json',
]

for url in API_URLS:
    print(f"\n--- {url} ---")
    try:
        r = requests.get(url, headers=HEADERS_V1, timeout=15)
        print(f"  HTTP {r.status_code}, {len(r.text)} bytes")
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  JSON keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
                with open('data/scraper/output/trackergg_matches_sample.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print("  *** SUCCESS! Saved data ***")
            except:
                print(f"  Not JSON: {r.text[:200]}")
        else:
            ct = r.headers.get('Content-Type', '')
            print(f"  Content-Type: {ct}")
            if 'json' in ct.lower():
                try:
                    err = r.json()
                    print(f"  Error: {json.dumps(err, ensure_ascii=False)[:300]}")
                except:
                    pass
            else:
                print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(1)

# 方法3: 使用 session 先获取cookie
print(f"\n\n{'='*70}")
print("Method 3: Session-based approach")
print("="*70)

session = requests.Session()
session.headers.update(HEADERS_V1)

# 先访问网站主页获取cookies
try:
    r0 = session.get('https://r6.tracker.network/', timeout=15, allow_redirects=True)
    print(f"Homepage: HTTP {r0.status_code}, cookies: {dict(session.cookies)}")
except Exception as e:
    print(f"Homepage error: {e}")

time.sleep(2)

# 然后请求API
try:
    r1 = session.get('https://api.tracker.gg/api/v2/r6siege/standard/matches/uplay/Beaulo', timeout=15)
    print(f"API: HTTP {r1.status_code}, {len(r1.text)} bytes")
    if r1.status_code == 200:
        data = r1.json()
        print(f"  *** SUCCESS! ***")
        with open('data/scraper/output/trackergg_matches_sample.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print(f"  {r1.text[:300]}")
except Exception as e:
    print(f"API error: {e}")

# 方法4: 回到 stats.cc，看看对局详情页面是否有干员信息
print(f"\n\n{'='*70}")
print("Method 4: Check stats.cc match detail for operator info")
print("="*70)

# stats.cc 玩家页面已知包含比赛历史，看看是否也有干员数据
r = requests.get('https://stats.cc/siege/exolt2turNt/3bae0298-8f3f-4fe2-ac96-91e12d31d381', 
                  headers={'User-Agent': HEADERS_V1['User-Agent']}, timeout=30)
print(f"stats.cc player page: HTTP {r.status_code}, {len(r.text)} bytes")

import re
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
if json_blocks:
    nuxt = json.loads(json_blocks[0])
    print(f"NUXT data: {len(nuxt)} items")
    
    # 搜索干员相关关键字
    nuxt_str = json.dumps(nuxt)
    operator_keywords = ['operatorName', 'operator_name', 'operatorId', 'operator_id', 
                          'operatorSide', 'operator_side', 'operatorPick', 'operator_pick']
    for kw in operator_keywords:
        if kw in nuxt_str:
            idx = nuxt_str.find(kw)
            print(f"  FOUND '{kw}' at pos {idx}: ...{nuxt_str[max(0,idx-30):idx+80]}...")
    
    # 搜索具体干员名称（可能以不同格式出现）
    op_names = ['ash', 'jager', 'thermite', 'sledge', 'bandit', 'mute', 'doc', 'rook',
                'valkyrie', 'hibana', 'vigil', 'maverick', 'kali', 'ace', 'flores']
    found_ops = []
    for op in op_names:
        # 只搜索作为独立值的干员名，不是URL的一部分
        count = nuxt_str.lower().count(f'"{op}"')
        if count > 0:
            found_ops.append((op, count))
    
    if found_ops:
        print(f"\n  Operator names found as values:")
        for op, c in sorted(found_ops, key=lambda x: -x[1]):
            print(f"    {op}: {c} times")
    else:
        print(f"\n  No operator names found as standalone values")
    
    # 看看 NUXT data 中有没有 match 详情页面的链接格式
    match_patterns = ['match/', 'match-detail', 'matchDetail', '/matches/']
    for pat in match_patterns:
        if pat in nuxt_str:
            idx = nuxt_str.find(pat)
            print(f"\n  Match URL pattern '{pat}': ...{nuxt_str[max(0,idx-50):idx+100]}...")

# 方法5: 尝试 stats.cc 的 r6.stats.cc API（之前返回401，看看是否有其他端点）
print(f"\n\n{'='*70}")
print("Method 5: Explore r6.stats.cc API endpoints")
print("="*70)

api_endpoints = [
    '/matches?profileId=3bae0298-8f3f-4fe2-ac96-91e12d31d381&playlist=ranked',
    '/matches/3bae0298-8f3f-4fe2-ac96-91e12d31d381',
    '/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381/matches',
    '/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381/matches?playlist=ranked',
    '/match/5441e056-6d6c-4480-bbb5-6eec3b439cf3',  # 从之前的数据获得的match id
]

for endpoint in api_endpoints:
    url = f'https://r6.stats.cc{endpoint}'
    try:
        r = requests.get(url, headers={'User-Agent': HEADERS_V1['User-Agent'], 'Accept': 'application/json'}, timeout=10)
        print(f"\n  {endpoint}")
        print(f"    HTTP {r.status_code}, {len(r.text)} bytes")
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"    JSON: {json.dumps(data, ensure_ascii=False)[:300]}")
            except:
                print(f"    Not JSON: {r.text[:200]}")
        elif r.status_code != 401:
            print(f"    Response: {r.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")

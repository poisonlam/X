"""
深入分析 r6data.eu 前端JS文件，找到所有内部API端点
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 需要分析的关键JS文件（含 /api/ 调用的）
key_files = [
    '/js/components/searchBar.js',
    '/dist/046f749148dd.js',  # AuthApi
    '/dist/d049bc0ae957.js',  # 最大的dist文件
    '/dist/ab11f4873395.js',
    '/dist/82e211a853bb.js',
    '/dist/4dee0955c127.js',
    '/dist/e3814b04fdc8.js',
    '/dist/b42a09afa128.js',
    '/dist/06ea59ada57b.js',
    '/dist/7f781d51eaf3.js',
    '/dist/7100bb4c476c.js',
    '/dist/eb76ddb849d8.js',
    '/dist/5b6ff4b4eb08.js',
    '/dist/aafca549d343.js',
    '/dist/32dbc9f68894.js',
    '/dist/4b4709a32ba5.js',
]

all_apis = set()

for path in key_files:
    url = f'https://r6data.eu{path}'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            continue
        # 找到所有 fetch 调用中的 URL
        fetches = re.findall(r'fetch\(["`\']([^"`\']+)["`\']', r.text)
        # 找到所有 /api/ 路径
        api_paths = re.findall(r'["`\'](/api/[^"`\']+)["`\']', r.text)
        # 找到所有模板字符串中的 /api/
        template_apis = re.findall(r'`([^`]*/api/[^`]*)`', r.text)
        
        found = set(fetches + api_paths + template_apis)
        if found:
            print(f"\n=== {path} ({len(r.text)} bytes) ===")
            for f in sorted(found):
                print(f"  {f}")
                all_apis.add(f)
    except Exception as e:
        print(f"  Error loading {path}: {e}")

print(f"\n\n=== ALL UNIQUE API ENDPOINTS FOUND ({len(all_apis)}) ===")
for a in sorted(all_apis):
    print(f"  {a}")

# 现在测试关键端点
print("\n\n=== TESTING KEY ENDPOINTS ===")
test_endpoints = [
    '/api/search?q=ash',
    '/api/search?q=Beaulo',
    '/api/operators',
    '/api/maps',
    '/api/weapons',
    '/api/seasons',
    '/api/ranks?version=v6',
    '/api/stats?type=accountInfo&nameOnPlatform=Beaulo&platformType=uplay',
    '/api/stats?type=stats&nameOnPlatform=Beaulo&platformType=uplay&platform_families=pc',
    '/api/stats?type=operatorStats&nameOnPlatform=Beaulo&platformType=uplay',
]

for endpoint in test_endpoints:
    url = f'https://r6data.eu{endpoint}'
    try:
        r = requests.get(url, headers=headers, timeout=15)
        content = r.text[:200] if r.status_code == 200 else r.text[:100]
        print(f"\n  {endpoint}")
        print(f"    HTTP {r.status_code}, Len={len(r.text)}")
        print(f"    Content: {content}")
    except Exception as e:
        print(f"\n  {endpoint} -> Error: {e}")

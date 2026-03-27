"""
分析 r6data.eu 前端页面，寻找内置的 API 调用逻辑和 API Key
"""
import requests
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. 获取主页面
print("=== 1. Fetching r6data.eu player page ===")
r = requests.get('https://r6data.eu/players/Beaulo', headers=headers)
print(f"HTTP {r.status_code}, Length: {len(r.text)}")

# 2. 找到所有JS文件引用
js_files = re.findall(r'src="([^"]*\.js[^"]*)"', r.text)
print(f"\n=== 2. JS files found: {len(js_files)} ===")
for f in js_files:
    print(f"  {f}")

# 3. 下载每个JS文件，搜索api相关内容
for js_url in js_files:
    if not js_url.startswith('http'):
        js_url = 'https://r6data.eu' + js_url if js_url.startswith('/') else 'https://r6data.eu/' + js_url
    print(f"\n=== Checking: {js_url} ===")
    try:
        jr = requests.get(js_url, headers=headers, timeout=10)
        print(f"  HTTP {jr.status_code}, Length: {len(jr.text)}")
        # 搜索关键字
        for kw in ['api-key', 'apiKey', 'api_key', '/api/', 'api.r6data', 'fetch(', 'axios']:
            positions = [m.start() for m in re.finditer(re.escape(kw), jr.text)]
            if positions:
                print(f"  FOUND '{kw}' at {len(positions)} locations!")
                for pos in positions[:3]:
                    ctx = jr.text[max(0,pos-60):pos+80].replace('\n', ' ')
                    print(f"    ...{ctx}...")
    except Exception as e:
        print(f"  Error: {e}")

# 4. 也检查 r6data.eu 的搜索接口
print("\n\n=== 4. Testing r6data.eu search/lookup endpoints ===")
test_urls = [
    'https://r6data.eu/api/search?q=Beaulo',
    'https://r6data.eu/search?q=Beaulo', 
    'https://r6data.eu/player/Beaulo',
    'https://r6data.eu/players/Beaulo/stats',
]
for url in test_urls:
    try:
        tr = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        print(f"  {url} -> HTTP {tr.status_code}, Len={len(tr.text)}")
        if tr.status_code == 200 and len(tr.text) < 1000:
            print(f"    Content: {tr.text[:200]}")
    except Exception as e:
        print(f"  {url} -> Error: {e}")

# 5. 尝试不带 api-key 但带其他 header 访问 API
print("\n\n=== 5. Testing API with various approaches ===")
# 也许前端用的是不同的认证方式
test_apis = [
    ('https://api.r6data.eu/api/operators?name=ash', {}),
    ('https://api.r6data.eu/api/operators?name=ash', {'Referer': 'https://r6data.eu/', 'Origin': 'https://r6data.eu'}),
    ('https://api.r6data.eu/api/maps', {'Referer': 'https://r6data.eu/'}),
]
for url, extra_h in test_apis:
    h = {**headers, **extra_h}
    try:
        ar = requests.get(url, headers=h, timeout=10)
        print(f"  {url} (extra={list(extra_h.keys())}) -> HTTP {ar.status_code}: {ar.text[:150]}")
    except Exception as e:
        print(f"  {url} -> Error: {e}")

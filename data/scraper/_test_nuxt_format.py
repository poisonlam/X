"""检查stats.cc新的NUXT格式"""
import requests
import re
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})

# 用排行榜第50名的玩家测试
with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

target = lb[50]
dn = target["displayName"]
pid = target["profileId"]
url = f"https://stats.cc/siege/{dn}/{pid}"
print(f"Testing: {url}")

r = session.get(url, timeout=(10, 25))
print(f"Status: {r.status_code}, Content-Length: {len(r.text)}")

# 方法1: 原始方式（application/json script tag）
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"\nMethod 1 (application/json script): {len(json_blocks)} blocks found")

# 方法2: window.__NUXT__
nuxt_match = re.search(r'window\.__NUXT__\s*=\s*(.+?)\s*</script>', r.text, re.DOTALL)
if nuxt_match:
    raw = nuxt_match.group(1).strip()
    print(f"\nMethod 2 (window.__NUXT__): Found! Raw length: {len(raw)}")
    print(f"First 500 chars of NUXT data:")
    print(raw[:500])
    print(f"\n...last 200 chars:")
    print(raw[-200:])
    
    # 尝试解析
    # window.__NUXT__ 通常是一个函数调用或直接JSON
    if raw.startswith('{') or raw.startswith('['):
        try:
            data = json.loads(raw)
            print(f"\nParsed as JSON! Type: {type(data).__name__}")
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            print(f"\nJSON parse failed: {e}")
    elif raw.startswith('('):
        # 可能是 IIFE
        print(f"\nStarts with '(' - likely IIFE/function call")
    else:
        print(f"\nUnexpected format, starts with: {raw[:50]}")
else:
    print("\nMethod 2 (window.__NUXT__): Not found")

# 方法3: __NUXT_DATA__ (id属性)
nuxt_data = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
if nuxt_data:
    print(f"\nMethod 3 (__NUXT_DATA__): Found! Length: {len(nuxt_data.group(1))}")
else:
    print(f"\nMethod 3 (__NUXT_DATA__): Not found")

# 查看所有script标签
all_scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"\n=== All script tags: {len(all_scripts)} ===")
for i, s in enumerate(all_scripts):
    s_stripped = s.strip()
    if len(s_stripped) > 10:
        preview = s_stripped[:150].replace('\n', ' ')
        print(f"  Script {i} (len={len(s_stripped)}): {preview}")

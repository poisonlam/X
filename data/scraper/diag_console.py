"""Quick diagnostic: check stats.cc console leaderboard response with proper decompression"""
import requests
import re
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    # Do NOT set Accept-Encoding - let requests handle it automatically
}

url = 'https://stats.cc/siege/leaderboards/console/ranked/rankPoints?page=1'
print(f"Fetching: {url}")
r = requests.get(url, headers=HEADERS, timeout=30)
print(f"Status: {r.status_code}")
print(f"Content-Length: {len(r.text)}")
print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
print(f"Content-Encoding: {r.headers.get('Content-Encoding', 'N/A')}")

# Check for JSON script blocks
json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"JSON blocks found: {len(json_blocks)}")

if json_blocks:
    for i, block in enumerate(json_blocks):
        print(f"\nBlock {i}: {len(block)} chars")
        try:
            data = json.loads(block)
            if isinstance(data, list):
                print(f"  Type: list, length: {len(data)}")
                if len(data) > 3:
                    root = data[3]
                    print(f"  data[3] type: {type(root).__name__}")
                    if isinstance(root, dict):
                        print(f"  data[3] keys: {list(root.keys())[:10]}")
                        for k in root.keys():
                            if 'leaderboard' in k.lower():
                                print(f"  Found leaderboard key: {k} -> {root[k]}")
            elif isinstance(data, dict):
                print(f"  Type: dict, keys: {list(data.keys())[:10]}")
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            print(f"  First 300 chars: {block[:300]}")
    print("\nDiagnosis: JSON blocks found - the fix works!")
else:
    print("\nNo JSON blocks found. Checking page content...")
    title = re.findall(r'<title>(.*?)</title>', r.text)
    print(f"Title: {title}")
    has_html = '<html' in r.text.lower()
    print(f"Has HTML tag: {has_html}")
    if not has_html:
        print("Response does not appear to be HTML - likely still compressed")
    print(f"\nFirst 500 chars:\n{r.text[:500]}")

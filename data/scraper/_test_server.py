"""Quick server connectivity test"""
import requests
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

import re

# Get the profile page
print("=== Fetching profile page ===")
try:
    r = s.get('https://stats.cc/siege/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381', timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Content length: {len(r.text)}")
    
    # Find script tags with JSON data
    scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
    print(f"\nJSON script tags found: {len(scripts)}")
    for i, s_content in enumerate(scripts):
        print(f"\n  Script {i}: {len(s_content)} chars")
        # Try to parse
        try:
            data = json.loads(s_content)
            if isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:20]}")
            elif isinstance(data, list):
                print(f"  List of {len(data)} items")
                if data:
                    print(f"  First item type: {type(data[0]).__name__}")
                    if isinstance(data[0], dict):
                        print(f"  First item keys: {list(data[0].keys())[:10]}")
        except:
            print(f"  Preview: {s_content[:200]}")
    
    # Check for Nuxt payload pattern
    nuxt_patterns = [
        r'<script id="__NUXT_DATA__"[^>]*>(.*?)</script>',
        r'window\.__NUXT__\s*=\s*',
        r'id="__NUXT_DATA__"',
    ]
    for pat in nuxt_patterns:
        matches = re.findall(pat, r.text, re.DOTALL)
        if matches:
            print(f"\nMatched pattern: {pat}")
            for m in matches[:1]:
                if isinstance(m, str) and len(m) > 0:
                    print(f"  Content preview ({len(m)} chars): {m[:500]}")
    
    # Check for links containing "match" or "history"
    links = re.findall(r'href="(/[^"]*(?:match|history|game)[^"]*)"', r.text)
    if links:
        print(f"\nLinks with match/history/game: {links[:20]}")
    
    # Check for API endpoints in the page
    api_patterns = re.findall(r'(https?://[^"\s]*api[^"\s]*)', r.text)
    if api_patterns:
        print(f"\nAPI URLs: {list(set(api_patterns))[:10]}")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

import json

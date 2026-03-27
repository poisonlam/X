"""深入检查 stats.cc 返回的 Nuxt 数据结构"""
import requests
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

url = 'https://stats.cc/siege/pengu/621b2e6e-22c5-4d88-a36c-87a5a7e5ab0e'
r = s.get(url, timeout=15)
print(f"Status: {r.status_code}")

json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
if json_blocks:
    nuxt = json.loads(json_blocks[0])
    print(f"Nuxt items: {len(nuxt)}")
    
    # Print types of items
    type_counts = {}
    dict_key_patterns = {}
    for i in range(min(len(nuxt), 200)):
        item = nuxt[i]
        t = type(item).__name__
        if t not in type_counts:
            type_counts[t] = 0
        type_counts[t] += 1
        
        if isinstance(item, dict):
            keys = tuple(sorted(item.keys()))
            if keys not in dict_key_patterns:
                dict_key_patterns[keys] = {'count': 0, 'example_idx': i}
            dict_key_patterns[keys]['count'] += 1
    
    print(f"\nType distribution (first 200 items):")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    
    print(f"\nDict key patterns (first 200 items):")
    for keys, info in sorted(dict_key_patterns.items(), key=lambda x: -x[1]['count'])[:15]:
        print(f"  Count={info['count']}: {keys[:5]}{'...' if len(keys) > 5 else ''}")
        # Show example
        example = nuxt[info['example_idx']]
        example_short = {k: str(v)[:50] if isinstance(v, str) else v for k, v in list(example.items())[:3]}
        print(f"    Example: {example_short}")
    
    # Check for error messages
    print(f"\nLooking for error-related strings...")
    for i in range(len(nuxt)):
        item = nuxt[i]
        if isinstance(item, str) and ('error' in item.lower() or 'fail' in item.lower() or 'exception' in item.lower()):
            print(f"  [{i}] {item[:200]}")
        elif isinstance(item, dict) and ('error' in str(item).lower()[:200] or 'statusCode' in item):
            print(f"  [{i}] {str(item)[:300]}")
    
    # Look for anything related to matches
    print(f"\nLooking for match-related dict items...")
    for i in range(len(nuxt)):
        item = nuxt[i]
        if isinstance(item, dict):
            keys_str = str(list(item.keys()))
            if any(k in keys_str for k in ['match', 'map', 'playlist', 'ranked', 'score', 'round']):
                print(f"  [{i}] keys={list(item.keys())[:8]}, vals={str(list(item.values())[:3])[:100]}")
    
    # Check tail
    print(f"\nLast 20 items:")
    for i in range(max(0, len(nuxt)-20), len(nuxt)):
        item = nuxt[i]
        print(f"  [{i}] {type(item).__name__}: {str(item)[:120]}")
else:
    print("No nuxt data found!")
    # Check page content
    if '<title>' in r.text:
        title = re.findall(r'<title>(.*?)</title>', r.text)
        print(f"Page title: {title}")

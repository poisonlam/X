"""Probe match detail page"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def deref(payload, idx, visited=None):
    if visited is None:
        visited = set()
    if not isinstance(idx, int) or idx < 0 or idx >= len(payload):
        return idx
    if idx in visited:
        return f"<circular:{idx}>"
    visited.add(idx)
    item = payload[idx]
    if isinstance(item, list):
        if len(item) >= 2 and isinstance(item[0], str) and item[0] in ('ShallowReactive', 'Reactive', 'ShallowRef', 'Ref'):
            return deref(payload, item[1], visited)
        return [deref(payload, i, set(visited)) for i in item if isinstance(i, int)]
    elif isinstance(item, dict):
        result = {}
        for k, v in item.items():
            result[k] = deref(payload, v, set(visited)) if isinstance(v, int) else v
        return result
    return item

def parse_nuxt_page(html):
    pattern = r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    if not matches:
        return None
    try:
        raw = json.loads(matches[0])
        return deref(raw, 0)
    except:
        return None

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
})

# Known match ID from profile
match_id = '086591c8-3c0a-4c25-8057-f925d895b6d2'

# Try various match detail URLs
urls = [
    f'https://stats.cc/siege/match/{match_id}',
    f'https://stats.cc/siege/matches/{match_id}',
    f'https://stats.cc/siege/-/match/{match_id}',
    f'https://stats.cc/siege/recent-matches/{match_id}',
]

for url in urls:
    print(f"\n=== {url} ===")
    try:
        r = s.get(url, timeout=15)
        print(f"Status: {r.status_code}, Size: {len(r.text)}")
        if r.status_code == 200:
            data = parse_nuxt_page(r.text)
            if data and 'pinia_colada' in data:
                pc = data['pinia_colada']
                print(f"pinia_colada keys: {list(pc.keys())}")
                for key in pc:
                    val = pc[key]
                    if isinstance(val, list) and len(val) > 0:
                        d = val[0]
                        if isinstance(d, dict):
                            print(f"  {key}: dict keys={list(d.keys())[:15]}")
                            # Look for rounds/players
                            for k2 in d:
                                v2 = d[k2]
                                if isinstance(v2, list) and len(v2) > 0:
                                    print(f"    {k2}: list[{len(v2)}]")
                                    if isinstance(v2[0], dict):
                                        print(f"      keys: {list(v2[0].keys())}")
                                        print(f"      [0]: {json.dumps(v2[0], ensure_ascii=False, default=str)[:400]}")
                                elif isinstance(v2, dict) and len(v2) > 0:
                                    print(f"    {k2}: dict keys={list(v2.keys())[:10]}")
                        elif isinstance(d, list):
                            print(f"  {key}: list[{len(d)}]")
                            if d and isinstance(d[0], dict):
                                print(f"    keys: {list(d[0].keys())}")
    except Exception as e:
        print(f"ERROR: {e}")

# Also check player_summary full structure from a match
print("\n\n=== Full player_summary from match ===")
r = s.get('https://stats.cc/siege/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381', timeout=30)
data = parse_nuxt_page(r.text)
if data and 'pinia_colada' in data:
    pc = data['pinia_colada']
    for key in pc:
        if 'matches' in key:
            val = pc[key]
            if isinstance(val, list) and len(val) > 0:
                match_data = val[0]
                if isinstance(match_data, dict) and 'pages' in match_data:
                    pages = match_data['pages']
                    if isinstance(pages, list) and len(pages) > 0:
                        page = pages[0]
                        if isinstance(page, list) and len(page) > 0:
                            first_match = page[0]
                            print(f"Full match: {json.dumps(first_match, ensure_ascii=False, default=str)}")

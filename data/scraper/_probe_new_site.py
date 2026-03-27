"""Extract match data from pages field"""
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

print("=== Extracting Match Pages Data ===")
r = s.get('https://stats.cc/siege/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381', timeout=30)
data = parse_nuxt_page(r.text)

if data and 'pinia_colada' in data:
    pc = data['pinia_colada']
    for key in pc:
        if 'matches' in key:
            val = pc[key]
            print(f"Matches key: {key}")
            if isinstance(val, list) and len(val) > 0:
                match_data = val[0]  # First element is the data
                if isinstance(match_data, dict) and 'pages' in match_data:
                    pages = match_data['pages']
                    print(f"Pages: {type(pages).__name__}[{len(pages) if isinstance(pages, list) else '?'}]")
                    if isinstance(pages, list):
                        for pi, page in enumerate(pages):
                            print(f"\n  Page {pi}: {type(page).__name__}")
                            if isinstance(page, list):
                                print(f"    Items: {len(page)}")
                                for mi, match in enumerate(page[:3]):
                                    if isinstance(match, dict):
                                        print(f"\n    Match {mi} keys: {list(match.keys())}")
                                        print(f"    Match {mi}: {json.dumps(match, ensure_ascii=False, default=str)[:600]}")
                            elif isinstance(page, dict):
                                print(f"    Keys: {list(page.keys())[:20]}")
                                # Check for items/data/matches sub-key
                                for k2 in page:
                                    v2 = page[k2]
                                    if isinstance(v2, list) and len(v2) > 0:
                                        print(f"    {k2}: list[{len(v2)}]")
                                        if isinstance(v2[0], dict):
                                            print(f"      First keys: {list(v2[0].keys())}")
                                            print(f"      First: {json.dumps(v2[0], ensure_ascii=False, default=str)[:500]}")
                                    elif isinstance(v2, dict):
                                        print(f"    {k2}: dict keys={list(v2.keys())[:10]}")
                                    elif v2 is not None:
                                        print(f"    {k2}: {str(v2)[:200]}")

# Also check sessions data
print("\n\n=== Sessions Data ===")
if data and 'pinia_colada' in data:
    pc = data['pinia_colada']
    for key in pc:
        if 'sessions' in key:
            val = pc[key]
            print(f"Sessions key: {key}")
            if isinstance(val, list) and len(val) > 0:
                session_data = val[0]
                if isinstance(session_data, list):
                    print(f"  Sessions list[{len(session_data)}]")
                    for si, sess in enumerate(session_data[:2]):
                        if isinstance(sess, dict):
                            print(f"\n  Session {si} keys: {list(sess.keys())}")
                            print(f"  Session {si}: {json.dumps(sess, ensure_ascii=False, default=str)[:500]}")

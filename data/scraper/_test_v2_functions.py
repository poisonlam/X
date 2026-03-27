"""Quick test of updated v2 fetch functions"""
import sys
import io

# Import first (it will set stdout), then we don't touch stdout again
import parallel_collect_v2 as pc
from id_mapping import get_mapper

mapper = get_mapper()

print("=== Test 1: fetch_player_matches ===")
# First manually test the URL and parsing
import requests
s = pc.get_session()
url = f'https://stats.cc/siege/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381'
print(f"URL: {url}")
r = s.get(url, timeout=30)
print(f"Status: {r.status_code}, Size: {len(r.text)}")

# Check for __NUXT_DATA__ in raw text
import re
has_nuxt = '__NUXT_DATA__' in r.text
has_nuxt_window = '__NUXT__' in r.text
script_tags = re.findall(r'<script[^>]*type="application/json"[^>]*>', r.text)
print(f"Has __NUXT_DATA__: {has_nuxt}")
print(f"Has __NUXT__: {has_nuxt_window}")
print(f"JSON script tags: {len(script_tags)}")
print(f"First 300 chars: {r.text[:300]}")
print(f"Last 300 chars: {r.text[-300:]}")

# Try raw requests (not using parallel_collect_v2's session)
print("\n--- Raw requests test ---")
import requests as raw_req
s2 = raw_req.Session()
s2.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
})
r2 = s2.get(url, timeout=30)
print(f"Raw Status: {r2.status_code}, Size: {len(r2.text)}")
has_nuxt2 = '__NUXT_DATA__' in r2.text
print(f"Raw Has __NUXT_DATA__: {has_nuxt2}")

nuxt = pc.parse_nuxt_page(r.text)
print(f"Nuxt result: {type(nuxt).__name__}")
if isinstance(nuxt, dict):
    print(f"  Top keys: {list(nuxt.keys())}")
    if 'pinia_colada' in nuxt:
        pcc = nuxt['pinia_colada']
        print(f"  pinia_colada keys ({len(pcc)}):")
        for k in pcc:
            v = pcc[k]
            print(f"    {k}: {type(v).__name__}[{len(v) if hasattr(v, '__len__') else ''}]")
            if 'matches' in k:
                print(f"    >>> MATCHES KEY FOUND!")
                if isinstance(v, list) and len(v) > 0:
                    md = v[0]
                    print(f"    data: {type(md).__name__}")
                    if isinstance(md, dict):
                        print(f"    data keys: {list(md.keys())}")
                        if 'pages' in md:
                            pages = md['pages']
                            print(f"    pages: {type(pages).__name__}[{len(pages) if isinstance(pages, list) else '?'}]")
                            if isinstance(pages, list) and len(pages) > 0:
                                pg = pages[0]
                                print(f"    page[0]: {type(pg).__name__}[{len(pg) if hasattr(pg, '__len__') else '?'}]")
                                if isinstance(pg, list) and len(pg) > 0:
                                    print(f"    page[0][0]: {type(pg[0]).__name__}")
                                    if isinstance(pg[0], dict):
                                        print(f"    keys: {list(pg[0].keys())}")

# Now test with the function
print("\n--- Testing fetch_player_matches ---")
matches = pc.fetch_player_matches('exolt2turNt', '3bae0298-8f3f-4fe2-ac96-91e12d31d381', mapper=mapper)
if matches is None:
    print("FAIL: returned None")
elif isinstance(matches, list):
    print(f"OK: {len(matches)} matches found")
    for m in matches[:3]:
        print(f"  {m['match_id'][:12]}... map={m['map']} playlist={m['playlist']} outcome={m.get('outcome')}")
else:
    print(f"UNEXPECTED: {type(matches)}")

print("\n=== Test 2: fetch_match_detail ===")
if matches and len(matches) > 0:
    mid = matches[0]['match_id']
    print(f"Fetching detail for: {mid}")
    import time
    time.sleep(1)
    detail = pc.fetch_match_detail(mid, mapper=mapper)
    if detail is None:
        print("FAIL: returned None")
    elif isinstance(detail, dict):
        print(f"OK: match detail retrieved")
        print(f"  map: {detail.get('map')}")
        print(f"  scores: {detail.get('scores')}")
        print(f"  total_players: {detail.get('total_players')}")
        print(f"  total_rounds: {detail.get('total_rounds')}")
        print(f"  round_records: {len(detail.get('round_records', []))}")
        print(f"  player_summaries: {len(detail.get('player_summaries', []))}")
        print(f"  profiles: {len(detail.get('profiles', []))}")
        if detail.get('round_records'):
            rr = detail['round_records'][0]
            print(f"  First round record: operator={rr.get('operator')} kills={rr.get('kills')} deaths={rr.get('deaths')}")
        if detail.get('player_summaries'):
            ps = detail['player_summaries'][0]
            print(f"  First player: {ps.get('username')} team={ps.get('team')} kills={ps.get('kills')} deaths={ps.get('deaths')}")
    else:
        print(f"UNEXPECTED: {type(detail)}")
else:
    print("SKIP: no matches to test")

print("\nDone!")

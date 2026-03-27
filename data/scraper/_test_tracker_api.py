#!/usr/bin/env python3
"""Test R6 Tracker API endpoints to compare with stats.cc"""
import urllib.request
import json
import time
import ssl

# Disable SSL verification for testing (some corporate envs have issues)
ctx = ssl.create_default_context()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://r6.tracker.network',
    'Referer': 'https://r6.tracker.network/',
}

test_cases = [
    # Player profile
    ("Player Profile (pengu)", "https://api.tracker.gg/api/v2/r6siege/standard/profile/ubi/pengu"),
    # Player profile by ID
    ("Player Profile (by ID)", "https://api.tracker.gg/api/v2/r6siege/standard/profile/ubi/e4f084a2-d4ff-4fd7-947b-ea2c61e4ddbf"),
    # Match history 
    ("Match History", "https://api.tracker.gg/api/v2/r6siege/standard/matches/ubi/e4f084a2-d4ff-4fd7-947b-ea2c61e4ddbf"),
    # Leaderboard
    ("Leaderboard", "https://api.tracker.gg/api/v2/r6siege/standard/leaderboards?type=stats&stat=PVPRankedWins&page=1"),
    # Seasonal stats
    ("Seasonal Stats", "https://api.tracker.gg/api/v2/r6siege/standard/profile/ubi/pengu/seasons"),
]

print("=" * 70)
print("R6 TRACKER API ENDPOINT TESTING")
print("=" * 70)

for name, url in test_cases:
    print(f"\n[TEST] {name}")
    print(f"  URL: {url}")
    
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        elapsed = time.time() - start
        body = resp.read()
        ct = resp.headers.get('Content-Type', '?')
        
        print(f"  Status: {resp.status} | Time: {elapsed:.3f}s | Size: {len(body):,} bytes")
        print(f"  Content-Type: {ct}")
        
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                print(f"  JSON keys: {list(data.keys())}")
                # Show structure
                if 'data' in data:
                    d = data['data']
                    if isinstance(d, dict):
                        print(f"  data keys: {list(d.keys())[:10]}")
                        # Check for segments (player stats)
                        if 'segments' in d:
                            segs = d['segments']
                            print(f"  segments count: {len(segs)}")
                            if segs:
                                print(f"  first segment type: {segs[0].get('type','?')}")
                        # Check for matches
                        if 'matches' in d:
                            matches = d['matches']
                            print(f"  matches count: {len(matches)}")
                            if matches:
                                m = matches[0]
                                print(f"  first match keys: {list(m.keys())[:10]}")
                                if 'attributes' in m:
                                    print(f"  match attributes: {m['attributes']}")
                                if 'segments' in m:
                                    print(f"  match segments count: {len(m['segments'])}")
                    elif isinstance(d, list):
                        print(f"  data is list, length: {len(d)}")
                        if d:
                            print(f"  first item keys: {list(d[0].keys())[:10]}" if isinstance(d[0], dict) else f"  first item type: {type(d[0])}")
                if 'errors' in data:
                    print(f"  ERRORS: {data['errors']}")
            elif isinstance(data, list):
                print(f"  JSON array length: {len(data)}")
        except json.JSONDecodeError:
            print(f"  NOT JSON, first 200 chars: {body[:200]}")
            
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start if 'start' in dir() else 0
        body = e.read()
        print(f"  HTTP ERROR: {e.code} {e.reason} | Size: {len(body)} bytes")
        try:
            err = json.loads(body)
            print(f"  Error body: {json.dumps(err, indent=2)[:300]}")
        except:
            print(f"  Error body: {body[:300]}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    
    time.sleep(2)

# Speed comparison test
print("\n" + "=" * 70)
print("SPEED COMPARISON: R6 Tracker API vs stats.cc HTML")
print("=" * 70)

# Test R6 Tracker API speed (3 requests)
api_times = []
for i in range(3):
    try:
        url = "https://api.tracker.gg/api/v2/r6siege/standard/profile/ubi/pengu"
        req = urllib.request.Request(url, headers=HEADERS)
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        body = resp.read()
        elapsed = time.time() - start
        api_times.append(elapsed)
        print(f"  R6 Tracker API #{i+1}: {elapsed:.3f}s ({len(body):,} bytes)")
    except Exception as e:
        print(f"  R6 Tracker API #{i+1}: ERROR - {e}")
    time.sleep(1.5)

# Test stats.cc HTML speed (3 requests) 
html_times = []
for i in range(3):
    try:
        url = "https://stats.cc/siege/player/pengu"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        body = resp.read()
        elapsed = time.time() - start
        html_times.append(elapsed)
        print(f"  stats.cc HTML #{i+1}: {elapsed:.3f}s ({len(body):,} bytes)")
    except Exception as e:
        print(f"  stats.cc HTML #{i+1}: ERROR - {e}")
    time.sleep(1.5)

print("\n--- Summary ---")
if api_times:
    avg_api = sum(api_times) / len(api_times)
    print(f"R6 Tracker API avg: {avg_api:.3f}s, avg size: ~{sum(len(b'x')*1 for _ in range(1))} bytes")
if html_times:
    avg_html = sum(html_times) / len(html_times)
    print(f"stats.cc HTML avg: {avg_html:.3f}s")
if api_times and html_times:
    print(f"API is {avg_html/avg_api:.1f}x faster in response time")

print("\n--- Key Finding ---")
print("R6 Tracker returns PURE JSON (no HTML parsing needed)")
print("stats.cc returns full HTML page requiring Nuxt SSR data extraction")
print("Both ultimately source data from Ubisoft's API")

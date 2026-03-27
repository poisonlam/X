#!/usr/bin/env python3
"""Probe stats.cc for faster API endpoints - with better error handling"""
import urllib.request
import time
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

test_cases = [
    ("1. Normal HTML", "https://stats.cc/siege/player/pengu", {}),
    ("2. JSON Accept", "https://stats.cc/siege/player/pengu", {"Accept": "application/json"}),
    ("3. x-nuxt-data header", "https://stats.cc/siege/player/pengu", {"x-nuxt-data": "true"}),
    ("4. API route", "https://stats.cc/api/siege/player/pengu", {}),
    ("5. _api route", "https://stats.cc/_api/siege/player/pengu", {}),
    ("6. Match HTML", "https://stats.cc/siege/match/d0c6c5c8-6a0a-45e5-b4da-8e2c6c69bcbb", {}),
    ("7. Match x-nuxt-data", "https://stats.cc/siege/match/d0c6c5c8-6a0a-45e5-b4da-8e2c6c69bcbb", {"x-nuxt-data": "true"}),
]

results = []

for name, url, extra in test_cases:
    try:
        headers = dict(HEADERS)
        headers.update(extra)
        req = urllib.request.Request(url, headers=headers)
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=15)
        elapsed = time.time() - start
        body = resp.read()
        ct = resp.headers.get("Content-Type", "")
        
        is_json = False
        try:
            json.loads(body)
            is_json = True
        except:
            pass
        
        is_html = b"<html" in body[:500].lower() or b"<!doctype" in body[:500].lower()
        nuxt_blocks = len(re.findall(rb'__NUXT_DATA__', body))
        
        status = f"{resp.status} OK"
        result_type = "JSON" if is_json else ("HTML" if is_html else "Other")
        results.append((name, status, f"{elapsed:.2f}s", f"{len(body):,}", ct[:40], result_type, nuxt_blocks))
        
        print(f"[OK] {name}: {resp.status} | {elapsed:.2f}s | {len(body):,} bytes | {result_type}")
        if is_json:
            data = json.loads(body)
            if isinstance(data, list) and len(data) > 0:
                print(f"     JSON array[{len(data)}], first item type: {type(data[0]).__name__}")
                if isinstance(data[0], dict):
                    print(f"     Keys: {list(data[0].keys())[:8]}")
            elif isinstance(data, dict):
                print(f"     JSON keys: {list(data.keys())[:8]}")
        
    except urllib.error.HTTPError as e:
        elapsed = 0
        print(f"[ERR] {name}: HTTP {e.code} {e.reason}")
        results.append((name, f"HTTP {e.code}", "-", "-", "-", "Error", 0))
    except Exception as e:
        print(f"[ERR] {name}: {type(e).__name__}: {e}")
        results.append((name, "Error", "-", "-", "-", "Error", 0))
    
    time.sleep(1.5)

# Now measure pure response time for HTML page
print("\n" + "=" * 60)
print("TIMING ANALYSIS")
print("=" * 60)

timings = []
url = "https://stats.cc/siege/player/pengu"

for i in range(3):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read()
        elapsed = time.time() - start
        timings.append(elapsed)
        print(f"  Request {i+1}: {elapsed:.3f}s ({len(body):,} bytes)")
        time.sleep(2)
    except Exception as e:
        print(f"  Request {i+1}: Error - {e}")

if timings:
    avg = sum(timings) / len(timings)
    print(f"\n  Average response time: {avg:.3f}s")
    print(f"  Current delay between requests: 2.5s + random(0.3, 2.0)")
    print(f"  Network time per request: ~{avg:.1f}s")
    print(f"  Total time per request (current): ~{avg + 2.5 + 1.15:.1f}s (network + base_delay + avg_jitter)")
    
    # Theoretical minimum with reduced delay
    print(f"\n  If delay reduced to 1.0s + random(0.2, 0.5):")
    new_total = avg + 1.0 + 0.35
    old_total = avg + 2.5 + 1.15
    print(f"    Time per request: ~{new_total:.1f}s (vs current ~{old_total:.1f}s)")
    print(f"    Speedup: {old_total/new_total:.2f}x")
    
    print(f"\n  If delay reduced to 0.5s + random(0.1, 0.3):")
    new_total2 = avg + 0.5 + 0.2
    print(f"    Time per request: ~{new_total2:.1f}s (vs current ~{old_total:.1f}s)")
    print(f"    Speedup: {old_total/new_total2:.2f}x")
    
    print(f"\n  If using async (2 concurrent requests per shard):")
    print(f"    Effective speedup: ~2x on top of any delay reduction")

# Nuxt data analysis
print("\n" + "=" * 60)
print("NUXT DATA SIZE ANALYSIS")
print("=" * 60)
try:
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=15)
    body = resp.read()
    
    nuxt_parts = re.findall(rb'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', body, re.DOTALL)
    nuxt_size = sum(len(p) for p in nuxt_parts)
    
    print(f"  Total page size: {len(body):,} bytes")
    print(f"  __NUXT_DATA__ payload: {nuxt_size:,} bytes ({nuxt_size/len(body)*100:.1f}%)")
    print(f"  HTML/CSS/JS overhead: {len(body)-nuxt_size:,} bytes ({(len(body)-nuxt_size)/len(body)*100:.1f}%)")
    print(f"\n  Conclusion: {(len(body)-nuxt_size)/len(body)*100:.0f}% of data transferred is non-useful HTML overhead")
    print(f"  A JSON API would reduce transfer by ~{(len(body)-nuxt_size)/1024:.0f} KB per request")
    print(f"  But this is minor compared to the wait delay between requests")
except Exception as e:
    print(f"  Error: {e}")

"""
方案A延迟安全测试
- 逐步降低请求间隔，观察 stats.cc 的响应
- 每个延迟级别发送10个请求，统计成功率和响应时间
- 目标：找到不触发429/500的最低安全延迟
"""
import time
import sys
import io
import json
import urllib.request
import random
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

BASE = os.path.dirname(os.path.abspath(__file__))

def load_test_urls():
    """Load some known match IDs from existing data for testing"""
    urls = []
    
    # Get some match IDs from PC data
    for sf in sorted(os.listdir(os.path.join(BASE, "output/match_data"))):
        if sf.startswith("shard_") and os.path.isdir(os.path.join(BASE, "output/match_data", sf)):
            mf = os.path.join(BASE, "output/match_data", sf, "match_details.json")
            if os.path.exists(mf):
                try:
                    with open(mf, "r", encoding="utf-8") as f:
                        matches = json.load(f)
                    for m in matches[:5]:  # Get 5 match IDs per shard
                        mid = m.get("match_id", "")
                        if mid:
                            urls.append(f"https://stats.cc/siege/matches/{mid}")
                except:
                    pass
    
    # Also get some player page URLs
    lb_file = os.path.join(BASE, "output/leaderboard/leaderboard_full.json")
    if os.path.exists(lb_file):
        try:
            with open(lb_file, "r", encoding="utf-8") as f:
                players = json.load(f)
            for p in players[:10]:
                name = p.get("displayName", "")
                pid = p.get("profileId", "")
                if name and pid:
                    urls.append(f"https://stats.cc/siege/{name}/{pid}")
        except:
            pass
    
    random.shuffle(urls)
    return urls


def send_request(url, timeout=20):
    """Send single request and return (status, response_time)"""
    req = urllib.request.Request(url, headers=HEADERS)
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        elapsed = time.time() - t0
        size = len(resp.read())
        return resp.status, elapsed, size
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        return e.code, elapsed, 0
    except Exception as e:
        elapsed = time.time() - t0
        return 0, elapsed, 0


def test_delay_level(urls, base_delay, jitter_range, requests_count=8):
    """Test a specific delay level with N requests"""
    results = []
    successes = 0
    errors_429 = 0
    errors_500 = 0
    errors_other = 0
    
    for i in range(min(requests_count, len(urls))):
        url = urls[i]
        status, elapsed, size = send_request(url)
        
        label = url.split("/")[-1][:20]
        
        if status == 200:
            successes += 1
            icon = "OK"
        elif status == 429:
            errors_429 += 1
            icon = "429"
        elif status >= 500:
            errors_500 += 1
            icon = "5xx"
        else:
            errors_other += 1
            icon = f"{status}"
        
        results.append({"status": status, "time": elapsed, "size": size})
        print(f"    [{i+1}/{requests_count}] {icon} ({elapsed:.2f}s, {size/1024:.0f}KB) {label}")
        
        # Wait before next request
        if i < requests_count - 1:
            actual_delay = base_delay + random.uniform(*jitter_range)
            time.sleep(actual_delay)
    
    avg_time = sum(r["time"] for r in results) / len(results) if results else 0
    success_rate = successes / len(results) * 100 if results else 0
    
    return {
        "successes": successes,
        "errors_429": errors_429,
        "errors_500": errors_500,
        "errors_other": errors_other,
        "total": len(results),
        "success_rate": success_rate,
        "avg_response_time": avg_time,
    }


def main():
    print("=" * 70)
    print("PLAN A: DELAY SAFETY TEST")
    print("=" * 70)
    print("Testing different delay levels to find minimum safe delay")
    print()
    
    # Load test URLs
    urls = load_test_urls()
    print(f"Loaded {len(urls)} test URLs")
    
    if len(urls) < 20:
        print("[WARN] Not enough URLs for comprehensive test")
        return
    
    # First: Warm up with a single request to check if site is accessible
    print("\n[Warm-up] Checking stats.cc accessibility...")
    status, elapsed, size = send_request(urls[0])
    print(f"  Status: {status}, Time: {elapsed:.2f}s, Size: {size/1024:.0f}KB")
    
    if status != 200:
        print(f"  [WARN] stats.cc returned {status}, may be experiencing issues")
        print("  Waiting 30s before starting tests...")
        time.sleep(30)
        # Try again
        status, elapsed, size = send_request(urls[1])
        print(f"  Retry: Status: {status}, Time: {elapsed:.2f}s")
        if status != 200:
            print("  [ERROR] stats.cc still not accessible. Aborting test.")
            print("  This may indicate temporary server issues or IP-level throttling.")
            return
    
    time.sleep(5)  # Wait before starting actual tests
    
    # Test different delay levels
    # Start from current delay (safe) and work down
    delay_levels = [
        {"name": "Current (2.5s + 0.3~1.5s jitter)", "base": 2.5, "jitter": (0.3, 1.5)},
        {"name": "Moderate (1.5s + 0.3~1.0s jitter)", "base": 1.5, "jitter": (0.3, 1.0)},
        {"name": "Aggressive (1.0s + 0.2~0.8s jitter)", "base": 1.0, "jitter": (0.2, 0.8)},
        {"name": "Very Aggressive (0.5s + 0.1~0.5s jitter)", "base": 0.5, "jitter": (0.1, 0.5)},
    ]
    
    all_results = []
    url_idx = 2  # Start from index 2 (used 0-1 for warmup)
    
    for level in delay_levels:
        # Get a fresh batch of URLs for each level
        batch_urls = urls[url_idx:url_idx+8]
        url_idx += 8
        
        if len(batch_urls) < 6:
            print(f"\n[SKIP] Not enough unused URLs for level: {level['name']}")
            break
        
        print(f"\n{'=' * 50}")
        print(f"  Testing: {level['name']}")
        print(f"  Effective delay: {level['base'] + level['jitter'][0]:.1f}s ~ {level['base'] + level['jitter'][1]:.1f}s")
        print(f"{'=' * 50}")
        
        result = test_delay_level(batch_urls, level["base"], level["jitter"], requests_count=8)
        result["level"] = level
        all_results.append(result)
        
        print(f"\n  Result: {result['success_rate']:.0f}% success rate "
              f"({result['successes']}/{result['total']} OK, "
              f"{result['errors_429']} x429, {result['errors_500']} x5xx)")
        print(f"  Avg response time: {result['avg_response_time']:.2f}s")
        
        # If we got 429 errors, don't test more aggressive levels
        if result["errors_429"] > 0:
            print(f"\n  [STOP] Hit rate limit at this level. Not testing more aggressive delays.")
            # Cooldown
            print(f"  Cooling down 60s...")
            time.sleep(60)
            break
        
        # If we got 500 errors (more than 1), also be cautious
        if result["errors_500"] > 2:
            print(f"\n  [WARN] Multiple 500 errors. Server may be stressed.")
            print(f"  Cooling down 30s...")
            time.sleep(30)
        
        # Wait between test levels
        print(f"  Waiting 15s before next level...")
        time.sleep(15)
    
    # ============================================================
    # Summary and Recommendation
    # ============================================================
    print(f"\n{'=' * 70}")
    print("DELAY TEST RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"\n  {'Level':<45} {'Success':>8} {'429s':>6} {'5xx':>6} {'Avg Time':>10}")
    print(f"  {'-'*45} {'-'*8} {'-'*6} {'-'*6} {'-'*10}")
    
    best_level = None
    for r in all_results:
        level_name = r["level"]["name"]
        print(f"  {level_name:<45} {r['success_rate']:>7.0f}% {r['errors_429']:>5} {r['errors_500']:>5} {r['avg_response_time']:>9.2f}s")
        
        if r["success_rate"] >= 95 and r["errors_429"] == 0:
            best_level = r
    
    if best_level:
        bl = best_level["level"]
        effective_min = bl["base"] + bl["jitter"][0]
        effective_max = bl["base"] + bl["jitter"][1]
        effective_avg = (effective_min + effective_max) / 2
        
        print(f"\n  RECOMMENDATION:")
        print(f"  Best safe delay: {bl['name']}")
        print(f"  Parameters: --delay {bl['base']} with jitter ({bl['jitter'][0]}, {bl['jitter'][1]})")
        print(f"  Effective delay range: {effective_min:.1f}s ~ {effective_max:.1f}s (avg {effective_avg:.1f}s)")
        
        # Current vs recommended speedup
        current_avg = 2.5 + 0.9  # current avg delay
        speedup = current_avg / effective_avg
        print(f"\n  Speedup vs current ({current_avg:.1f}s avg): {speedup:.1f}x")
    else:
        print(f"\n  RECOMMENDATION:")
        print(f"  All tested levels had issues. Keep current delay (2.5s).")
        print(f"  stats.cc may be under heavy load currently.")


if __name__ == "__main__":
    main()

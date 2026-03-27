"""
补充测试 0.5s 延迟级别 (Very Aggressive)
单独测试更多请求以确认安全下限
"""
import time, sys, io, json, urllib.request, random, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

BASE = os.path.dirname(os.path.abspath(__file__))

def send_request(url, timeout=20):
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

def main():
    print("=" * 70)
    print("ADDITIONAL DELAY TEST: 0.5s level")
    print("=" * 70)
    
    # Load more URLs
    urls = []
    for sf in sorted(os.listdir(os.path.join(BASE, "output/match_data"))):
        if sf.startswith("shard_") and os.path.isdir(os.path.join(BASE, "output/match_data", sf)):
            mf = os.path.join(BASE, "output/match_data", sf, "match_details.json")
            if os.path.exists(mf):
                try:
                    with open(mf, "r", encoding="utf-8") as f:
                        matches = json.load(f)
                    for m in matches[5:15]:  # Skip the first 5 (already used)
                        mid = m.get("match_id", "")
                        if mid:
                            urls.append(f"https://stats.cc/siege/matches/{mid}")
                except:
                    pass
    
    random.shuffle(urls)
    print(f"Loaded {len(urls)} test URLs")
    
    # Test 0.5s delay
    print(f"\n--- Testing: Very Aggressive (0.5s + 0.1~0.5s jitter) ---")
    print(f"Effective delay: 0.6s ~ 1.0s")
    
    successes = 0
    errors_429 = 0
    errors_5xx = 0
    errors_other = 0
    total = min(12, len(urls))
    
    for i in range(total):
        url = urls[i]
        status, elapsed, size = send_request(url)
        label = url.split("/")[-1][:20]
        
        if status == 200:
            successes += 1
            icon = "OK"
        elif status == 429:
            errors_429 += 1
            icon = "429!"
        elif status >= 500:
            errors_5xx += 1
            icon = f"{status}"
        else:
            errors_other += 1
            icon = f"{status}"
        
        print(f"  [{i+1}/{total}] {icon} ({elapsed:.2f}s, {size/1024:.0f}KB) {label}")
        
        if i < total - 1:
            delay = 0.5 + random.uniform(0.1, 0.5)
            time.sleep(delay)
        
        # Stop if rate limited
        if errors_429 > 0:
            print(f"\n  [STOP] Hit 429 rate limit!")
            break
    
    done = successes + errors_429 + errors_5xx + errors_other
    print(f"\n  Result: {successes}/{done} OK, {errors_429} x429, {errors_5xx} x5xx, {errors_other} other")
    print(f"  Success rate: {successes/done*100:.0f}%")
    
    if errors_429 > 0:
        print(f"\n  CONCLUSION: 0.5s delay is TOO AGGRESSIVE - triggers rate limiting")
        print(f"  Stick with 1.0s + (0.2, 0.8) jitter as the optimal safe delay")
    elif errors_5xx > 1:
        print(f"\n  CONCLUSION: 0.5s delay causes server stress (multiple 5xx errors)")
        print(f"  Stick with 1.0s + (0.2, 0.8) jitter as the optimal safe delay")
    else:
        print(f"\n  CONCLUSION: 0.5s delay also works! But risky with 13+ concurrent scrapers")
        print(f"  Recommended conservative optimum: 1.0s + (0.2, 0.8) jitter")
        print(f"  Aggressive option: 0.5s + (0.1, 0.5) - use with caution")


if __name__ == "__main__":
    main()

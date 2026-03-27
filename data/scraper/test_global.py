import requests, re, json, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    # Do NOT set Accept-Encoding - let requests handle it automatically
}

url = 'https://stats.cc/siege/leaderboards/global/ranked/rankPoints?page=1'
print(f"Fetching: {url}")
r = requests.get(url, headers=HEADERS, timeout=30)
print(f"Status: {r.status_code}")
print(f"Content-Length: {len(r.text)}")
print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
print(f"Content-Encoding: {r.headers.get('Content-Encoding', 'N/A')}")

blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"JSON blocks found: {len(blocks)}")

if blocks:
    for i, b in enumerate(blocks):
        print(f"\nBlock {i}: {len(b)} chars")
        data = json.loads(b)
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
    print("\nDiagnosis: JSON blocks found - SSR data available!")
else:
    print("\nNo JSON blocks found.")
    print(f"First 500 chars:\n{r.text[:500]}")

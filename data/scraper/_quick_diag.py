"""快速诊断脚本：检查进度文件和API连通性"""
import json, os, time, sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. 检查PC进度
print("\n>>> PC 分片进度 <<<")
pc_total = 0
for i in range(5):
    f = os.path.join(BASE, f"output/match_data/_shard_{i}_progress.json")
    if os.path.exists(f):
        p = json.load(open(f, 'r', encoding='utf-8'))
        n = len(p.get('completed_players', []))
        pc_total += n
        ts = p.get('last_updated', '?')
        print(f"  Shard {i}: {n} players, last_updated={ts}")
print(f"  PC 总计: {pc_total}")

# 2. 检查Extra进度
print("\n>>> Extra 分片进度 <<<")
ex_total = 0
for i in range(8):
    f = os.path.join(BASE, f"output/extra_match_data/_shard_{i}_progress.json")
    if os.path.exists(f):
        p = json.load(open(f, 'r', encoding='utf-8'))
        n = len(p.get('completed_players', []))
        ex_total += n
        ts = p.get('last_updated', '?')
        print(f"  Shard {i}: {n} players, last_updated={ts}")
print(f"  Extra 总计: {ex_total}")

# 3. 测试API连通性
print("\n>>> API 连通性测试 <<<")
import requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# 测试一个已知玩家的profile页面
test_urls = [
    "https://r6.tracker.network/r6siege/profile/ubi/pengu/overview",
    "https://api.tracker.network/api/v2/r6siege/standard/profile/ubi/pengu",
]
for url in test_urls:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  {url[:60]}... => {r.status_code} ({len(r.text)} bytes)")
    except Exception as e:
        print(f"  {url[:60]}... => ERROR: {e}")

# 4. 测试cookie/auth
print("\n>>> Cookie 文件检查 <<<")
cred_dir = os.path.join(BASE, "..", "..", "creds")
for f in os.listdir(cred_dir) if os.path.isdir(cred_dir) else []:
    fpath = os.path.join(cred_dir, f)
    size = os.path.getsize(fpath)
    mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"  {f}: {size} bytes, modified {mtime}")

print("\n诊断完成")

"""直接测试几个最近FAIL的玩家，看看API返回了什么"""
import requests
import time

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

# 测试几个从日志里看到FAIL的玩家
test_players = [
    ("fz.sakura", "5687"),  # 从日志里看到FAIL的
    ("BuckYourAshhole", "5692"),
    ("Avqnn", "5697"),
]

# 也测试一个之前成功的玩家（排名靠前的）
# 先用进度文件里已完成的最后一个玩家

import json
with open("output/match_data/_shard_0_progress.json", "r") as f:
    prog = json.load(f)
last_completed = prog["completed_players"][-3:]
print(f"最近完成的3个玩家: {last_completed}")

for name, idx in test_players:
    # 这里的profile_id不对，只是排行榜序号。让我看看代码是怎么获取真正的profile_id的
    url = f"https://stats.cc/siege/{name}/{idx}"
    print(f"\n--- Testing: {name} (index {idx}) ---")
    print(f"URL: {url}")
    try:
        r = session.get(url, timeout=(10, 25))
        print(f"Status: {r.status_code}")
        print(f"Content-Length: {len(r.text)}")
        # 检查是否有__NUXT__
        if "__NUXT__" in r.text or "__NUXT_DATA__" in r.text:
            print("Has NUXT data: YES")
        else:
            print("Has NUXT data: NO")
        # 看前500个字符
        print(f"First 300 chars: {r.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)

# 最重要的：看看profile_id到底是什么
# 从排行榜数据里找出来
print("\n\n=== 检查排行榜数据中的profile_id格式 ===")
import os
leaderboard_path = None
for root, dirs, files in os.walk("output"):
    for f in files:
        if "leaderboard" in f.lower() or "ranking" in f.lower():
            leaderboard_path = os.path.join(root, f)
            print(f"Found: {leaderboard_path}")

# 也看看parallel_collect.py里怎么获取玩家列表的
print("\n=== 查看shard_0进度中前3个已完成玩家 ===")
for p in prog["completed_players"][:3]:
    print(f"  {p}")
print(f"\n=== 总已完成: {len(prog['completed_players'])} 玩家, {len(prog['completed_matches'])} 对局 ===")

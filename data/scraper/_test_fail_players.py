"""测试FAIL的玩家：用真正的UUID profile_id"""
import sys
sys.path.insert(0, ".")
import requests
import json
from parallel_collect import parse_nuxt_page, deref, get_session, fetch_player_matches

with open("output/leaderboard/leaderboard_full.json", "r") as f:
    lb = json.load(f)

# 测试排行榜5686-5690的玩家（这些在日志里都FAIL了）
print("=== 测试日志里FAIL的玩家 ===")
for idx in [5686, 5687, 5688, 5689, 5690]:
    entry = lb[idx]
    dn = entry["displayName"]
    pid = entry["profileId"]
    print(f"\n[{idx}] {dn} / {pid[:24]}...")
    
    # 直接调用fetch_player_matches
    result = fetch_player_matches(dn, pid)
    print(f"  Result: {type(result).__name__}, value={result if result is None else f'list({len(result)})' if isinstance(result, list) else str(result)[:100]}")

# 对比：测试排行榜前面的几个玩家
print("\n\n=== 对比测试：排行榜前面的玩家 ===")
for idx in [0, 10, 50, 100]:
    entry = lb[idx]
    dn = entry["displayName"]
    pid = entry["profileId"]
    print(f"\n[{idx}] {dn} / {pid[:24]}...")
    
    result = fetch_player_matches(dn, pid)
    print(f"  Result: {type(result).__name__}, value={result if result is None else f'list({len(result)})' if isinstance(result, list) else str(result)[:100]}")

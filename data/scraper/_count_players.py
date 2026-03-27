import json, os

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'match_data')
total_pids = set()
total_matches = 0

for s in range(5):
    f = os.path.join(base, f'shard_{s}', 'match_details.json')
    if not os.path.exists(f):
        continue
    d = json.load(open(f, 'r', encoding='utf-8'))
    total_matches += len(d)
    for m in d:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id', '')
            if pid:
                total_pids.add(pid)

# 也加载排行榜中的玩家IDs
lb_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'leaderboard', 'leaderboard_full.json')
lb_players = json.load(open(lb_file, 'r', encoding='utf-8'))
lb_ids = set(p['profileId'] for p in lb_players)

# 计算不在排行榜中但出现在比赛数据里的额外玩家
extra_players = total_pids - lb_ids

print(f"排行榜玩家数: {len(lb_ids)}")
print(f"比赛数据中的唯一玩家数: {len(total_pids)}")
print(f"其中不在排行榜中的额外玩家: {len(extra_players)}")
print(f"总比赛场次: {total_matches}")
print(f"平均每场玩家数: {len(total_pids) * 10 / total_matches:.1f}" if total_matches > 0 else "")

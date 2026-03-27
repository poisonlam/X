"""统计已采集比赛数据中涉及的唯一玩家数量"""
import json, os

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'match_data')
lb_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'leaderboard', 'leaderboard_full.json')

total_pids = set()
total_matches = 0

for s in range(5):
    f = os.path.join(base, f'shard_{s}', 'match_details.json')
    if not os.path.exists(f):
        continue
    print(f"Loading shard {s}...", end=" ", flush=True)
    with open(f, 'r', encoding='utf-8') as fh:
        d = json.load(fh)
    total_matches += len(d)
    for m in d:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id', '')
            if pid:
                total_pids.add(pid)
    print(f"{len(d)} matches loaded")

# 排行榜玩家
lb_players = json.load(open(lb_file, 'r', encoding='utf-8'))
lb_ids = set(p['profileId'] for p in lb_players)

# 不在排行榜中但出现在比赛中的玩家
extra_players = total_pids - lb_ids

print()
print("=" * 60)
print(f"排行榜玩家数:           {len(lb_ids):>8,}")
print(f"比赛数据中的唯一玩家:   {len(total_pids):>8,}")
print(f"其中不在排行榜中的:     {len(extra_players):>8,}")
print(f"总比赛场次:             {total_matches:>8,}")
print("=" * 60)

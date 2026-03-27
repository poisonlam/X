import json

# 1. Check extra players list - does it have rank info?
print("=== Extra Players List ===")
ep = json.load(open("output/extra_match_data/_extra_players.json", 'r', encoding='utf-8'))
print(f"Total: {len(ep)}")
if ep:
    sample = ep[:3]
    for s in sample:
        if isinstance(s, dict):
            print(f"  Keys: {list(s.keys())}")
            print(f"  Sample: {json.dumps(s, ensure_ascii=False)[:200]}")
        elif isinstance(s, str):
            print(f"  Just an ID string: {s[:50]}")

# 2. Check all unique source_player ranks from PC match data  
print("\n=== Source Player Ranks from PC Matches ===")
rank_counts = {}
player_ranks = {}  # profile_id -> (rank, rp)
total_matches = 0
for i in range(5):
    f = f"output/match_data/shard_{i}/match_details.json"
    try:
        data = json.load(open(f, 'r', encoding='utf-8'))
        for m in data:
            total_matches += 1
            sp = m.get("source_player", {})
            rank = sp.get("rank", "")
            rp = sp.get("rankPoints", 0)
            pid = sp.get("profile_id", sp.get("profileId", ""))
            if rank:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
            # Also get all player IDs from summaries
            for ps in m.get("player_summaries", []):
                p_id = ps.get("profile_id", "")
                if p_id:
                    # We only have rank for source player
                    if p_id == pid and rank:
                        player_ranks[p_id] = (rank, rp)
                    elif p_id not in player_ranks:
                        player_ranks[p_id] = ("", 0)
    except:
        pass

print(f"Total matches scanned: {total_matches}")
print(f"Unique source player rank distribution:")
for r, c in sorted(rank_counts.items(), key=lambda x: -x[1]):
    print(f"  {r}: {c}")
print(f"Total unique players found: {len(player_ranks)}")
print(f"Players WITH rank: {sum(1 for v in player_ranks.values() if v[0])}")
print(f"Players WITHOUT rank: {sum(1 for v in player_ranks.values() if not v[0])}")

# 3. Check extra match data source_player ranks
print("\n=== Source Player Ranks from Extra Matches ===")
extra_rank_counts = {}
for i in range(8):
    f = f"output/extra_match_data/shard_{i}/match_details.json"
    try:
        data = json.load(open(f, 'r', encoding='utf-8'))
        for m in data:
            sp = m.get("source_player", {})
            rank = sp.get("rank", "")
            if rank:
                extra_rank_counts[rank] = extra_rank_counts.get(rank, 0) + 1
    except:
        pass

print("Extra match source player ranks:")
for r, c in sorted(extra_rank_counts.items(), key=lambda x: -x[1]):
    print(f"  {r}: {c}")
if not extra_rank_counts:
    print("  (No rank data yet - extra players may not have rank in source_player)")

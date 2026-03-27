"""
完整的Extra vs PC比赛数据重叠分析（修正版）
使用正确的字段名: player_summaries.profile_id, round_records
"""
import json, glob, os, time

BASE = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 70)
    print("Extra vs PC Match Data Overlap Analysis (Final)")
    print("=" * 70)
    
    # 1. PC matches
    print("\n[1/4] Loading PC shard matches...")
    t0 = time.time()
    pc_match_ids = set()
    pc_player_ids = set()
    pc_total = 0
    pc_rounds = 0
    
    for sf in sorted(glob.glob(os.path.join(BASE, "output/match_data/shard_*/match_details.json"))):
        name = sf.split(os.sep)[-2]
        try:
            with open(sf, "r", encoding="utf-8") as f:
                matches = json.load(f)
            for m in matches:
                mid = m.get("match_id", "").lower()
                if mid:
                    pc_match_ids.add(mid)
                pc_total += 1
                # Extract players from player_summaries
                for ps in m.get("player_summaries", []):
                    pid = ps.get("profile_id", "").lower()
                    if pid:
                        pc_player_ids.add(pid)
                # Count rounds
                pc_rounds += m.get("total_rounds", 0)
            print(f"  {name}: {len(matches)} matches")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
    
    print(f"  Total: {pc_total} matches, {len(pc_match_ids)} unique, {len(pc_player_ids)} players, {pc_rounds} rounds ({time.time()-t0:.1f}s)")
    
    # 2. Known players
    print("\n[2/4] Loading known player lists...")
    lb_players = set()
    lb_file = os.path.join(BASE, "output/leaderboard/leaderboard_full.json")
    if os.path.exists(lb_file):
        with open(lb_file, "r", encoding="utf-8") as f:
            for p in json.load(f):
                pid = (p.get("profileId") or p.get("profile_id") or "").lower()
                if pid:
                    lb_players.add(pid)
    
    extra_list = set()
    ef = os.path.join(BASE, "output/extra_match_data/_extra_players.json")
    if os.path.exists(ef):
        with open(ef, "r", encoding="utf-8") as f:
            for p in json.load(f):
                pid = p.get("profileId", "").lower()
                if pid:
                    extra_list.add(pid)
    
    all_known = lb_players | extra_list | pc_player_ids
    print(f"  Leaderboard: {len(lb_players)}, Extra list: {len(extra_list)}, PC match players: {len(pc_player_ids)}")
    print(f"  All known: {len(all_known)}")
    
    # 3. Extra matches
    print("\n[3/4] Loading Extra shard matches...")
    t1 = time.time()
    extra_match_ids = set()
    extra_player_ids = set()
    extra_total = 0
    extra_rounds = 0
    
    for sf in sorted(glob.glob(os.path.join(BASE, "output/extra_match_data/shard_*/match_details.json"))):
        name = sf.split(os.sep)[-2]
        try:
            with open(sf, "r", encoding="utf-8") as f:
                matches = json.load(f)
            for m in matches:
                mid = m.get("match_id", "").lower()
                if mid:
                    extra_match_ids.add(mid)
                extra_total += 1
                for ps in m.get("player_summaries", []):
                    pid = ps.get("profile_id", "").lower()
                    if pid:
                        extra_player_ids.add(pid)
                extra_rounds += m.get("total_rounds", 0)
            print(f"  {name}: {len(matches)} matches")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
    
    print(f"  Total: {extra_total} matches, {len(extra_match_ids)} unique, {len(extra_player_ids)} players, {extra_rounds} rounds ({time.time()-t1:.1f}s)")
    
    # 4. Core analysis
    print("\n" + "=" * 70)
    print("[4/4] CORE OVERLAP ANALYSIS")
    print("=" * 70)
    
    overlap = pc_match_ids & extra_match_ids
    new_matches = extra_match_ids - pc_match_ids
    
    print(f"\n--- Match Overlap ---")
    print(f"  PC unique matches: {len(pc_match_ids):,}")
    print(f"  Extra unique matches: {len(extra_match_ids):,}")
    print(f"  Overlapping: {len(overlap):,} ({len(overlap)/len(extra_match_ids)*100:.1f}% of Extra)")
    print(f"  NEW matches (only in Extra): {len(new_matches):,} ({len(new_matches)/len(extra_match_ids)*100:.1f}% of Extra)")
    
    # Player discovery from extra matches
    new_players = extra_player_ids - all_known
    print(f"\n--- Player Discovery ---")
    print(f"  Players in Extra matches: {len(extra_player_ids):,}")
    print(f"  Already known: {len(extra_player_ids & all_known):,}")
    print(f"  NEW players (never seen before): {len(new_players):,} ({len(new_players)/len(extra_player_ids)*100:.1f}% of Extra players)")
    
    # Completed extra players count
    completed = 0
    for pf in glob.glob(os.path.join(BASE, "output/extra_match_data/_shard_*_progress.json")):
        try:
            with open(pf, "r", encoding="utf-8") as f:
                completed += len(json.load(f).get("completed_players", []))
        except:
            pass
    
    print(f"\n--- Per-Player Efficiency ---")
    print(f"  Completed Extra players: {completed}")
    if completed > 0:
        print(f"  Matches per Extra player: {len(extra_match_ids)/completed:.1f}")
        print(f"  NEW matches per Extra player: {len(new_matches)/completed:.2f}")
        print(f"  NEW players per Extra player: {len(new_players)/completed:.2f}")
    
    print(f"\n--- PROJECTION (all 63,199 Extra players) ---")
    if completed > 0:
        proj_total = int(len(extra_match_ids) / completed * 63199)
        proj_new = int(len(new_matches) / completed * 63199)
        proj_new_players = int(len(new_players) / completed * 63199)
        proj_new_rounds = int(extra_rounds / extra_total * proj_new) if extra_total > 0 else 0
        
        print(f"  Projected total matches: ~{proj_total:,}")
        print(f"  Projected NEW matches: ~{proj_new:,}")
        print(f"  Projected NEW players: ~{proj_new_players:,}")
        print(f"  Projected NEW round records: ~{proj_new_rounds:,}")
    
    print(f"\n--- PLAN C IMPACT ---")
    overlap_pct = len(overlap) / len(extra_match_ids) * 100 if extra_match_ids else 0
    new_pct = len(new_matches) / len(extra_match_ids) * 100 if extra_match_ids else 0
    
    print(f"  Match overlap rate: {overlap_pct:.1f}%")
    print(f"  NEW match rate: {new_pct:.1f}%")
    
    if new_pct > 50:
        print(f"\n  >>> CONCLUSION: Plan C will LOSE ~{new_pct:.0f}% of Extra match data!")
        print(f"  >>> That's ~{proj_new:,} unique matches and ~{proj_new_rounds:,} round records!")
        if proj_new_players > 0:
            print(f"  >>> Plus ~{proj_new_players:,} newly discovered players!")
        print(f"  >>> RECOMMENDATION: Do NOT use Plan C. Keep full match detail crawling.")
        print(f"  >>> Use Plan A (reduce delay) instead for speedup.")
    elif new_pct > 20:
        print(f"\n  >>> Plan C will lose a moderate amount ({new_pct:.0f}%) of data.")
        print(f"  >>> Consider a middle-ground approach.")
    else:
        print(f"\n  >>> Plan C is safe - only {new_pct:.0f}% data loss.")
    
    # Combined dataset stats
    all_matches = pc_match_ids | extra_match_ids
    all_players = pc_player_ids | extra_player_ids
    print(f"\n--- COMBINED DATASET ---")
    print(f"  Total unique matches (PC+Extra): {len(all_matches):,}")
    print(f"  Total unique players (PC+Extra): {len(all_players):,}")
    print(f"  PC-only matches: {len(pc_match_ids - extra_match_ids):,}")
    print(f"  Extra-only matches: {len(new_matches):,}")
    print(f"  Shared matches: {len(overlap):,}")


if __name__ == "__main__":
    main()

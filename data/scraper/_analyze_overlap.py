"""
分析已收集的Extra玩家数据：他们的比赛和PC排行榜玩家的比赛重叠率是多少？
是否包含全新的比赛和全新的玩家？

思路：不需要再访问stats.cc，直接对比已收集的数据：
- PC分片(shard_0~4): 排行榜玩家的比赛
- Extra分片(shard_0~7): 额外玩家的比赛
"""

import json
import glob
import os
import time
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 70)
    print("Extra 玩家数据重叠分析（基于已采集数据）")
    print("=" * 70)
    
    # ============================================================
    # 1. 加载PC排行榜玩家数据
    # ============================================================
    print("\n[1/5] 加载 PC 排行榜玩家的比赛数据...")
    t0 = time.time()
    
    pc_match_ids = set()
    pc_player_ids = set()  # 出现在PC比赛中的所有玩家
    pc_match_count = 0
    pc_round_count = 0
    
    for shard_file in sorted(glob.glob(os.path.join(BASE_DIR, "output/match_data/shard_*/match_details.json"))):
        shard_name = shard_file.split(os.sep)[-2]
        try:
            with open(shard_file, "r", encoding="utf-8") as f:
                matches = json.load(f)
            
            for m in matches:
                mid = (m.get("match_id") or m.get("matchId") or m.get("id", "")).lower()
                if mid:
                    pc_match_ids.add(mid)
                pc_match_count += 1
                
                # 提取参与者
                rounds = m.get("rounds") or m.get("round_data") or []
                if isinstance(rounds, list):
                    pc_round_count += len(rounds)
                    for rnd in rounds:
                        if isinstance(rnd, dict):
                            for team_key in ["team1", "team2", "attackers", "defenders", "teams"]:
                                team = rnd.get(team_key)
                                if isinstance(team, list):
                                    for player in team:
                                        if isinstance(player, dict):
                                            pid = (player.get("profileId") or player.get("profile_id") or "").lower()
                                            if pid:
                                                pc_player_ids.add(pid)
                                elif isinstance(team, dict):
                                    players = team.get("players") or team.get("members") or []
                                    for player in players:
                                        if isinstance(player, dict):
                                            pid = (player.get("profileId") or player.get("profile_id") or "").lower()
                                            if pid:
                                                pc_player_ids.add(pid)
            
            print(f"  {shard_name}: {len(matches)} matches loaded")
        except Exception as e:
            print(f"  {shard_name}: ERROR - {e}")
    
    print(f"  总计: {pc_match_count} matches, {len(pc_match_ids)} unique IDs, {len(pc_player_ids)} unique players, {pc_round_count} rounds")
    print(f"  耗时: {time.time()-t0:.1f}s")
    
    # ============================================================
    # 2. 加载已知玩家列表
    # ============================================================
    print("\n[2/5] 加载已知玩家列表...")
    
    # PC排行榜玩家
    lb_players = set()
    lb_file = os.path.join(BASE_DIR, "output/leaderboard/leaderboard_full.json")
    if os.path.exists(lb_file):
        with open(lb_file, "r", encoding="utf-8") as f:
            for p in json.load(f):
                pid = (p.get("profileId") or p.get("profile_id") or p.get("id", "")).lower()
                if pid:
                    lb_players.add(pid)
    
    # Extra玩家列表
    extra_players = set()
    extra_file = os.path.join(BASE_DIR, "output/extra_match_data/_extra_players.json")
    if os.path.exists(extra_file):
        with open(extra_file, "r", encoding="utf-8") as f:
            for p in json.load(f):
                pid = p.get("profileId", "").lower()
                if pid:
                    extra_players.add(pid)
    
    all_known_players = lb_players | extra_players | pc_player_ids
    print(f"  PC排行榜玩家: {len(lb_players)}")
    print(f"  Extra玩家列表: {len(extra_players)}")
    print(f"  PC比赛中的玩家: {len(pc_player_ids)}")
    print(f"  总已知玩家: {len(all_known_players)}")
    
    # ============================================================
    # 3. 加载Extra玩家的比赛数据
    # ============================================================
    print("\n[3/5] 加载 Extra 玩家的比赛数据...")
    t1 = time.time()
    
    extra_match_ids = set()
    extra_players_in_matches = set()
    extra_match_count = 0
    extra_round_count = 0
    extra_match_details = []  # 保存用于详细分析
    
    for shard_file in sorted(glob.glob(os.path.join(BASE_DIR, "output/extra_match_data/shard_*/match_details.json"))):
        shard_name = shard_file.split(os.sep)[-2]
        try:
            with open(shard_file, "r", encoding="utf-8") as f:
                matches = json.load(f)
            
            for m in matches:
                mid = (m.get("match_id") or m.get("matchId") or m.get("id", "")).lower()
                if mid:
                    extra_match_ids.add(mid)
                extra_match_count += 1
                extra_match_details.append(m)
                
                # 提取参与者
                rounds = m.get("rounds") or m.get("round_data") or []
                if isinstance(rounds, list):
                    extra_round_count += len(rounds)
                    for rnd in rounds:
                        if isinstance(rnd, dict):
                            for team_key in ["team1", "team2", "attackers", "defenders", "teams"]:
                                team = rnd.get(team_key)
                                if isinstance(team, list):
                                    for player in team:
                                        if isinstance(player, dict):
                                            pid = (player.get("profileId") or player.get("profile_id") or "").lower()
                                            if pid:
                                                extra_players_in_matches.add(pid)
                                elif isinstance(team, dict):
                                    players = team.get("players") or team.get("members") or []
                                    for player in players:
                                        if isinstance(player, dict):
                                            pid = (player.get("profileId") or player.get("profile_id") or "").lower()
                                            if pid:
                                                extra_players_in_matches.add(pid)
            
            print(f"  {shard_name}: {len(matches)} matches loaded")
        except Exception as e:
            print(f"  {shard_name}: ERROR - {e}")
    
    print(f"  总计: {extra_match_count} matches, {len(extra_match_ids)} unique IDs, {len(extra_players_in_matches)} unique players, {extra_round_count} rounds")
    print(f"  耗时: {time.time()-t1:.1f}s")
    
    # ============================================================
    # 4. 核心分析：重叠率
    # ============================================================
    print("\n" + "=" * 70)
    print("[4/5] 核心重叠分析")
    print("=" * 70)
    
    # 比赛重叠
    overlapping_matches = pc_match_ids & extra_match_ids
    new_matches = extra_match_ids - pc_match_ids
    
    print(f"\n--- 比赛重叠分析 ---")
    print(f"  Extra 中的唯一比赛: {len(extra_match_ids)}")
    print(f"  与 PC 数据重叠的比赛: {len(overlapping_matches)} ({len(overlapping_matches)/len(extra_match_ids)*100:.1f}%)" if extra_match_ids else "  无数据")
    print(f"  Extra 中的全新比赛: {len(new_matches)} ({len(new_matches)/len(extra_match_ids)*100:.1f}%)" if extra_match_ids else "  无数据")
    
    # 玩家重叠
    new_players_from_extra = extra_players_in_matches - all_known_players
    
    print(f"\n--- 玩家发现分析 ---")
    print(f"  Extra 比赛中的唯一玩家: {len(extra_players_in_matches)}")
    print(f"  已知玩家(排行榜+Extra列表+PC比赛): {len(all_known_players)}")
    print(f"  全新发现的玩家: {len(new_players_from_extra)} ({len(new_players_from_extra)/len(extra_players_in_matches)*100:.1f}%)" if extra_players_in_matches else "  无数据")
    
    # 计算每个已完成的Extra玩家贡献的新比赛数
    # 从进度文件获取已完成Extra玩家数
    completed_extra = 0
    for prog_file in glob.glob(os.path.join(BASE_DIR, "output/extra_match_data/_shard_*_progress.json")):
        try:
            with open(prog_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                completed_extra += len(data.get("completed_players", []))
        except:
            pass
    
    if completed_extra > 0 and len(new_matches) > 0:
        new_per_player = len(new_matches) / completed_extra
        print(f"\n--- 效率分析 ---")
        print(f"  已完成的 Extra 玩家数: {completed_extra}")
        print(f"  每个 Extra 玩家平均贡献: {len(extra_match_ids)/completed_extra:.1f} 场比赛")
        print(f"  其中全新比赛平均: {new_per_player:.2f} 场/人")
        print(f"  新比赛中的新玩家平均: {len(new_players_from_extra)/completed_extra:.2f} 人/人")
    
    # ============================================================
    # 5. 对方案C的影响评估
    # ============================================================
    print("\n" + "=" * 70)
    print("[5/5] 对方案C的影响评估")
    print("=" * 70)
    
    overlap_rate = len(overlapping_matches) / len(extra_match_ids) * 100 if extra_match_ids else 0
    new_rate = len(new_matches) / len(extra_match_ids) * 100 if extra_match_ids else 0
    
    print(f"\n  比赛重叠率: {overlap_rate:.1f}%")
    print(f"  新比赛比率: {new_rate:.1f}%")
    
    if new_rate > 0 and completed_extra > 0:
        # 预测：如果采集全部63199个Extra玩家的比赛
        projected_new_matches = int(new_per_player * 63199)
        projected_new_players = int(len(new_players_from_extra) / completed_extra * 63199)
        
        print(f"\n  [预测] 如果采集全部 63,199 个 Extra 玩家:")
        print(f"     预计总比赛数: ~{int(len(extra_match_ids)/completed_extra*63199):,}")
        print(f"     预计全新比赛: ~{projected_new_matches:,}")
        print(f"     预计新发现玩家: ~{projected_new_players:,}")
        
        if overlap_rate >= 80:
            print(f"\n  [OK] C: overlap {overlap_rate:.1f}% high, most match data already collected")
            print(f"     C will lose ~{projected_new_matches:,} new matches")
            print(f"     But keeps all {len(pc_match_ids):,} + {len(overlapping_matches):,} = {len(pc_match_ids)+len(overlapping_matches):,} existing matches")
        elif overlap_rate >= 50:
            print(f"\n  [WARN] C: overlap {overlap_rate:.1f}%, about {new_rate:.0f}% matches are new")
            print(f"     C will lose ~{projected_new_matches:,} new matches")
            print(f"     And ~{projected_new_players:,} new players in those matches")
            print(f"     Suggest: keep match detail crawl, use plan A to reduce delay")
        else:
            print(f"\n  [DANGER] C: overlap only {overlap_rate:.1f}%!")
            print(f"     Extra players bring lots of new match data ({new_rate:.0f}%)")
            print(f"     C will lose ~{projected_new_matches:,} new matches and ~{projected_new_players:,} new players")
            print(f"     [X] Strongly against plan C, suggest full crawl + plan A")
    
    # 额外分析：新比赛的回合数据
    if extra_match_details:
        new_match_rounds = 0
        for m in extra_match_details:
            mid = (m.get("match_id") or m.get("matchId") or m.get("id", "")).lower()
            if mid in new_matches:
                rounds = m.get("rounds") or m.get("round_data") or []
                if isinstance(rounds, list):
                    new_match_rounds += len(rounds)
        
        if new_matches:
            print(f"\n  [Detail] New match details:")
            print(f"     新比赛中的回合数: {new_match_rounds}")
            print(f"     每场新比赛平均回合: {new_match_rounds/len(new_matches):.1f}" if new_matches else "")
    
    print(f"\n分析完成！")


if __name__ == "__main__":
    main()

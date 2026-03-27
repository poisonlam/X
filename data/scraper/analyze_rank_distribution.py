"""
R6 Siege 玩家段位分布总览分析
数据来源：
1. PC排行榜 (leaderboard_full.json) — rank字段直接可用
2. 已采集比赛 (match_data) — source_player有rank, 其他玩家无rank
3. 额外玩家列表 (_extra_players.json) — 无rank，但知道出现次数
"""

import json
import os
from pathlib import Path
from collections import defaultdict, OrderedDict
from datetime import datetime

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# 段位名称标准化 (leaderboard格式 -> 显示格式)
def normalize_rank(rank_raw):
    """把 champion, diamond-i, diamond-ii 等标准化"""
    if not rank_raw:
        return ""
    r = rank_raw.strip().lower()
    # 罗马数字映射
    roman = {"i": "I", "ii": "II", "iii": "III", "iv": "IV", "v": "V"}
    parts = r.split("-")
    if len(parts) == 2:
        tier = parts[0].capitalize()
        level = roman.get(parts[1], parts[1].upper())
        return f"{tier} {level}"
    elif len(parts) == 1:
        return parts[0].capitalize()
    return rank_raw

TIER_ORDER = ["Copper", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond", "Champion"]

def get_tier(rank_name):
    if not rank_name:
        return "Unknown"
    for tier in TIER_ORDER:
        if rank_name.startswith(tier):
            return tier
    if rank_name.lower() == "champion":
        return "Champion"
    return "Unknown"

def get_rank_sort_key(rank):
    full_order = []
    for tier in ["Copper", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond"]:
        for level in ["V", "IV", "III", "II", "I"]:
            full_order.append(f"{tier} {level}")
    full_order.append("Champion")
    try:
        return full_order.index(rank)
    except ValueError:
        return -1

def analyze():
    print(f"\n{'='*70}")
    print(f"  R6 Siege 玩家段位分布总览分析")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # ===========================
    # 第一部分: 收集所有已知段位信息
    # ===========================
    
    # 所有玩家: profileId -> {name, rank, rankPoints, source}
    all_players = {}
    
    # 1. 排行榜数据 — 最完整的段位信息源
    print("📋 加载排行榜数据...")
    lb_file = OUTPUT_DIR / "leaderboard" / "leaderboard_full.json"
    if lb_file.exists():
        lb_data = json.load(open(lb_file, 'r', encoding='utf-8'))
        for p in lb_data:
            pid = p.get("profileId", "")
            if pid:
                all_players[pid] = {
                    "name": p.get("displayName", ""),
                    "rank": normalize_rank(p.get("rank", "")),
                    "rankPoints": p.get("rankPoints", 0),
                    "source": "leaderboard"
                }
        print(f"  PC排行榜: {len(lb_data)} 玩家")
    
    # 2. 已采集比赛中的 source_player 段位
    print("📋 扫描比赛数据中的段位信息...")
    match_players_total = set()
    match_source_players = 0
    
    for label, match_dir, shard_range in [
        ("PC排行榜比赛", OUTPUT_DIR / "match_data", range(5)),
        ("额外玩家比赛", OUTPUT_DIR / "extra_match_data", range(8))
    ]:
        if not match_dir.exists():
            continue
        dir_new = 0
        for si in shard_range:
            mf = match_dir / f"shard_{si}" / "match_details.json"
            if not mf.exists():
                continue
            try:
                data = json.load(open(mf, 'r', encoding='utf-8'))
                for m in data:
                    # source_player 有段位
                    sp = m.get("source_player", {})
                    sp_id = sp.get("profile_id", sp.get("profileId", ""))
                    sp_rank = normalize_rank(sp.get("rank", ""))
                    sp_rp = sp.get("rankPoints", 0)
                    
                    if sp_id and sp_rank:
                        if sp_id not in all_players or (sp_rp > all_players[sp_id].get("rankPoints", 0)):
                            all_players[sp_id] = {
                                "name": sp.get("username", sp.get("displayName", "")),
                                "rank": sp_rank,
                                "rankPoints": sp_rp,
                                "source": "match_source"
                            }
                            match_source_players += 1
                    
                    # player_summaries 中的所有玩家（无段位，但记录存在）
                    for ps in m.get("player_summaries", []):
                        p_id = ps.get("profile_id", "")
                        if p_id:
                            match_players_total.add(p_id)
                            if p_id not in all_players:
                                all_players[p_id] = {
                                    "name": ps.get("username", ""),
                                    "rank": "",
                                    "rankPoints": 0,
                                    "source": "match_participant"
                                }
            except Exception as e:
                pass
        print(f"  {label}: 扫描完成")
    
    # 3. 额外玩家列表
    ep_file = OUTPUT_DIR / "extra_match_data" / "_extra_players.json"
    extra_players_list = []
    if ep_file.exists():
        extra_players_list = json.load(open(ep_file, 'r', encoding='utf-8'))
        for ep in extra_players_list:
            pid = ep.get("profileId", "")
            if pid and pid not in all_players:
                all_players[pid] = {
                    "name": ep.get("displayName", ""),
                    "rank": "",
                    "rankPoints": 0,
                    "source": "extra_list"
                }
    
    # ===========================
    # 第二部分: 统计分析
    # ===========================
    
    total = len(all_players)
    has_rank = {pid: info for pid, info in all_players.items() if info.get("rank")}
    no_rank = {pid: info for pid, info in all_players.items() if not info.get("rank")}
    
    print(f"\n{'='*70}")
    print(f"  数据总量概况")
    print(f"{'='*70}\n")
    print(f"  总唯一玩家数: {total:,}")
    print(f"  有段位信息:   {len(has_rank):,} ({len(has_rank)/total*100:.1f}%)")
    print(f"  无段位信息:   {len(no_rank):,} ({len(no_rank)/total*100:.1f}%)")
    print(f"  (无段位玩家 = 比赛中出现但尚未采集个人数据的玩家)")
    
    # 有段位的玩家分布
    print(f"\n{'='*70}")
    print(f"  有段位玩家的段位分布 ({len(has_rank):,} 人)")
    print(f"{'='*70}\n")
    
    tier_counts = defaultdict(int)
    rank_counts = defaultdict(int)
    tier_rp = defaultdict(list)
    
    for pid, info in has_rank.items():
        rank = info["rank"]
        rank_counts[rank] += 1
        tier = get_tier(rank)
        tier_counts[tier] += 1
        rp = info.get("rankPoints", 0)
        if rp > 0:
            tier_rp[tier].append(rp)
    
    # 大段位分布表
    tier_icons = {
        "Champion": "👑", "Diamond": "💎", "Emerald": "💚",
        "Platinum": "🔷", "Gold": "🥇", "Silver": "🥈",
        "Bronze": "🥉", "Copper": "🟤", "Unknown": "❓"
    }
    
    max_count = max(tier_counts.values()) if tier_counts else 1
    print(f"{'':>3} {'段位':>10}  {'人数':>8}  {'占比':>8}  {'RP范围':>18}  {'平均RP':>8}  分布")
    print(f"{'':>3} {'-'*10}  {'-'*8}  {'-'*8}  {'-'*18}  {'-'*8}  {'-'*25}")
    
    for tier in TIER_ORDER:
        count = tier_counts.get(tier, 0)
        if count == 0:
            continue
        pct = count / len(has_rank) * 100
        icon = tier_icons.get(tier, "")
        rps = tier_rp.get(tier, [])
        rp_range = f"{min(rps)}-{max(rps)}" if rps else "N/A"
        avg_rp = f"{sum(rps)/len(rps):.0f}" if rps else "N/A"
        bar_len = int(count / max_count * 25)
        bar = "█" * bar_len
        print(f"{icon:>3} {tier:>10}  {count:>8,}  {pct:>7.1f}%  {rp_range:>18}  {avg_rp:>8}  {bar}")
    
    # 详细段位分布
    print(f"\n  详细段位分布:")
    sorted_ranks = sorted(rank_counts.items(), key=lambda x: get_rank_sort_key(x[0]))
    max_rc = max(rank_counts.values()) if rank_counts else 1
    for rank, count in sorted_ranks:
        pct = count / len(has_rank) * 100
        bar_len = int(count / max_rc * 25)
        bar = "▓" * bar_len
        print(f"  {rank:>16}  {count:>8,}  ({pct:>5.1f}%)  {bar}")
    
    # ===========================
    # 第三部分: 采集进度与预估
    # ===========================
    
    print(f"\n{'='*70}")
    print(f"  采集进度与预估")
    print(f"{'='*70}\n")
    
    # PC排行榜采集进度
    pc_done = 0
    pc_total = len(lb_data) if lb_file.exists() else 10015
    for i in range(5):
        pf = OUTPUT_DIR / "match_data" / f"_shard_{i}_progress.json"
        if pf.exists():
            d = json.load(open(pf, 'r', encoding='utf-8'))
            pc_done += len(d.get("completed_players", []))
    
    # 额外玩家采集进度
    extra_done = 0
    extra_total = len(extra_players_list) if extra_players_list else 63199
    for i in range(8):
        pf = OUTPUT_DIR / "extra_match_data" / f"_shard_{i}_progress.json"
        if pf.exists():
            d = json.load(open(pf, 'r', encoding='utf-8'))
            extra_done += len(d.get("completed_players", []))
    
    print(f"  PC排行榜比赛采集: {pc_done:,}/{pc_total:,} ({pc_done/pc_total*100:.1f}%)")
    print(f"  额外玩家比赛采集: {extra_done:,}/{extra_total:,} ({extra_done/extra_total*100:.1f}%)")
    print(f"  比赛中发现的参赛玩家: {len(match_players_total):,}")
    
    print(f"\n  📊 关键洞察:")
    print(f"  - 排行榜 {pc_total:,} 人全部集中在 Diamond III 以上")
    print(f"  - 这些高段位玩家的比赛中出现了 {len(match_players_total):,} 个不同玩家")
    print(f"  - 其中 {extra_total:,} 人不在排行榜中，正在采集他们的比赛数据")
    print(f"  - 额外玩家覆盖 Champion 到 Copper 各段位，是扩展低段位数据的关键")
    print(f"  - 每个额外玩家的比赛又会引入更多新玩家（滚雪球效应）")
    
    print(f"\n  📈 预估完成后数据规模:")
    print(f"  - 直接采集玩家: ~{pc_total + extra_total:,}")
    print(f"  - 比赛场次: ~{(pc_total*9 + extra_total*5)//1000*1000:,}+")
    print(f"  - 涉及唯一玩家: 预计 200,000-500,000")
    print(f"  - 段位覆盖: Champion → Copper 全段位")
    
    # ===========================
    # 第四部分: 已知段位的RP分布
    # ===========================
    
    print(f"\n{'='*70}")
    print(f"  RP (Rank Points) 分布分析")
    print(f"{'='*70}\n")
    
    all_rps = [info["rankPoints"] for info in has_rank.values() if info.get("rankPoints", 0) > 0]
    if all_rps:
        all_rps.sort()
        print(f"  RP 统计:")
        print(f"    最低: {min(all_rps)}")
        print(f"    最高: {max(all_rps)}")
        print(f"    平均: {sum(all_rps)/len(all_rps):.0f}")
        print(f"    中位数: {all_rps[len(all_rps)//2]}")
        print(f"    P25: {all_rps[len(all_rps)//4]}")
        print(f"    P75: {all_rps[len(all_rps)*3//4]}")
        
        # RP 区间直方图
        print(f"\n  RP 区间分布:")
        buckets = defaultdict(int)
        for rp in all_rps:
            bucket = (rp // 200) * 200
            buckets[bucket] += 1
        
        max_bucket = max(buckets.values())
        for bucket_start in sorted(buckets.keys()):
            count = buckets[bucket_start]
            pct = count / len(all_rps) * 100
            bar_len = int(count / max_bucket * 30)
            bar = "█" * bar_len
            print(f"    {bucket_start:>5}-{bucket_start+199:<5}: {count:>5} ({pct:>5.1f}%) {bar}")
    
    print(f"\n{'='*70}")
    print(f"  分析完成!")
    print(f"{'='*70}")
    
    return {
        "total_players": total,
        "has_rank": len(has_rank),
        "no_rank": len(no_rank),
        "tier_counts": dict(tier_counts),
        "rank_counts": dict(rank_counts)
    }

if __name__ == "__main__":
    result = analyze()

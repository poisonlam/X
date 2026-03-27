"""
分析实际采集数据中match_id的冗余情况
- 同一个match_id被几个不同的分片重复采集了？
- 冗余请求占总请求的比例是多少？
"""
import json, glob, os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 70)
    print("MATCH REDUNDANCY ANALYSIS")
    print("=" * 70)
    
    # ============================================================
    # 1. PC shards: 检查跨分片重复
    # ============================================================
    print("\n[1/3] PC Leaderboard Shards - Cross-Shard Redundancy")
    print("-" * 70)
    
    pc_match_by_shard = defaultdict(set)  # match_id -> set of shard_ids
    pc_total_records = 0  # 总记录数（含重复）
    pc_unique_matches = set()
    
    for sf in sorted(glob.glob(os.path.join(BASE, "output/match_data/shard_*/match_details.json"))):
        shard_name = sf.split(os.sep)[-2]  # shard_0, shard_1, ...
        try:
            with open(sf, "r", encoding="utf-8") as f:
                matches = json.load(f)
            for m in matches:
                mid = m.get("match_id", "")
                if mid:
                    pc_match_by_shard[mid].add(shard_name)
                    pc_unique_matches.add(mid)
                pc_total_records += 1
            print(f"  {shard_name}: {len(matches)} match records")
        except Exception as e:
            print(f"  {shard_name}: ERROR - {e}")
    
    # 统计重复
    dup_counts = Counter()
    for mid, shards in pc_match_by_shard.items():
        dup_counts[len(shards)] += 1
    
    total_dup_records = sum((count - 1) * freq for count, freq in dup_counts.items())
    dup_rate = total_dup_records / pc_total_records * 100 if pc_total_records > 0 else 0
    
    print(f"\n  Total match records (all shards): {pc_total_records}")
    print(f"  Unique match IDs: {len(pc_unique_matches)}")
    print(f"  Duplicate records (same match in multiple shards): {total_dup_records}")
    print(f"  Duplication rate: {dup_rate:.1f}%")
    print(f"  Wasted HTTP requests (match detail): ~{total_dup_records}")
    
    print(f"\n  Cross-shard overlap distribution:")
    for count in sorted(dup_counts.keys()):
        freq = dup_counts[count]
        print(f"    Match in {count} shard(s): {freq} matches ({freq/len(pc_unique_matches)*100:.1f}%)")
    
    # 分析哪些分片对之间重叠最多
    pair_overlap = Counter()
    for mid, shards in pc_match_by_shard.items():
        if len(shards) > 1:
            shard_list = sorted(shards)
            for i in range(len(shard_list)):
                for j in range(i+1, len(shard_list)):
                    pair_overlap[(shard_list[i], shard_list[j])] += 1
    
    if pair_overlap:
        print(f"\n  Top shard pair overlaps:")
        for (s1, s2), count in pair_overlap.most_common(10):
            print(f"    {s1} <-> {s2}: {count} shared matches")
    
    # ============================================================
    # 2. Extra shards: 检查跨分片重复
    # ============================================================
    print(f"\n[2/3] Extra Player Shards - Cross-Shard Redundancy")
    print("-" * 70)
    
    extra_match_by_shard = defaultdict(set)
    extra_total_records = 0
    extra_unique_matches = set()
    
    for sf in sorted(glob.glob(os.path.join(BASE, "output/extra_match_data/shard_*/match_details.json"))):
        shard_name = sf.split(os.sep)[-2]
        try:
            with open(sf, "r", encoding="utf-8") as f:
                matches = json.load(f)
            for m in matches:
                mid = m.get("match_id", "")
                if mid:
                    extra_match_by_shard[mid].add(shard_name)
                    extra_unique_matches.add(mid)
                extra_total_records += 1
            print(f"  {shard_name}: {len(matches)} match records")
        except Exception as e:
            print(f"  {shard_name}: ERROR - {e}")
    
    extra_dup_counts = Counter()
    for mid, shards in extra_match_by_shard.items():
        extra_dup_counts[len(shards)] += 1
    
    extra_dup_records = sum((count - 1) * freq for count, freq in extra_dup_counts.items())
    extra_dup_rate = extra_dup_records / extra_total_records * 100 if extra_total_records > 0 else 0
    
    print(f"\n  Total match records: {extra_total_records}")
    print(f"  Unique match IDs: {len(extra_unique_matches)}")
    print(f"  Duplicate records: {extra_dup_records}")
    print(f"  Duplication rate: {extra_dup_rate:.1f}%")
    
    print(f"\n  Cross-shard overlap distribution:")
    for count in sorted(extra_dup_counts.keys()):
        freq = extra_dup_counts[count]
        print(f"    Match in {count} shard(s): {freq} matches ({freq/len(extra_unique_matches)*100:.1f}%)" if extra_unique_matches else f"    {count}: {freq}")
    
    # ============================================================
    # 3. PC <-> Extra 交叉重复
    # ============================================================
    print(f"\n[3/3] PC <-> Extra Cross Redundancy")
    print("-" * 70)
    
    cross_overlap = pc_unique_matches & extra_unique_matches
    print(f"  PC unique matches: {len(pc_unique_matches)}")
    print(f"  Extra unique matches: {len(extra_unique_matches)}")
    print(f"  Cross-overlap (same match in both PC and Extra): {len(cross_overlap)}")
    
    if extra_unique_matches:
        print(f"  Cross-overlap as % of Extra: {len(cross_overlap)/len(extra_unique_matches)*100:.1f}%")
    if pc_unique_matches:
        print(f"  Cross-overlap as % of PC: {len(cross_overlap)/len(pc_unique_matches)*100:.1f}%")
    
    # ============================================================
    # Summary
    # ============================================================
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    
    total_records = pc_total_records + extra_total_records
    total_unique = len(pc_unique_matches | extra_unique_matches)
    total_wasted = (pc_total_records - len(pc_unique_matches)) + (extra_total_records - len(extra_unique_matches))
    
    print(f"  Total match detail records across all shards: {total_records}")
    print(f"  Total unique matches: {total_unique}")
    print(f"  Total redundant records: {total_wasted}")
    print(f"  Overall redundancy rate: {total_wasted/total_records*100:.1f}%")
    
    # 估算浪费的时间
    avg_delay_per_request = 3.7  # 2.5s base + ~1.2s random
    wasted_time_hours = total_wasted * avg_delay_per_request / 3600
    print(f"\n  Wasted request time (at ~3.7s/req): ~{wasted_time_hours:.1f} hours")
    
    # 如果实现跨分片去重，能节省多少
    print(f"\n  --- If cross-shard dedup were implemented ---")
    print(f"  Saved requests: {total_wasted}")
    print(f"  Saved time: ~{wasted_time_hours:.1f} hours")
    
    # 但注意：跨分片去重只影响future采集，不影响已经采集的
    # 计算对剩余任务的影响
    remaining_extra = 63199 - sum(1 for _ in glob.glob(os.path.join(BASE, "output/extra_match_data/_shard_*_progress.json")))
    
    print(f"\n  --- Projected impact on remaining {remaining_extra} Extra players ---")
    if extra_total_records > 0 and extra_unique_matches:
        current_dup_rate_extra = extra_dup_records / extra_total_records
        # Extra每个分片处理的平均比赛数
        avg_matches_per_extra_player = extra_total_records / max(1, len(set.union(*[shards for shards in extra_match_by_shard.values()]) if extra_match_by_shard else [set()]))
        
        # 但实际上重要的是：如果能在采集前检查全局已知match_id，能跳过多少请求
        print(f"  Current intra-Extra dup rate: {extra_dup_rate:.1f}%")
        print(f"  Cross PC-Extra overlap: {len(cross_overlap)} matches already known from PC")
        
        # 关键指标：如果Extra采集能实时读取PC和其他Extra分片的已知match_id
        # 在当前Extra数据中，有多少match已经在PC数据里了
        # 这些match本来可以跳过
        skippable = len(cross_overlap) + extra_dup_records
        if extra_total_records > 0:
            print(f"\n  Skippable requests with full cross-source dedup: {skippable}")
            print(f"  Skippable rate: {skippable/extra_total_records*100:.1f}%")


if __name__ == "__main__":
    main()

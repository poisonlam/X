"""快速扫描已采集数据中的段位信息"""
import json, os, glob

script_dir = os.path.dirname(os.path.abspath(__file__))

# 扫描 extra_match_data 的各分片
ranks = {}
unique_players = {}
total_matches = 0

for pattern in [
    os.path.join(script_dir, "output", "extra_match_data", "shard_*", "match_details.json"),
    os.path.join(script_dir, "output", "match_data", "shard_*", "match_details.json"),
]:
    for fpath in glob.glob(pattern):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            matches = data if isinstance(data, list) else [data]
            for m in matches:
                sp = m.get("source_player", {})
                rank = sp.get("rank", "")
                pid = sp.get("profileId", "")
                rp = sp.get("rankPoints", 0)
                
                if rank and pid:
                    if pid not in unique_players or rp > unique_players[pid].get("rankPoints", 0):
                        unique_players[pid] = {
                            "rank": rank,
                            "rankPoints": rp,
                            "displayName": sp.get("displayName", ""),
                        }
                    total_matches += 1
        except Exception as e:
            print(f"  Error reading {fpath}: {e}")

# 统计
from collections import Counter
rank_counts = Counter(p["rank"] for p in unique_players.values())

print(f"扫描完成:")
print(f"  总匹配数: {total_matches}")
print(f"  唯一玩家(有段位): {len(unique_players)}")
print()

print("段位分布:")
rank_order = [
    "champion", "diamond-i", "diamond-ii", "diamond-iii", "diamond-iv", "diamond-v",
    "emerald-i", "emerald-ii", "emerald-iii", "emerald-iv", "emerald-v",
    "platinum-i", "platinum-ii", "platinum-iii", "platinum-iv", "platinum-v",
    "gold-i", "gold-ii", "gold-iii", "gold-iv", "gold-v",
    "silver-i", "silver-ii", "silver-iii", "silver-iv", "silver-v",
    "bronze-i", "bronze-ii", "bronze-iii", "bronze-iv", "bronze-v",
    "copper-i", "copper-ii", "copper-iii", "copper-iv", "copper-v",
    "unranked",
]

total = len(unique_players)
for rank in rank_order:
    count = rank_counts.get(rank, 0)
    if count > 0:
        pct = count / total * 100
        bar = "#" * max(1, int(pct / 2))
        print(f"  {rank:<20} {count:>6,} ({pct:>6.2f}%) {bar}")

# 其他段位
for rank, count in sorted(rank_counts.items(), key=lambda x: -x[1]):
    if rank not in rank_order:
        pct = count / total * 100
        print(f"  {rank:<20} {count:>6,} ({pct:>6.2f}%)")

# 保存结果
output = {
    "total_unique_players": len(unique_players),
    "total_matches_scanned": total_matches,
    "rank_distribution": dict(rank_counts),
    "players": unique_players,
}
out_path = os.path.join(script_dir, "output", "rank_data")
os.makedirs(out_path, exist_ok=True)
with open(os.path.join(out_path, "collected_ranks.json"), "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=1)
print(f"\n已保存到: {os.path.join(out_path, 'collected_ranks.json')}")

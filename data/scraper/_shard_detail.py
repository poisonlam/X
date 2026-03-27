"""查看各shard进度详情"""
import json, glob, os, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.abspath(__file__))

def safe_load(path):
    for _ in range(3):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except:
            time.sleep(0.1)
    return None

print("=== Extra Shard 详情 ===")
total_completed = 0
all_completed_set = set()
for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/_shard_*_progress.json'))):
    data = safe_load(f)
    if data is None:
        print(f"  {os.path.basename(f)}: [读取失败]")
        continue
    cp = data.get('completed_players', [])
    tp = data.get('total_players', '?')
    fm = data.get('fetched_matches', 0)
    nm = data.get('new_matches', 0)
    total_completed += len(cp)
    all_completed_set.update(cp)
    print(f"  {os.path.basename(f)}: completed={len(cp)}, total={tp}, fetched_matches={fm}, new_matches={nm}")

print(f"\n  总计 completed (求和): {total_completed:,}")
print(f"  总计 completed (去重): {len(all_completed_set):,}")
print(f"  重复率: {(1 - len(all_completed_set)/total_completed)*100:.1f}%" if total_completed > 0 else "")

print("\n=== PC Shard 详情 ===")
pc_total = 0
pc_set = set()
for f in sorted(glob.glob(os.path.join(BASE, 'output/match_data/_shard_*_progress.json'))):
    data = safe_load(f)
    if data is None:
        print(f"  {os.path.basename(f)}: [读取失败]")
        continue
    cp = data.get('completed_players', [])
    tp = data.get('total_players', '?')
    fm = data.get('fetched_matches', 0)
    nm = data.get('new_matches', 0)
    pc_total += len(cp)
    pc_set.update(cp)
    print(f"  {os.path.basename(f)}: completed={len(cp)}, total={tp}, fetched_matches={fm}, new_matches={nm}")

print(f"\n  总计 completed (求和): {pc_total:,}")
print(f"  总计 completed (去重): {len(pc_set):,}")

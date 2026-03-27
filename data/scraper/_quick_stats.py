"""快速统计当前数据完整度"""
import json, os, glob, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))

def safe_load_json(path, retries=3):
    """安全读取JSON文件，支持重试（应对文件正在被写入的情况）"""
    for attempt in range(retries):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            if attempt < retries - 1:
                time.sleep(0.2)
            else:
                print(f"  [WARN] 无法读取 {os.path.basename(path)}: {e}")
                return None
    return None

# 1. PC对局数据
pc_match_ids = set()
pc_match_count = 0
for f in sorted(glob.glob(os.path.join(BASE, 'output/match_data/shard_*/match_details.json'))):
    data = safe_load_json(f)
    if data is None:
        continue
    pc_match_count += len(data)
    for m in data:
        mid = m.get('match_id', '')
        if mid:
            pc_match_ids.add(mid)

# 2. Extra对局数据
ex_match_ids = set()
ex_match_count = 0
for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/shard_*/match_details.json'))):
    data = safe_load_json(f)
    if data is None:
        continue
    ex_match_count += len(data)
    for m in data:
        mid = m.get('match_id', '')
        if mid:
            ex_match_ids.add(mid)

# 3. 所有对局中发现的玩家
all_player_ids = set()
for f in sorted(glob.glob(os.path.join(BASE, 'output/match_data/shard_*/match_details.json'))):
    data = safe_load_json(f)
    if data is None:
        continue
    for m in data:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id', '')
            if pid:
                all_player_ids.add(pid)
for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/shard_*/match_details.json'))):
    data = safe_load_json(f)
    if data is None:
        continue
    for m in data:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id', '')
            if pid:
                all_player_ids.add(pid)

overlap = pc_match_ids & ex_match_ids
combined = pc_match_ids | ex_match_ids

print("=" * 60)
print("数据完整度统计")
print("=" * 60)
print()
print(f"--- 对局数据 ---")
print(f"  PC 对局记录: {pc_match_count:,} (去重: {len(pc_match_ids):,})")
print(f"  Extra 对局记录: {ex_match_count:,} (去重: {len(ex_match_ids):,})")
print(f"  PC-Extra 重叠对局: {len(overlap):,}")
print(f"  合计唯一对局: {len(combined):,}")
print()
print(f"--- 玩家数据 ---")
print(f"  对局中出现的唯一玩家: {len(all_player_ids):,}")
print()

# 4. 检查还有多少玩家完全没被采到
try:
    extra_file = os.path.join(BASE, 'output/extra_match_data/_extra_players.json')
    extra_list = json.load(open(extra_file, encoding='utf-8'))
    extra_ids_in_list = set()
    for p in extra_list:
        pid = p.get('profileId', p.get('profile_id', ''))
        if pid:
            extra_ids_in_list.add(pid)
    
    # 已完成的extra玩家
    ex_completed = set()
    for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/_shard_*_progress.json'))):
        data = safe_load_json(f)
        if data is None:
            continue
        ex_completed.update(data.get('completed_players', []))
    
    ex_unique_completed = len(set(ex_completed))
    
    print(f"--- Extra 采集进度 ---")
    print(f"  Extra 玩家列表总数: {len(extra_ids_in_list):,}")
    print(f"  Extra completed (跨shard总计): {len(ex_completed):,}")
    print(f"  Extra completed (去重): {ex_unique_completed:,}")
    print(f"  Extra 列表中未完成: {len(extra_ids_in_list - ex_completed):,}")
    print(f"  Extra 对局中出现在列表中: {len(extra_ids_in_list & all_player_ids):,}")
except Exception as e:
    print(f"  Error loading extra list: {e}")

# PC completed
pc_completed = set()
for f in sorted(glob.glob(os.path.join(BASE, 'output/match_data/_shard_*_progress.json'))):
    data = safe_load_json(f)
    if data is None:
        continue
    pc_completed.update(data.get('completed_players', []))

print()
print(f"--- PC 采集进度 ---")
print(f"  PC completed (去重): {len(set(pc_completed)):,}")

# 有多少对局中的玩家完全不在任何列表里
all_completed = set(pc_completed) | set(ex_completed) if 'ex_completed' in dir() else set(pc_completed)
uncovered = all_player_ids - all_completed
print()
print(f"--- 覆盖度 ---")
print(f"  对局中出现但未被采集的玩家: {len(uncovered):,}")
print(f"  采集覆盖率: {(len(all_player_ids)-len(uncovered))/len(all_player_ids)*100:.1f}%")

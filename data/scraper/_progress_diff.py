"""对比30秒内的进度变化，确认Extra进程是否还在正常工作"""
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

def get_snapshot():
    result = {}
    for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/_shard_*_progress.json'))):
        name = os.path.basename(f)
        data = safe_load(f)
        if data:
            result[name] = {
                'completed': len(data.get('completed_players', [])),
                'matches': len(data.get('completed_matches', [])),
                'last_updated': data.get('last_updated', '?'),
            }
    return result

print("第一次快照...")
snap1 = get_snapshot()
total1_completed = set()
for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/_shard_*_progress.json'))):
    data = safe_load(f)
    if data:
        total1_completed.update(data.get('completed_players', []))
unique1 = len(total1_completed)

print(f"  去重 completed: {unique1}")
print(f"  等待 30 秒...")
time.sleep(30)

print("第二次快照...")
snap2 = get_snapshot()
total2_completed = set()
for f in sorted(glob.glob(os.path.join(BASE, 'output/extra_match_data/_shard_*_progress.json'))):
    data = safe_load(f)
    if data:
        total2_completed.update(data.get('completed_players', []))
unique2 = len(total2_completed)

print(f"  去重 completed: {unique2}")
print()

# 对比
print("=" * 60)
print("30秒内变化:")
print("=" * 60)
for name in sorted(snap1.keys()):
    s1 = snap1.get(name, {})
    s2 = snap2.get(name, {})
    c_diff = s2.get('completed', 0) - s1.get('completed', 0)
    m_diff = s2.get('matches', 0) - s1.get('matches', 0)
    status = "→ 活跃" if c_diff > 0 else "→ 停滞"
    print(f"  {name}: completed +{c_diff}, matches +{m_diff}  {status}")
    print(f"    last_updated: {s2.get('last_updated', '?')}")

new_unique = unique2 - unique1
print(f"\n去重 completed 变化: {unique1} → {unique2} (+{new_unique})")
print(f"每分钟预计新增: ~{new_unique * 2} 玩家 (去重)")

if new_unique == 0:
    print("\n⚠️ 30秒内无新增玩家！进程可能已完成各自分片内的任务。")
else:
    remaining = 112816 - unique2
    if new_unique > 0:
        eta_min = remaining / (new_unique * 2)
        print(f"剩余 ~{remaining} 玩家，预计还需 ~{eta_min:.0f} 分钟 (~{eta_min/60:.1f} 小时)")

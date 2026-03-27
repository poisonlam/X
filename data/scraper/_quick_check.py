"""Quick check for automation: process count + shard details"""
import subprocess, re, json, os, datetime

base_extra = 'data/scraper/output/extra_match_data'
base_pc = 'data/scraper/output/pc_match_data'

# 1. Process count via wmic
r = subprocess.run(
    'wmic process where "Name=\'python.exe\'" get ProcessId,CommandLine /format:csv',
    capture_output=True, text=True, shell=True
)
lines = r.stdout.splitlines()
pc_procs = [l for l in lines if 'parallel_collect' in l]
ex_procs = [l for l in lines if 'extract_and_collect_extra' in l]
print(f"=== Process Count ===")
print(f"PC parallel_collect processes: {len(pc_procs)}")
print(f"Extra extract_and_collect processes: {len(ex_procs)}")

# 2. Extra shard details
print(f"\n=== Extra Shard Progress ===")
total_completed = 0
total_players = 0
total_matches = 0
shards = sorted([f for f in os.listdir(base_extra) if f.startswith('_shard_') and f.endswith('_progress.json')])
for f in shards:
    path = os.path.join(base_extra, f)
    try:
        d = json.load(open(path, encoding='utf-8'))
        p = d.get('completed_count', 0)
        m = d.get('match_count', 0)
        t = d.get('total_players', 0)
        total_completed += p
        total_players += t
        total_matches += m
        age = (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 60
        print(f"  {f}: {p}/{t} done, {m} matches, remain={t-p}, age={age:.1f}min")
    except Exception as e:
        print(f"  {f}: ERROR {e}")

print(f"\n  TOTAL: {total_completed}/{total_players} players, {total_matches} matches, remain={total_players-total_completed}")

# 3. Speed estimate
# From progress data: started at 00:15, now check elapsed
started = datetime.datetime(2026, 3, 25, 0, 15)  # relay launched
now = datetime.datetime.now()
elapsed_h = (now - started).total_seconds() / 3600
# Previously completed 4361, so new = total_completed - 4361
new_completed = total_completed - 4361
if elapsed_h > 0 and new_completed > 0:
    rate = new_completed / elapsed_h
    remaining = total_players - total_completed
    eta_h = remaining / rate if rate > 0 else 999
    print(f"\n=== Speed Estimate ===")
    print(f"  Elapsed since relay: {elapsed_h:.1f}h")
    print(f"  New completions: {new_completed}")
    print(f"  Rate: {rate:.0f} players/hour ({rate/16:.0f}/shard/hour)")
    print(f"  Remaining: {remaining} players")
    print(f"  ETA: {eta_h:.1f} hours ({eta_h/24:.1f} days)")

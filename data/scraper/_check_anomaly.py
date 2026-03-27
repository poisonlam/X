import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))

pc_file = os.path.join(BASE, 'output', 'match_data', '_anomaly_players.json')
ex_file = os.path.join(BASE, 'output', 'extra_match_data', '_anomaly_players.json')

print("=== PC Anomaly Players ===")
if os.path.exists(pc_file):
    with open(pc_file, 'r', encoding='utf-8') as f:
        pc = json.load(f)
    print(f"  Total: {len(pc)} players")
    for p in pc[:5]:
        print(f"  - {p['player_name']} | {p['reason']} | {p.get('recorded_at','?')}")
    if len(pc) > 5:
        print(f"  ... and {len(pc)-5} more")
else:
    print("  (no file yet)")

print("\n=== Extra Anomaly Players ===")
if os.path.exists(ex_file):
    with open(ex_file, 'r', encoding='utf-8') as f:
        ex = json.load(f)
    print(f"  Total: {len(ex)} players")
    for p in ex[:5]:
        print(f"  - {p['player_name']} | {p['reason']} | {p.get('recorded_at','?')}")
    if len(ex) > 5:
        print(f"  ... and {len(ex)-5} more")
else:
    print("  (no file yet)")

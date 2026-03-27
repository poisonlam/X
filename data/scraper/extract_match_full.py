"""
完整提取 stats.cc 比赛详情页面的所有结构化数据
目标: 提取 地图 × 干员 × 回合 × 玩家 的完整数据
"""
import requests
import re
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}

def deref(data, idx, depth=0, max_depth=25, cache=None):
    if cache is None:
        cache = {}
    if idx in cache:
        return cache[idx]
    if depth > max_depth or idx >= len(data):
        return None
    item = data[idx]
    if isinstance(item, (str, float, bool)) or item is None:
        return item
    if isinstance(item, int):
        return item
    if isinstance(item, list):
        if len(item) == 2 and isinstance(item[0], str) and item[0] in ('ShallowReactive', 'Reactive', 'ShallowRef', 'Ref', 'Set'):
            result = deref(data, item[1], depth+1, max_depth, cache)
            cache[idx] = result
            return result
        result = [deref(data, i, depth+1, max_depth, cache) if isinstance(i, int) else i for i in item]
        cache[idx] = result
        return result
    if isinstance(item, dict):
        result = {}
        for k, v in item.items():
            result[k] = deref(data, v, depth+1, max_depth, cache) if isinstance(v, int) else v
        cache[idx] = result
        return result
    return item

# 获取比赛详情
match_id = '5441e056-6d6c-4480-bbb5-6eec3b439cf3'
r = requests.get(f'https://stats.cc/siege/matches/{match_id}', headers=HEADERS, timeout=30)
print(f"HTTP {r.status_code}, {len(r.text)} bytes")

json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
nuxt = json.loads(json_blocks[0])

# 1. 提取所有回合级数据（每个玩家每回合的干员 + 表现）
print("\n" + "=" * 70)
print("EXTRACTING ROUND-BY-ROUND OPERATOR DATA")
print("=" * 70)

round_data = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'operator' in item and 'outcome' in item and 'profile_id' in item:
        resolved = deref(nuxt, i, max_depth=12)
        round_data.append(resolved)

print(f"Total round records: {len(round_data)}")

# 2. 提取比赛元数据
match_meta = None
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'map' in item and 'scores' in item and 'playlist' in item:
        match_meta = deref(nuxt, i, max_depth=15)
        break

if match_meta:
    print(f"\nMatch: {match_meta.get('map', 'N/A')} ({match_meta.get('playlist', 'N/A')})")
    print(f"Scores: {match_meta.get('scores', 'N/A')}")
    print(f"Started: {match_meta.get('started_at', 'N/A')}")

# 3. 提取比赛中的回合数据（每个round有哪些记录）
print("\n" + "=" * 70)
print("ROUND-BY-ROUND DETAILS")
print("=" * 70)

# 找到 rounds 列表
rounds_list = None
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'round_number' in item and 'end_reason' in item:
        # 这是一个 round
        if rounds_list is None:
            rounds_list = []
        resolved = deref(nuxt, i, max_depth=15)
        rounds_list.append(resolved)

if rounds_list:
    print(f"Found {len(rounds_list)} rounds")
    for rd in rounds_list[:3]:
        print(f"\n  Round {rd.get('round_number', '?')}: end_reason={rd.get('end_reason', '?')}")
        print(f"    {json.dumps(rd, ensure_ascii=False, default=str)[:500]}")
else:
    # 换个方式找 round 数据
    print("  No 'round_number' dicts found. Looking for round lists...")
    for i in range(len(nuxt)):
        item = nuxt[i]
        if isinstance(item, list) and len(item) >= 5 and len(item) <= 15:
            # 可能是 rounds 列表
            first_ref = item[0] if isinstance(item[0], int) else None
            if first_ref and first_ref < len(nuxt) and isinstance(nuxt[first_ref], dict):
                if 'operator' in nuxt[first_ref] and 'profile_id' in nuxt[first_ref]:
                    resolved_first = deref(nuxt, first_ref, max_depth=10)
                    print(f"\n  [{i}] Round player data list (len={len(item)}):")
                    print(f"    First: {json.dumps(resolved_first, ensure_ascii=False, default=str)[:300]}")

# 4. 组织数据：按回合分组
print("\n" + "=" * 70)
print("ORGANIZED DATA: ROUND → PLAYERS → OPERATORS")
print("=" * 70)

# 找到 round 结构
round_groups = {}
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict):
        keys = set(item.keys())
        # 寻找包含 round + players/player_rounds 的 dict
        if 'round' in keys and ('player_rounds' in keys or 'players' in keys):
            resolved = deref(nuxt, i, max_depth=20)
            rd_num = resolved.get('round', '?')
            print(f"\n  Round {rd_num}:")
            print(f"    Keys: {list(resolved.keys())}")
            
            # player_rounds
            pr = resolved.get('player_rounds', resolved.get('players', []))
            if isinstance(pr, list):
                print(f"    Players: {len(pr)}")
                for p in pr[:10]:
                    if isinstance(p, dict):
                        print(f"      {p.get('username', p.get('profile_id', '?'))[:20]}: "
                              f"Op={p.get('operator', '?')}, "
                              f"K={p.get('kills', '?')}/D={p.get('deaths', '?')}, "
                              f"Outcome={p.get('outcome', '?')}")

# 5. 提取玩家汇总数据
print("\n" + "=" * 70)
print("PLAYER SUMMARIES")  
print("=" * 70)

player_summaries = []
for i in range(len(nuxt)):
    item = nuxt[i]
    if isinstance(item, dict) and 'username' in item and 'rounds' in item and 'round_wins' in item and 'team' in item:
        resolved = deref(nuxt, i, max_depth=12)
        player_summaries.append(resolved)

print(f"Found {len(player_summaries)} player summaries")
for ps in player_summaries:
    print(f"  {ps.get('username', '?'):20s} Team={ps.get('team', '?')} "
          f"Outcome={ps.get('outcome', '?'):4s} "
          f"K/D={ps.get('kills', 0)}/{ps.get('deaths', 0)} "
          f"Rounds={ps.get('round_wins', 0)}W/{ps.get('round_losses', 0)}L")

# 6. 组装完整的比赛数据结构
print("\n" + "=" * 70)
print("ASSEMBLING COMPLETE MATCH DATA")
print("=" * 70)

complete_match = {
    "match_id": match_id,
    "map": match_meta.get('map') if match_meta else None,
    "playlist": match_meta.get('playlist') if match_meta else None,
    "mode": match_meta.get('mode') if match_meta else None,
    "scores": match_meta.get('scores') if match_meta else None,
    "started_at": match_meta.get('started_at') if match_meta else None,
    "ended_at": match_meta.get('ended_at') if match_meta else None,
    "player_summaries": player_summaries,
    "round_by_round_operators": round_data,
}

# 按 profile_id 分组 round_data
players_rounds = {}
for rd in round_data:
    pid = rd.get('profile_id', 'unknown')
    if pid not in players_rounds:
        players_rounds[pid] = []
    players_rounds[pid].append(rd)

print(f"\nPlayers with round data: {len(players_rounds)}")
for pid, rounds in players_rounds.items():
    # 找这个玩家的 username
    username = pid[:12]
    for ps in player_summaries:
        if ps.get('profile_id') == pid:
            username = ps.get('username', pid[:12])
            break
    
    ops = [r.get('operator', '?') for r in rounds]
    outcomes = [r.get('outcome', '?') for r in rounds]
    print(f"\n  {username}:")
    for j, (op, out) in enumerate(zip(ops, outcomes)):
        kills = rounds[j].get('kills', 0)
        deaths = rounds[j].get('deaths', 0)
        print(f"    Rd {j+1}: {op:15s} {out:4s} K:{kills} D:{deaths}")

# 保存完整数据
output_file = 'data/scraper/output/statscc_match_full.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(complete_match, f, ensure_ascii=False, indent=2, default=str)
print(f"\nSaved complete match data to {output_file}")
print(f"  File size: {len(json.dumps(complete_match, default=str))} bytes")
print(f"  Total round records: {len(round_data)}")
print(f"  Players: {len(player_summaries)}")
print(f"  Rounds per player: ~{len(round_data) // max(len(player_summaries), 1)}")

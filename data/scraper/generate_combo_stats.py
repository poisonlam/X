"""
生成地图×干员阵容搭配分析数据
输出追加到 player_match_stats.js 的 topCombos 和新增 mapTeamComps 字段

流式处理，按地图统计:
1. 每张地图的热门双人搭配 (攻/防方分开, Top 15)
2. 每张地图的热门五人阵容 (攻/防方分开, Top 10)
"""
import json
import os
import sys
import io
import glob
import gc
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JS = os.path.join(BASE_DIR, '..', 'player_match_stats.js')

ATTACKERS = {
    'sledge','thatcher','ash','thermite','twitch','montagne','blitz','iq','fuze','glaz',
    'buck','blackbeard','capitao','hibana','jackal','ying','zofia','dokkaebi','lion','finka',
    'maverick','nomad','gridlock','nokk','amaru','kali','iana','ace','zero','flores',
    'osa','sens','grim','brava','ram','striker','deimos','solid-snake'
}
DEFENDERS = {
    'smoke','mute','castle','pulse','doc','rook','jager','bandit','tachanka','kapkan',
    'frost','valkyrie','caveira','echo','mira','lesion','ela','vigil','alibi','maestro',
    'clash','kaid','mozzie','warden','goyo','wamai','oryx','melusi','aruni','thunderbird',
    'thorn','azami','solis','fenrir','tubarao','skopos','neon'
}

def get_side(op):
    op = op.lower().strip()
    if op in ATTACKERS: return 'attack'
    if op in DEFENDERS: return 'defense'
    return 'unknown'

# 按地图统计
# map -> side(attack/defense) -> combo_key -> {total, wins}
map_duo_combos = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'total': 0, 'wins': 0})))
map_full_combos = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'total': 0, 'wins': 0})))
# 全局双人搭配
global_duo = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'wins': 0}))

seen_match_ids = set()
match_count = 0
round_count = 0

def process_match(m):
    global match_count, round_count
    mid = m.get('match_id')
    if not mid or mid in seen_match_ids:
        return
    seen_match_ids.add(mid)
    match_count += 1

    map_name = m.get('map', 'unknown')
    total_players = m.get('total_players', 10)
    total_rounds = m.get('total_rounds', 0)

    # 构建 profile_id -> team 映射
    pid_team = {}
    for ps in m.get('player_summaries', []):
        pid = ps.get('profile_id')
        team = ps.get('team', -1)
        if pid is not None and team >= 0:
            pid_team[pid] = team

    round_records = m.get('round_records', [])
    chunk_size = total_players if total_players else 10

    # 按回合分组 (每 chunk_size 条 = 一个回合的所有玩家记录)
    for i in range(0, len(round_records), chunk_size):
        chunk = round_records[i:i+chunk_size]
        if len(chunk) < chunk_size:
            continue
        round_count += 1

        # 按队伍分组
        teams = defaultdict(list)  # team_id -> [(operator, is_win)]
        for rd in chunk:
            pid = rd.get('profile_id', '')
            op = rd.get('operator', '')
            outcome = rd.get('outcome', '')
            team = pid_team.get(pid, -1)
            if op and team >= 0:
                teams[team].append((op.lower().strip(), outcome == 'win'))

        for team_id, ops_list in teams.items():
            if len(ops_list) != 5:
                continue

            ops = [o[0] for o in ops_list]
            is_win = ops_list[0][1]  # 同队胜负一致

            # 判断攻/防方
            sides = [get_side(o) for o in ops]
            atk_count = sides.count('attack')
            def_count = sides.count('defense')
            if atk_count >= 4:
                side = 'attack'
            elif def_count >= 4:
                side = 'defense'
            else:
                continue  # 混合阵营，跳过

            sorted_ops = tuple(sorted(ops))

            # 五人阵容
            full_key = '+'.join(sorted_ops)
            fc = map_full_combos[map_name][side][full_key]
            fc['total'] += 1
            if is_win: fc['wins'] += 1

            # 双人搭配
            for j in range(len(sorted_ops)):
                for k in range(j+1, len(sorted_ops)):
                    duo_key = f"{sorted_ops[j]}+{sorted_ops[k]}"
                    dc = map_duo_combos[map_name][side][duo_key]
                    dc['total'] += 1
                    if is_win: dc['wins'] += 1
                    gd = global_duo[side][duo_key]
                    gd['total'] += 1
                    if is_win: gd['wins'] += 1


def scan_json(fpath):
    shard = os.path.basename(os.path.dirname(fpath))
    parent = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
    print(f"  {parent}/{shard} ...", end=' ', flush=True)
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    matches = data if isinstance(data, list) else [data]
    for m in matches:
        process_match(m)
    print(f"{len(matches)} matches")

def scan_jsonl(fpath):
    shard = os.path.basename(os.path.dirname(fpath))
    parent = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
    print(f"  {parent}/{shard} ...", end=' ', flush=True)
    count = 0
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            count += 1
            try:
                process_match(json.loads(line))
            except: pass
    print(f"{count} lines")


def main():
    print("=" * 70)
    print("干员阵容搭配分析 (流式处理)")
    print("=" * 70)

    # 扫描 PC 分片
    pattern = os.path.join(BASE_DIR, 'output', 'match_data', 'shard_*', 'match_details.json')
    files = sorted(glob.glob(pattern))
    print(f"\n[PC] {len(files)} 个分片")
    for f in files:
        scan_json(f); gc.collect()

    # 扫描 Extra V2
    pattern = os.path.join(BASE_DIR, 'output', 'extra_match_data', 'v2_shard_*', 'match_details.jsonl')
    files = sorted(glob.glob(pattern))
    print(f"\n[Extra V2] {len(files)} 个分片")
    for f in files:
        scan_jsonl(f); gc.collect()

    # 旧 Extra
    pattern = os.path.join(BASE_DIR, 'output', 'extra_match_data', 'shard_*', 'match_details.json')
    files = sorted(glob.glob(pattern))
    if files:
        print(f"\n[旧 Extra] {len(files)} 个分片")
        for f in files:
            scan_json(f); gc.collect()

    print(f"\n扫描完成: {match_count} 比赛, {round_count} 回合")

    # 生成结果
    print("\n生成阵容搭配数据...")

    map_team_comps = {}
    for map_name in sorted(map_duo_combos.keys()):
        map_team_comps[map_name] = {}
        for side in ['attack', 'defense']:
            # 双人搭配 Top 15
            duos = map_duo_combos[map_name][side]
            top_duos = sorted(duos.items(), key=lambda x: -x[1]['total'])[:15]
            duo_list = []
            for key, stats in top_duos:
                ops = key.split('+')
                wr = round(stats['wins'] / max(stats['total'], 1) * 100, 1)
                duo_list.append({
                    'operators': ops,
                    'pickCount': stats['total'],
                    'winRate': wr
                })

            # 五人阵容 Top 10
            fulls = map_full_combos[map_name][side]
            top_fulls = sorted(fulls.items(), key=lambda x: -x[1]['total'])[:10]
            full_list = []
            for key, stats in top_fulls:
                ops = key.split('+')
                wr = round(stats['wins'] / max(stats['total'], 1) * 100, 1)
                full_list.append({
                    'operators': ops,
                    'pickCount': stats['total'],
                    'winRate': wr
                })

            map_team_comps[map_name][side] = {
                'duoCombos': duo_list,
                'fullLineups': full_list
            }

    # 全局热门双人搭配 Top 30
    global_top_combos = []
    for side in ['attack', 'defense']:
        top = sorted(global_duo[side].items(), key=lambda x: -x[1]['total'])[:15]
        for key, stats in top:
            ops = key.split('+')
            wr = round(stats['wins'] / max(stats['total'], 1) * 100, 1)
            global_top_combos.append({
                'operators': ops,
                'side': side,
                'pickCount': stats['total'],
                'winRate': wr
            })

    # 读取现有 player_match_stats.js，注入新数据
    print("更新 player_match_stats.js ...")
    with open(OUTPUT_JS, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到 const PLAYER_MATCH_STATS = {...}; 中的 JSON 部分
    start = content.index('{', content.index('const PLAYER_MATCH_STATS'))
    end = content.rindex('};')
    json_str = content[start:end+1]
    data = json.loads(json_str)

    # 注入新数据
    data['topCombos'] = global_top_combos
    data['mapTeamComps'] = map_team_comps

    # 重写文件
    header = content[:content.index('const PLAYER_MATCH_STATS')]
    js = header + f"const PLAYER_MATCH_STATS = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write(js)

    size_kb = os.path.getsize(OUTPUT_JS) / 1024
    print(f"  ✅ {OUTPUT_JS} ({size_kb:.1f} KB)")
    print(f"  地图数: {len(map_team_comps)}")
    print(f"  全局热门搭配: {len(global_top_combos)}")

    # 打印示例
    for map_name in list(map_team_comps.keys())[:2]:
        print(f"\n  📍 {map_name}:")
        for side in ['attack', 'defense']:
            comps = map_team_comps[map_name].get(side, {})
            duos = comps.get('duoCombos', [])[:3]
            fulls = comps.get('fullLineups', [])[:2]
            side_label = '进攻' if side == 'attack' else '防守'
            print(f"    {side_label}方 热门双人搭配:")
            for d in duos:
                print(f"      {'+'.join(d['operators'])} ({d['pickCount']}次, 胜率{d['winRate']}%)")
            print(f"    {side_label}方 热门阵容:")
            for fl in fulls:
                print(f"      {'+'.join(fl['operators'])} ({fl['pickCount']}次, 胜率{fl['winRate']}%)")

    print("\n" + "=" * 70)
    print("✅ 完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()

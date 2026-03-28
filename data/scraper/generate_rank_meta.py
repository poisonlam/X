"""
段位 × 干员 × 地图 交叉分析
流式处理所有比赛数据，按玩家段位分组统计干员使用情况

生成:
1. 各段位干员 Meta 差异（每个段位 tier 的 Top 干员选取率+胜率）
2. 段位 × 地图 × 干员选取率（每个地图每个段位的热门干员）
"""
import json, os, sys, io, glob, gc
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RANK_FILE = BASE_DIR / 'output' / 'rank_data' / '_final_ranks.json'
OUTPUT_JS = BASE_DIR / '..' / 'player_match_stats.js'

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

# 段位大类映射
TIER_ORDER = ['Champion','Diamond','Emerald','Platinum','Gold','Silver','Bronze','Copper']

def rank_to_tier(rank):
    if not rank or rank in ('unknown','error','timeout','unranked'):
        return None
    for t in TIER_ORDER:
        if rank.startswith(t.lower()):
            return t
    return None

# 加载段位数据: pid -> tier
print("加载段位数据...")
rank_raw = json.load(open(RANK_FILE, 'r', encoding='utf-8'))
player_tier = {}
for pid, val in rank_raw.items():
    if isinstance(val, dict):
        r = val.get('rank', '')
    else:
        r = val
    t = rank_to_tier(r)
    if t:
        player_tier[pid] = t
print(f"  {len(player_tier)} 玩家有段位大类")
tier_counts = Counter(player_tier.values())
for t in TIER_ORDER:
    print(f"  {t}: {tier_counts.get(t,0):,}")

# 也加载排行榜玩家段位 (他们的段位来自排行榜)
lb_file = BASE_DIR / 'output' / 'leaderboard' / 'leaderboard_full.json'
if lb_file.exists():
    lb = json.load(open(lb_file, 'r', encoding='utf-8'))
    for p in lb:
        pid = p.get('profileId','')
        rp = p.get('rankPoints', 0)
        if pid and rp:
            if rp >= 5000: player_tier[pid] = 'Champion'
            elif rp >= 4000: player_tier[pid] = 'Diamond'
            elif rp >= 3500: player_tier[pid] = 'Emerald'
            elif rp >= 3000: player_tier[pid] = 'Platinum'
            elif rp >= 2500: player_tier[pid] = 'Gold'
            elif rp >= 2000: player_tier[pid] = 'Silver'
            elif rp >= 1500: player_tier[pid] = 'Bronze'
            else: player_tier[pid] = 'Copper'
    print(f"  After leaderboard merge: {len(player_tier)} 玩家")

# 统计容器
# tier -> op -> {picks, wins, kills, deaths}
tier_op_stats = defaultdict(lambda: defaultdict(lambda: {'picks':0,'wins':0,'kills':0,'deaths':0}))
# tier -> map -> op -> {picks, wins, kills, deaths}
tier_map_op_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'picks':0,'wins':0,'kills':0,'deaths':0})))
# tier -> map -> {atk_wins, atk_total, def_wins, def_total}
tier_map_side = defaultdict(lambda: defaultdict(lambda: {'atk_wins':0,'atk_total':0,'def_wins':0,'def_total':0}))

seen = set()
match_count = 0

def process_match(m):
    global match_count
    mid = m.get('match_id')
    if not mid or mid in seen: return
    seen.add(mid)
    match_count += 1

    map_name = m.get('map', 'unknown')
    total_players = m.get('total_players', 10)

    # pid -> team
    pid_team = {}
    for ps in m.get('player_summaries', []):
        pid = ps.get('profile_id')
        if pid:
            pid_team[pid] = ps.get('team', -1)

    for rd in m.get('round_records', []):
        pid = rd.get('profile_id', '')
        op = rd.get('operator', '')
        if not op or not pid: continue

        tier = player_tier.get(pid)
        if not tier: continue

        outcome = rd.get('outcome', '')
        is_win = outcome == 'win'
        kills = rd.get('kills', 0)
        deaths = rd.get('deaths', 0)
        side = get_side(op)

        # tier × op
        s = tier_op_stats[tier][op]
        s['picks'] += 1
        if is_win: s['wins'] += 1
        s['kills'] += kills
        s['deaths'] += deaths

        # tier × map × op
        s2 = tier_map_op_stats[tier][map_name][op]
        s2['picks'] += 1
        if is_win: s2['wins'] += 1
        s2['kills'] += kills
        s2['deaths'] += deaths

        # tier × map × side win rate
        ms = tier_map_side[tier][map_name]
        if side == 'attack':
            ms['atk_total'] += 1
            if is_win: ms['atk_wins'] += 1
        elif side == 'defense':
            ms['def_total'] += 1
            if is_win: ms['def_wins'] += 1


def scan_json(fpath):
    label = f"{Path(fpath).parent.parent.name}/{Path(fpath).parent.name}"
    print(f"  {label} ...", end=' ', flush=True)
    data = json.load(open(fpath, 'r', encoding='utf-8'))
    matches = data if isinstance(data, list) else [data]
    for m in matches: process_match(m)
    print(f"{len(matches)} matches")

def scan_jsonl(fpath):
    label = f"{Path(fpath).parent.parent.name}/{Path(fpath).parent.name}"
    print(f"  {label} ...", end=' ', flush=True)
    c = 0
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            c += 1
            try: process_match(json.loads(line))
            except: pass
    print(f"{c} lines")

# 扫描
print("\n扫描比赛数据...")
for f in sorted(glob.glob(str(BASE_DIR / 'output' / 'match_data' / 'shard_*' / 'match_details.json'))):
    scan_json(f); gc.collect()
for f in sorted(glob.glob(str(BASE_DIR / 'output' / 'extra_match_data' / 'v2_shard_*' / 'match_details.jsonl'))):
    scan_jsonl(f); gc.collect()
for f in sorted(glob.glob(str(BASE_DIR / 'output' / 'extra_match_data' / 'shard_*' / 'match_details.json'))):
    scan_json(f); gc.collect()

print(f"\n扫描完成: {match_count} 比赛")

# === 生成分析结果 ===

# 1. 各段位干员Meta差异
print("\n生成段位干员Meta...")
rank_meta = {}
for tier in TIER_ORDER:
    ops = tier_op_stats.get(tier, {})
    total_picks = sum(s['picks'] for s in ops.values())
    atk_list = []
    def_list = []
    for op, s in ops.items():
        side = get_side(op)
        entry = {
            'name': op,
            'picks': s['picks'],
            'pickRate': round(s['picks'] / max(total_picks, 1) * 100, 2),
            'winRate': round(s['wins'] / max(s['picks'], 1) * 100, 1),
            'kd': round(s['kills'] / max(s['deaths'], 1), 2),
        }
        if side == 'attack': atk_list.append(entry)
        elif side == 'defense': def_list.append(entry)
    atk_list.sort(key=lambda x: -x['picks'])
    def_list.sort(key=lambda x: -x['picks'])
    rank_meta[tier] = {
        'totalRounds': total_picks,
        'attackers': atk_list[:20],
        'defenders': def_list[:20],
    }

# 2. 段位×地图×干员
print("生成段位×地图×干员...")
rank_map_meta = {}
for tier in TIER_ORDER:
    rank_map_meta[tier] = {}
    maps = tier_map_op_stats.get(tier, {})
    for map_name, ops in maps.items():
        total_picks = sum(s['picks'] for s in ops.values())
        atk = []
        defe = []
        for op, s in ops.items():
            side = get_side(op)
            entry = {
                'name': op,
                'picks': s['picks'],
                'pickRate': round(s['picks'] / max(total_picks, 1) * 100, 2),
                'winRate': round(s['wins'] / max(s['picks'], 1) * 100, 1),
                'kd': round(s['kills'] / max(s['deaths'], 1), 2),
            }
            if side == 'attack': atk.append(entry)
            elif side == 'defense': defe.append(entry)
        atk.sort(key=lambda x: -x['picks'])
        defe.sort(key=lambda x: -x['picks'])
        
        # 攻防胜率
        ms = tier_map_side.get(tier, {}).get(map_name, {})
        atk_wr = round(ms.get('atk_wins',0) / max(ms.get('atk_total',1), 1) * 100, 1)
        def_wr = round(ms.get('def_wins',0) / max(ms.get('def_total',1), 1) * 100, 1)
        
        rank_map_meta[tier][map_name] = {
            'totalRounds': total_picks,
            'atkWinRate': atk_wr,
            'defWinRate': def_wr,
            'attackers': atk[:15],
            'defenders': defe[:15],
        }

# 注入到 player_match_stats.js
print("\n更新 player_match_stats.js ...")
with open(OUTPUT_JS, 'r', encoding='utf-8') as f:
    content = f.read()

start = content.index('{', content.index('const PLAYER_MATCH_STATS'))
end = content.rindex('};')
data = json.loads(content[start:end+1])

data['rankMeta'] = rank_meta
data['rankMapMeta'] = rank_map_meta

header = content[:content.index('const PLAYER_MATCH_STATS')]
js = header + f"const PLAYER_MATCH_STATS = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
    f.write(js)

size_kb = os.path.getsize(OUTPUT_JS) / 1024
print(f"  ✅ {OUTPUT_JS} ({size_kb:.1f} KB)")

# 打印摘要
for tier in TIER_ORDER:
    meta = rank_meta.get(tier, {})
    print(f"\n  📊 {tier} ({meta.get('totalRounds',0):,} rounds)")
    atk = meta.get('attackers', [])[:3]
    defe = meta.get('defenders', [])[:3]
    print(f"    ATK Top3: {', '.join(f'{a['name']}({a['pickRate']}%)' for a in atk)}")
    print(f"    DEF Top3: {', '.join(f'{d['name']}({d['pickRate']}%)' for d in defe)}")

print(f"\n✅ 完成!")

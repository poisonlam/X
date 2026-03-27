"""
从采集的对局数据生成前端展示所需的 JS 数据文件
输出: data/player_match_stats.js

改进：直接从各分片文件读取数据（无需先 merge），
自动包含 PC 排行榜分片 + 额外玩家分片的全部数据。
"""
import json
import os
import sys
import io
import glob
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_FILE = os.path.join(BASE_DIR, 'output', 'leaderboard', 'leaderboard_full.json')
OUTPUT_JS = os.path.join(BASE_DIR, '..', 'player_match_stats.js')

# 干员阵营映射（攻击/防守）
ATTACKERS = {
    'sledge', 'thatcher', 'ash', 'thermite', 'twitch', 'montagne', 'blitz', 'iq', 'fuze', 'glaz',
    'buck', 'blackbeard', 'capitao', 'hibana', 'jackal', 'ying', 'zofia', 'dokkaebi', 'lion', 'finka',
    'maverick', 'nomad', 'gridlock', 'nokk', 'amaru', 'kali', 'iana', 'ace', 'zero', 'flores',
    'osa', 'sens', 'grim', 'brava', 'ram', 'striker', 'deimos', 'solid-snake'
}
DEFENDERS = {
    'smoke', 'mute', 'castle', 'pulse', 'doc', 'rook', 'jager', 'bandit', 'tachanka', 'kapkan',
    'frost', 'valkyrie', 'caveira', 'echo', 'mira', 'lesion', 'ela', 'vigil', 'alibi', 'maestro',
    'clash', 'kaid', 'mozzie', 'warden', 'goyo', 'wamai', 'oryx', 'melusi', 'aruni', 'thunderbird',
    'thorn', 'azami', 'solis', 'fenrir', 'tubarao', 'skopos', 'neon'
}

# 段位积分区间映射
RANK_TIERS = [
    (5000, 'Champion'),
    (4700, 'Diamond I'),
    (4400, 'Diamond II'),
    (4100, 'Emerald I'),
    (3800, 'Emerald II'),
    (3500, 'Platinum I'),
    (3200, 'Platinum II'),
    (2900, 'Gold I'),
    (2600, 'Gold II'),
    (2300, 'Silver I'),
    (2000, 'Silver II'),
    (1700, 'Bronze I'),
    (1400, 'Bronze II'),
    (1100, 'Copper I'),
    (0, 'Copper II'),
]

def get_rank_tier(rp):
    for threshold, tier in RANK_TIERS:
        if rp >= threshold:
            return tier
    return 'Copper II'

def get_side(operator):
    op = operator.lower().strip()
    if op in ATTACKERS:
        return 'attack'
    elif op in DEFENDERS:
        return 'defense'
    return 'unknown'

def load_all_matches():
    """从所有分片文件中加载比赛数据（去重）"""
    all_matches = []
    seen_match_ids = set()
    
    # 搜索模式：PC 分片 + 额外玩家分片
    patterns = [
        os.path.join(BASE_DIR, 'output', 'match_data', 'shard_*', 'match_details.json'),
        os.path.join(BASE_DIR, 'output', 'extra_match_data', 'shard_*', 'match_details.json'),
    ]
    
    for pattern in patterns:
        for fpath in sorted(glob.glob(pattern)):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                matches = data if isinstance(data, list) else [data]
                new_count = 0
                for m in matches:
                    mid = m.get('match_id')
                    if mid and mid not in seen_match_ids:
                        all_matches.append(m)
                        seen_match_ids.add(mid)
                        new_count += 1
                shard_name = os.path.basename(os.path.dirname(fpath))
                parent_name = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
                print(f"  Loaded {parent_name}/{shard_name}: {len(matches)} matches ({new_count} new)")
            except Exception as e:
                print(f"  [WARN] Error loading {fpath}: {e}")
    
    # 也尝试加载旧的合并文件（兼容）
    old_merged = os.path.join(BASE_DIR, 'output', 'match_data', 'all_match_details.json')
    if os.path.exists(old_merged):
        try:
            with open(old_merged, 'r', encoding='utf-8') as f:
                data = json.load(f)
            new_count = 0
            for m in data:
                mid = m.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_matches.append(m)
                    seen_match_ids.add(mid)
                    new_count += 1
            if new_count > 0:
                print(f"  Loaded legacy all_match_details.json: {new_count} additional matches")
        except Exception:
            pass
    
    return all_matches


def main():
    print("=" * 70)
    print("生成前端数据文件: player_match_stats.js")
    print("=" * 70)
    
    # 加载数据 - 直接从各分片文件读取
    print("\n加载比赛数据（从各分片文件）...")
    all_matches = load_all_matches()
    
    with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
        leaderboard = json.load(f)
    
    print(f"\n比赛数据总计: {len(all_matches)} 场（去重）")
    print(f"排行榜: {len(leaderboard)} 玩家")
    
    # ===== 1. 数据总览 =====
    total_rounds = sum(len(m.get('round_records', [])) for m in all_matches)
    all_player_ids = set()
    for m in all_matches:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id')
            if pid:
                all_player_ids.add(pid)
    
    all_operators = set()
    all_maps = set()
    for m in all_matches:
        map_name = m.get('map')
        if map_name:
            all_maps.add(map_name)
        for rd in m.get('round_records', []):
            op = rd.get('operator')
            if op:
                all_operators.add(op)
    
    overview = {
        'totalLeaderboardPlayers': len(leaderboard),
        'totalPlayersProcessed': len(set(m.get('source_player', {}).get('profileId', '') for m in all_matches)),
        'totalMatchesCollected': len(all_matches),
        'totalRoundRecords': total_rounds,
        'totalUniquePlayers': len(all_player_ids),
        'totalUniqueOperators': len(all_operators),
        'totalUniqueMaps': len(all_maps),
        'generatedAt': datetime.now().isoformat(),
        'dataSource': 'stats.cc (排行榜 + 比赛详情)',
        'season': 'Silent Hunt (Y10S4)',
    }
    
    # ===== 2. 排行榜段位分布 =====
    rank_distribution = defaultdict(int)
    rp_distribution = defaultdict(int)
    for p in leaderboard:
        rank = p.get('rank', 'unknown')
        rp = p.get('rankPoints', 0)
        rank_distribution[rank] += 1
        tier = get_rank_tier(rp)
        rp_distribution[tier] += 1
    
    # 使用详细的积分区间分布
    rp_ranges = defaultdict(int)
    for p in leaderboard:
        rp = p.get('rankPoints', 0)
        if rp >= 5000:
            rp_ranges['5000+'] += 1
        elif rp >= 4800:
            rp_ranges['4800-4999'] += 1
        elif rp >= 4600:
            rp_ranges['4600-4799'] += 1
        elif rp >= 4400:
            rp_ranges['4400-4599'] += 1
        elif rp >= 4200:
            rp_ranges['4200-4399'] += 1
        elif rp >= 4000:
            rp_ranges['4000-4199'] += 1
        elif rp >= 3800:
            rp_ranges['3800-3999'] += 1
        elif rp >= 3600:
            rp_ranges['3600-3799'] += 1
        elif rp >= 3400:
            rp_ranges['3400-3599'] += 1
        elif rp >= 3200:
            rp_ranges['3200-3399'] += 1
        else:
            rp_ranges['<3200'] += 1
    
    # ===== 3. 地图分布 =====
    map_stats = defaultdict(lambda: {'total': 0, 'rounds': 0})
    for m in all_matches:
        map_name = m.get('map', 'unknown')
        map_stats[map_name]['total'] += 1
        map_stats[map_name]['rounds'] += len(m.get('round_records', []))
    
    # ===== 4. 干员使用统计 =====
    operator_stats = defaultdict(lambda: {
        'total': 0, 'wins': 0, 'kills': 0, 'deaths': 0,
        'opening_kills': 0, 'headshots': 0, 'clutch': 0
    })
    
    for m in all_matches:
        for rd in m.get('round_records', []):
            op = rd.get('operator', '')
            if not op:
                continue
            stats = operator_stats[op]
            stats['total'] += 1
            if rd.get('outcome') == 'win':
                stats['wins'] += 1
            stats['kills'] += rd.get('kills', 0)
            stats['deaths'] += rd.get('deaths', 0)
            stats['opening_kills'] += rd.get('opening_kills', 0)
            stats['headshots'] += rd.get('headshots', 0)
            stats['clutch'] += rd.get('clutch', 0)
    
    # 计算衍生指标
    operator_data = []
    for op, stats in operator_stats.items():
        side = get_side(op)
        win_rate = round(stats['wins'] / max(stats['total'], 1) * 100, 2)
        kd = round(stats['kills'] / max(stats['deaths'], 1), 2)
        operator_data.append({
            'name': op,
            'side': side,
            'pickCount': stats['total'],
            'winRate': win_rate,
            'wins': stats['wins'],
            'kills': stats['kills'],
            'deaths': stats['deaths'],
            'kd': kd,
            'openingKills': stats['opening_kills'],
            'headshots': stats['headshots'],
            'clutch': stats['clutch'],
        })
    
    operator_data.sort(key=lambda x: -x['pickCount'])
    
    # ===== 5. 地图 × 干员交叉数据 =====
    map_operator = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'wins': 0, 'kills': 0, 'deaths': 0}))
    
    for m in all_matches:
        map_name = m.get('map', 'unknown')
        for rd in m.get('round_records', []):
            op = rd.get('operator', '')
            if not op:
                continue
            mo = map_operator[map_name][op]
            mo['total'] += 1
            if rd.get('outcome') == 'win':
                mo['wins'] += 1
            mo['kills'] += rd.get('kills', 0)
            mo['deaths'] += rd.get('deaths', 0)
    
    # 转换为可序列化格式
    map_operator_data = {}
    for map_name, ops in map_operator.items():
        map_operator_data[map_name] = []
        for op, stats in ops.items():
            wr = round(stats['wins'] / max(stats['total'], 1) * 100, 2)
            kd = round(stats['kills'] / max(stats['deaths'], 1), 2)
            map_operator_data[map_name].append({
                'name': op,
                'side': get_side(op),
                'pickCount': stats['total'],
                'winRate': wr,
                'kd': kd,
                'kills': stats['kills'],
                'deaths': stats['deaths'],
            })
        map_operator_data[map_name].sort(key=lambda x: -x['pickCount'])
    
    # ===== 6. 攻防胜率对比 =====
    attack_wins = 0
    attack_total = 0
    defense_wins = 0
    defense_total = 0
    
    for m in all_matches:
        for rd in m.get('round_records', []):
            op = rd.get('operator', '')
            side = get_side(op)
            outcome = rd.get('outcome', '')
            if side == 'attack':
                attack_total += 1
                if outcome == 'win':
                    attack_wins += 1
            elif side == 'defense':
                defense_total += 1
                if outcome == 'win':
                    defense_wins += 1
    
    side_stats = {
        'attack': {
            'total': attack_total,
            'wins': attack_wins,
            'winRate': round(attack_wins / max(attack_total, 1) * 100, 2)
        },
        'defense': {
            'total': defense_total,
            'wins': defense_wins,
            'winRate': round(defense_wins / max(defense_total, 1) * 100, 2)
        }
    }
    
    # ===== 7. 热门组合（同队干员搭配）=====
    # 找每场比赛同队的干员组合
    team_combos = defaultdict(lambda: {'total': 0, 'wins': 0})
    
    for m in all_matches:
        round_records = m.get('round_records', [])
        players_per_round = m.get('total_players', 10)
        rounds_count = len(round_records) // max(players_per_round, 1) if players_per_round else 0
        
        if not round_records:
            continue
        
        # 按 round 分组
        player_summaries = {ps.get('profile_id'): ps.get('team') for ps in m.get('player_summaries', [])}
        
        # 简单：从 round_records 按每10条一组（每回合10个玩家的记录）
        chunk_size = players_per_round if players_per_round else 10
        for i in range(0, len(round_records), chunk_size):
            chunk = round_records[i:i+chunk_size]
            # 分成两队
            team_ops = defaultdict(list)
            for rd in chunk:
                pid = rd.get('profile_id', '')
                team = player_summaries.get(pid, -1)
                op = rd.get('operator', '')
                outcome = rd.get('outcome', '')
                if op and team >= 0:
                    team_ops[team].append((op, outcome))
            
            # 生成有序的干员组合
            for team_id, ops_list in team_ops.items():
                if len(ops_list) >= 2:
                    sorted_ops = sorted([o[0] for o in ops_list])
                    # 取 top 2 组合
                    for j in range(len(sorted_ops)):
                        for k in range(j+1, len(sorted_ops)):
                            combo_key = f"{sorted_ops[j]}+{sorted_ops[k]}"
                            team_combos[combo_key]['total'] += 1
                            if ops_list[0][1] == 'win':
                                team_combos[combo_key]['wins'] += 1
    
    # Top 30 组合
    top_combos = sorted(team_combos.items(), key=lambda x: -x[1]['total'])[:30]
    combo_data = []
    for combo, stats in top_combos:
        ops = combo.split('+')
        wr = round(stats['wins'] / max(stats['total'], 1) * 100, 2)
        combo_data.append({
            'operators': ops,
            'pickCount': stats['total'],
            'winRate': wr,
        })
    
    # ===== 8. 玩家表现排名 =====
    player_perf = defaultdict(lambda: {
        'kills': 0, 'deaths': 0, 'rounds': 0, 'wins': 0,
        'opening_kills': 0, 'headshots': 0, 'matches': set()
    })
    
    player_names = {}
    for m in all_matches:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id')
            name = ps.get('username')
            if pid and name:
                player_names[pid] = name
        
        for rd in m.get('round_records', []):
            pid = rd.get('profile_id', '')
            perf = player_perf[pid]
            perf['kills'] += rd.get('kills', 0)
            perf['deaths'] += rd.get('deaths', 0)
            perf['rounds'] += 1
            if rd.get('outcome') == 'win':
                perf['wins'] += 1
            perf['opening_kills'] += rd.get('opening_kills', 0)
            perf['headshots'] += rd.get('headshots', 0)
    
    # Top 50 by KD
    top_players = []
    for pid, perf in player_perf.items():
        if perf['rounds'] < 20:  # 至少20回合
            continue
        kd = round(perf['kills'] / max(perf['deaths'], 1), 2)
        wr = round(perf['wins'] / max(perf['rounds'], 1) * 100, 2)
        top_players.append({
            'profileId': pid,
            'username': player_names.get(pid, pid[:12]),
            'rounds': perf['rounds'],
            'kills': perf['kills'],
            'deaths': perf['deaths'],
            'kd': kd,
            'winRate': wr,
            'openingKills': perf['opening_kills'],
            'headshots': perf['headshots'],
        })
    
    top_players.sort(key=lambda x: -x['kd'])
    top_players = top_players[:50]
    
    # ===== 组装最终数据 =====
    final_data = {
        'overview': overview,
        'rankDistribution': dict(rank_distribution),
        'rpDistribution': dict(rp_distribution),
        'rpRanges': dict(rp_ranges),
        'mapStats': {k: v for k, v in sorted(map_stats.items(), key=lambda x: -x[1]['total'])},
        'operatorData': operator_data,
        'mapOperatorData': map_operator_data,
        'sideStats': side_stats,
        'topCombos': combo_data,
        'topPlayers': top_players,
    }
    
    # 输出 JS 文件
    js_content = f"// R6 Siege 玩家对局数据统计\n"
    js_content += f"// 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    js_content += f"// 数据来源: stats.cc 排行榜 + 比赛详情\n\n"
    js_content += f"const PLAYER_MATCH_STATS = {json.dumps(final_data, ensure_ascii=False, indent=2)};\n"
    
    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"\n输出文件: {OUTPUT_JS}")
    print(f"文件大小: {os.path.getsize(OUTPUT_JS) / 1024:.1f} KB")
    print(f"\n数据总览:")
    print(f"  排行榜玩家: {overview['totalLeaderboardPlayers']}")
    print(f"  采集玩家: {overview['totalPlayersProcessed']}")
    print(f"  比赛数: {overview['totalMatchesCollected']}")
    print(f"  回合记录: {overview['totalRoundRecords']}")
    print(f"  涉及玩家: {overview['totalUniquePlayers']}")
    print(f"  干员种类: {overview['totalUniqueOperators']}")
    print(f"  地图种类: {overview['totalUniqueMaps']}")
    print(f"  干员数据项: {len(operator_data)}")
    print(f"  地图干员交叉: {sum(len(v) for v in map_operator_data.values())}")


if __name__ == '__main__':
    main()

"""
统一数据聚合脚本 — 流式处理 ~18GB 采集数据
一次扫描同时生成:
  1. data/player_match_stats.js   (玩家对局统计)
  2. data/operator_map_stats.js   (地图×干员×段位统计)

支持:
  - PC 分片: output/match_data/shard_*/match_details.json  (JSON 数组)
  - Extra V2: output/extra_match_data/v2_shard_*/match_details.jsonl (JSONL)
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
LEADERBOARD_FILE = os.path.join(BASE_DIR, 'output', 'leaderboard', 'leaderboard_full.json')
OUTPUT_PLAYER_STATS = os.path.join(BASE_DIR, '..', 'player_match_stats.js')
OUTPUT_OPERATOR_MAP = os.path.join(BASE_DIR, '..', 'operator_map_stats.js')

# ==================== 干员阵营映射 ====================
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

RANK_TIERS = [
    (5000, 'Champion'), (4700, 'Diamond I'), (4400, 'Diamond II'),
    (4100, 'Emerald I'), (3800, 'Emerald II'), (3500, 'Platinum I'),
    (3200, 'Platinum II'), (2900, 'Gold I'), (2600, 'Gold II'),
    (2300, 'Silver I'), (2000, 'Silver II'), (1700, 'Bronze I'),
    (1400, 'Bronze II'), (1100, 'Copper I'), (0, 'Copper II'),
]

def get_rank_tier(rp):
    for threshold, tier in RANK_TIERS:
        if rp >= threshold:
            return tier
    return 'Copper II'

def get_side(operator):
    op = operator.lower().strip()
    if op in ATTACKERS: return 'attack'
    if op in DEFENDERS: return 'defense'
    return 'unknown'

# ==================== 聚合容器 ====================
class StreamingAggregator:
    def __init__(self):
        self.seen_match_ids = set()
        self.total_matches = 0
        self.total_rounds = 0
        self.total_source_players = set()
        self.all_player_ids = set()
        self.all_operators = set()
        self.all_maps = set()

        # player_match_stats 数据
        self.map_stats = defaultdict(lambda: {'total': 0, 'rounds': 0})
        self.operator_stats = defaultdict(lambda: {
            'total': 0, 'wins': 0, 'kills': 0, 'deaths': 0,
            'opening_kills': 0, 'headshots': 0, 'clutch': 0
        })
        self.map_operator = defaultdict(lambda: defaultdict(lambda: {
            'total': 0, 'wins': 0, 'kills': 0, 'deaths': 0
        }))
        self.attack_wins = 0
        self.attack_total = 0
        self.defense_wins = 0
        self.defense_total = 0
        self.player_perf = defaultdict(lambda: {
            'kills': 0, 'deaths': 0, 'rounds': 0, 'wins': 0,
            'opening_kills': 0, 'headshots': 0
        })
        self.player_names = {}

        # operator_map_stats 数据 (地图×干员×段位)
        self.oms_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
            'picks': 0, 'wins': 0, 'kills': 0, 'deaths': 0
        })))
        self.oms_map_rounds = defaultdict(int)

    def process_match(self, m):
        """处理单场比赛"""
        mid = m.get('match_id')
        if not mid or mid in self.seen_match_ids:
            return False
        self.seen_match_ids.add(mid)
        self.total_matches += 1

        map_name = m.get('map', 'unknown')
        self.all_maps.add(map_name)

        # source player
        sp = m.get('source_player', {})
        sp_id = sp.get('profileId', '')
        if sp_id:
            self.total_source_players.add(sp_id)
        # 尝试获取 source player 的段位
        sp_rank = sp.get('rank', '')
        sp_rp = sp.get('rankPoints', 0)
        rank_tier = get_rank_tier(sp_rp) if sp_rp else 'Unknown'

        # player summaries
        player_teams = {}
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id')
            name = ps.get('username')
            if pid:
                self.all_player_ids.add(pid)
                player_teams[pid] = ps.get('team', -1)
                if name:
                    self.player_names[pid] = name

        round_records = m.get('round_records', [])
        n_rounds = len(round_records)
        self.total_rounds += n_rounds

        # map stats
        self.map_stats[map_name]['total'] += 1
        self.map_stats[map_name]['rounds'] += n_rounds
        self.oms_map_rounds[map_name] += n_rounds

        for rd in round_records:
            op = rd.get('operator', '')
            if not op:
                continue
            self.all_operators.add(op)
            side = get_side(op)
            outcome = rd.get('outcome', '')
            is_win = outcome == 'win'
            kills = rd.get('kills', 0)
            deaths = rd.get('deaths', 0)
            ok = rd.get('opening_kills', 0)
            hs = rd.get('headshots', 0)
            clutch = rd.get('clutch', 0)

            # operator stats
            os_ = self.operator_stats[op]
            os_['total'] += 1
            if is_win: os_['wins'] += 1
            os_['kills'] += kills
            os_['deaths'] += deaths
            os_['opening_kills'] += ok
            os_['headshots'] += hs
            os_['clutch'] += clutch

            # map × operator
            mo = self.map_operator[map_name][op]
            mo['total'] += 1
            if is_win: mo['wins'] += 1
            mo['kills'] += kills
            mo['deaths'] += deaths

            # side stats
            if side == 'attack':
                self.attack_total += 1
                if is_win: self.attack_wins += 1
            elif side == 'defense':
                self.defense_total += 1
                if is_win: self.defense_wins += 1

            # player perf
            pid = rd.get('profile_id', '')
            if pid:
                pp = self.player_perf[pid]
                pp['kills'] += kills
                pp['deaths'] += deaths
                pp['rounds'] += 1
                if is_win: pp['wins'] += 1
                pp['opening_kills'] += ok
                pp['headshots'] += hs

            # operator_map_stats: 地图×干员×段位
            oms_side = 'ATK' if side == 'attack' else ('DEF' if side == 'defense' else 'UNK')
            oms = self.oms_data[map_name][op][rank_tier]
            oms['picks'] += 1
            if is_win: oms['wins'] += 1
            oms['kills'] += kills
            oms['deaths'] += deaths

        return True

    def scan_json_file(self, fpath):
        """流式扫描大 JSON 数组文件（使用 ijson 或分块读取）"""
        parent = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
        shard = os.path.basename(os.path.dirname(fpath))
        print(f"  Scanning {parent}/{shard}/match_details.json ...", end=' ', flush=True)

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            matches = data if isinstance(data, list) else [data]
            new_count = sum(1 for m in matches if self.process_match(m))
            print(f"{len(matches)} matches ({new_count} new)")
        except MemoryError:
            print(f"MemoryError! Trying line-by-line fallback...")
            self._scan_json_chunked(fpath)
        except Exception as e:
            print(f"ERROR: {e}")

    def _scan_json_chunked(self, fpath):
        """备用：逐行读取大 JSON"""
        import re
        new_count = 0
        buf = []
        depth = 0
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped == '[' or stripped == ']':
                    continue
                buf.append(line)
                depth += line.count('{') - line.count('}')
                if depth == 0 and buf:
                    text = ''.join(buf).strip().rstrip(',')
                    buf = []
                    try:
                        m = json.loads(text)
                        if self.process_match(m):
                            new_count += 1
                    except:
                        pass
        print(f"  (chunked) {new_count} new matches")

    def scan_jsonl_file(self, fpath):
        """流式扫描 JSONL 文件"""
        parent = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
        shard = os.path.basename(os.path.dirname(fpath))
        print(f"  Scanning {parent}/{shard}/match_details.jsonl ...", end=' ', flush=True)

        total = 0
        new_count = 0
        errors = 0
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    total += 1
                    try:
                        m = json.loads(line)
                        if self.process_match(m):
                            new_count += 1
                    except json.JSONDecodeError:
                        errors += 1
            err_str = f" ({errors} errors)" if errors else ""
            print(f"{total} lines ({new_count} new){err_str}")
        except Exception as e:
            print(f"ERROR: {e}")

    def scan_all(self):
        """扫描所有数据源"""
        print("\n" + "=" * 70)
        print("扫描所有比赛数据（流式处理）")
        print("=" * 70)

        # 1. PC 分片 (JSON)
        pattern = os.path.join(BASE_DIR, 'output', 'match_data', 'shard_*', 'match_details.json')
        json_files = sorted(glob.glob(pattern))
        print(f"\n[PC 分片] 发现 {len(json_files)} 个文件")
        for fpath in json_files:
            self.scan_json_file(fpath)
            gc.collect()

        # 2. Extra V2 分片 (JSONL)
        pattern = os.path.join(BASE_DIR, 'output', 'extra_match_data', 'v2_shard_*', 'match_details.jsonl')
        jsonl_files = sorted(glob.glob(pattern))
        print(f"\n[Extra V2 分片] 发现 {len(jsonl_files)} 个文件")
        for fpath in jsonl_files:
            self.scan_jsonl_file(fpath)
            gc.collect()

        # 3. 旧 Extra 分片 (JSON, 兼容)
        pattern = os.path.join(BASE_DIR, 'output', 'extra_match_data', 'shard_*', 'match_details.json')
        old_json_files = sorted(glob.glob(pattern))
        if old_json_files:
            print(f"\n[旧 Extra 分片] 发现 {len(old_json_files)} 个文件")
            for fpath in old_json_files:
                self.scan_json_file(fpath)
                gc.collect()

        print(f"\n{'='*70}")
        print(f"扫描完成!")
        print(f"  总比赛: {self.total_matches}")
        print(f"  总回合: {self.total_rounds}")
        print(f"  来源玩家: {len(self.total_source_players)}")
        print(f"  涉及玩家: {len(self.all_player_ids)}")
        print(f"  干员种类: {len(self.all_operators)}")
        print(f"  地图种类: {len(self.all_maps)}")
        print(f"{'='*70}")

    def generate_player_match_stats(self, leaderboard):
        """生成 player_match_stats.js"""
        print("\n生成 player_match_stats.js ...")

        # 排行榜段位分布
        rank_distribution = defaultdict(int)
        rp_distribution = defaultdict(int)
        rp_ranges = defaultdict(int)
        for p in leaderboard:
            rank = p.get('rank', 'unknown')
            rp = p.get('rankPoints', 0)
            rank_distribution[rank] += 1
            rp_distribution[get_rank_tier(rp)] += 1
            if rp >= 5000: rp_ranges['5000+'] += 1
            elif rp >= 4800: rp_ranges['4800-4999'] += 1
            elif rp >= 4600: rp_ranges['4600-4799'] += 1
            elif rp >= 4400: rp_ranges['4400-4599'] += 1
            elif rp >= 4200: rp_ranges['4200-4399'] += 1
            elif rp >= 4000: rp_ranges['4000-4199'] += 1
            elif rp >= 3800: rp_ranges['3800-3999'] += 1
            elif rp >= 3600: rp_ranges['3600-3799'] += 1
            elif rp >= 3400: rp_ranges['3400-3599'] += 1
            elif rp >= 3200: rp_ranges['3200-3399'] += 1
            else: rp_ranges['<3200'] += 1

        # 干员数据
        operator_data = []
        for op, stats in self.operator_stats.items():
            side = get_side(op)
            wr = round(stats['wins'] / max(stats['total'], 1) * 100, 2)
            kd = round(stats['kills'] / max(stats['deaths'], 1), 2)
            operator_data.append({
                'name': op, 'side': side, 'pickCount': stats['total'],
                'winRate': wr, 'wins': stats['wins'],
                'kills': stats['kills'], 'deaths': stats['deaths'], 'kd': kd,
                'openingKills': stats['opening_kills'],
                'headshots': stats['headshots'], 'clutch': stats['clutch'],
            })
        operator_data.sort(key=lambda x: -x['pickCount'])

        # 地图×干员交叉
        map_operator_data = {}
        for map_name, ops in self.map_operator.items():
            map_operator_data[map_name] = []
            for op, stats in ops.items():
                wr = round(stats['wins'] / max(stats['total'], 1) * 100, 2)
                kd = round(stats['kills'] / max(stats['deaths'], 1), 2)
                map_operator_data[map_name].append({
                    'name': op, 'side': get_side(op),
                    'pickCount': stats['total'], 'winRate': wr, 'kd': kd,
                    'kills': stats['kills'], 'deaths': stats['deaths'],
                })
            map_operator_data[map_name].sort(key=lambda x: -x['pickCount'])

        side_stats = {
            'attack': {'total': self.attack_total, 'wins': self.attack_wins,
                       'winRate': round(self.attack_wins / max(self.attack_total, 1) * 100, 2)},
            'defense': {'total': self.defense_total, 'wins': self.defense_wins,
                        'winRate': round(self.defense_wins / max(self.defense_total, 1) * 100, 2)},
        }

        # Top 50 玩家
        top_players = []
        for pid, perf in self.player_perf.items():
            if perf['rounds'] < 20:
                continue
            kd = round(perf['kills'] / max(perf['deaths'], 1), 2)
            wr = round(perf['wins'] / max(perf['rounds'], 1) * 100, 2)
            top_players.append({
                'profileId': pid,
                'username': self.player_names.get(pid, pid[:12]),
                'rounds': perf['rounds'], 'kills': perf['kills'],
                'deaths': perf['deaths'], 'kd': kd, 'winRate': wr,
                'openingKills': perf['opening_kills'], 'headshots': perf['headshots'],
            })
        top_players.sort(key=lambda x: -x['kd'])
        top_players = top_players[:50]

        overview = {
            'totalLeaderboardPlayers': len(leaderboard),
            'totalPlayersProcessed': len(self.total_source_players),
            'totalMatchesCollected': self.total_matches,
            'totalRoundRecords': self.total_rounds,
            'totalUniquePlayers': len(self.all_player_ids),
            'totalUniqueOperators': len(self.all_operators),
            'totalUniqueMaps': len(self.all_maps),
            'generatedAt': datetime.now().isoformat(),
            'dataSource': 'stats.cc (排行榜 + 比赛详情)',
            'season': 'Silent Hunt (Y11S1)',
        }

        final_data = {
            'overview': overview,
            'rankDistribution': dict(rank_distribution),
            'rpDistribution': dict(rp_distribution),
            'rpRanges': dict(rp_ranges),
            'mapStats': {k: v for k, v in sorted(self.map_stats.items(), key=lambda x: -x[1]['total'])},
            'operatorData': operator_data,
            'mapOperatorData': map_operator_data,
            'sideStats': side_stats,
            'topCombos': [],  # 跳过组合统计（需要大量内存追踪同队关系）
            'topPlayers': top_players,
        }

        js = f"// R6 Siege 玩家对局数据统计\n"
        js += f"// 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        js += f"// 数据来源: stats.cc 排行榜 + 比赛详情 (PC + Extra 完整数据)\n\n"
        js += f"const PLAYER_MATCH_STATS = {json.dumps(final_data, ensure_ascii=False, indent=2)};\n"

        with open(OUTPUT_PLAYER_STATS, 'w', encoding='utf-8') as f:
            f.write(js)

        size_kb = os.path.getsize(OUTPUT_PLAYER_STATS) / 1024
        print(f"  ✅ {OUTPUT_PLAYER_STATS} ({size_kb:.1f} KB)")
        return overview

    def generate_operator_map_stats(self):
        """生成 operator_map_stats.js"""
        print("\n生成 operator_map_stats.js ...")

        rankings = {}
        for map_id, operators in self.oms_data.items():
            rankings[map_id] = {'attackers': [], 'defenders': [], 'overall': []}
            map_total_rounds = self.oms_map_rounds.get(map_id, 1)

            for op_id, ranks in operators.items():
                total_picks = sum(r['picks'] for r in ranks.values())
                total_wins = sum(r['wins'] for r in ranks.values())
                total_kills = sum(r['kills'] for r in ranks.values())
                total_deaths = sum(r['deaths'] for r in ranks.values())

                side = get_side(op_id)
                entry = {
                    'operator': op_id,
                    'picks': total_picks,
                    'pickRate': f"{total_picks / map_total_rounds * 100:.2f}%",
                    'winRate': f"{total_wins / max(total_picks, 1) * 100:.2f}%",
                    'kd': f"{total_kills / max(total_deaths, 1):.2f}",
                    'wins': total_wins,
                    'side': 'ATK' if side == 'attack' else ('DEF' if side == 'defense' else 'UNK')
                }

                rankings[map_id]['overall'].append(entry)
                if side == 'attack':
                    rankings[map_id]['attackers'].append(entry)
                elif side == 'defense':
                    rankings[map_id]['defenders'].append(entry)

            for key in ['attackers', 'defenders', 'overall']:
                rankings[map_id][key].sort(key=lambda x: -x['picks'])

        # 段位分组
        rank_breakdown = {}
        for map_id, operators in self.oms_data.items():
            rank_breakdown[map_id] = {}
            for op_id, ranks in operators.items():
                for rank_name, stat in ranks.items():
                    if rank_name not in rank_breakdown[map_id]:
                        rank_breakdown[map_id][rank_name] = []
                    if stat['picks'] > 0:
                        rank_breakdown[map_id][rank_name].append({
                            'operator': op_id,
                            'picks': stat['picks'],
                            'winRate': f"{stat['wins'] / max(stat['picks'], 1) * 100:.2f}%",
                            'kd': f"{stat['kills'] / max(stat['deaths'], 1):.2f}",
                            'side': 'ATK' if get_side(op_id) == 'attack' else 'DEF'
                        })
            for rn in rank_breakdown[map_id]:
                rank_breakdown[map_id][rn].sort(key=lambda x: -x['picks'])

        now = datetime.now().isoformat()
        js = f"""/**
 * Rainbow Six Siege - 地图 × 干员 统计数据
 *
 * 数据来源: stats.cc 玩家对局数据 (PC排行榜 + Extra玩家)
 * 生成时间: {now}
 * 样本量: {self.total_matches} 场对局, {self.total_rounds} 回合
 * 覆盖地图: {len(self.all_maps)} 张
 * 覆盖干员: {len(self.all_operators)} 个
 */

const OPERATOR_MAP_STATS = {{
  metadata: {json.dumps({
      'generatedAt': now,
      'totalMatches': self.total_matches,
      'totalRounds': self.total_rounds,
      'mapsCount': len(self.all_maps),
      'operatorsCount': len(self.all_operators),
      'source': 'stats.cc (排行榜 + 比赛详情)'
  }, ensure_ascii=False, indent=4)},

  rankings: {json.dumps(rankings, ensure_ascii=False, indent=2)},

  rankBreakdown: {json.dumps(rank_breakdown, ensure_ascii=False, indent=2)},

  rawStats: {{}}
}};

// 导出
if (typeof module !== 'undefined' && module.exports) {{
  module.exports = {{ OPERATOR_MAP_STATS }};
}}
"""
        with open(OUTPUT_OPERATOR_MAP, 'w', encoding='utf-8') as f:
            f.write(js)

        size_kb = os.path.getsize(OUTPUT_OPERATOR_MAP) / 1024
        print(f"  ✅ {OUTPUT_OPERATOR_MAP} ({size_kb:.1f} KB)")


def main():
    print("=" * 70)
    print("R6 统一数据聚合 (流式处理)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 加载排行榜
    print("\n加载排行榜数据...")
    with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
        leaderboard = json.load(f)
    print(f"  排行榜: {len(leaderboard)} 玩家")

    # 流式扫描所有数据
    agg = StreamingAggregator()
    agg.scan_all()

    # 生成两个输出文件
    overview = agg.generate_player_match_stats(leaderboard)
    agg.generate_operator_map_stats()

    print("\n" + "=" * 70)
    print("✅ 全部完成!")
    print(f"  player_match_stats.js  -> {OUTPUT_PLAYER_STATS}")
    print(f"  operator_map_stats.js  -> {OUTPUT_OPERATOR_MAP}")
    print("=" * 70)


if __name__ == '__main__':
    main()

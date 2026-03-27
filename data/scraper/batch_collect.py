"""
R6 Siege 玩家对局数据批量采集脚本
===================================
三步流水线：
  Step 1: 从排行榜获取玩家列表（已完成，使用现有 leaderboard_full.json）
  Step 2: 从 stats.cc 玩家页面获取比赛历史（match_id + 地图）
  Step 3: 从 stats.cc 比赛详情页获取回合级干员选择数据

用法:
  python batch_collect.py [--max-players 50] [--max-matches 20] [--delay 2]
  python batch_collect.py --resume  # 从中断处继续
"""
import requests
import re
import sys
import io
import json
import os
import time
import argparse
import hashlib
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# 输出目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
PROGRESS_FILE = os.path.join(OUTPUT_DIR, '_progress.json')
SUMMARY_FILE = os.path.join(OUTPUT_DIR, '_summary.json')

# ===== Nuxt 数据解析 =====
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


def parse_nuxt_page(html):
    """从 HTML 中解析 Nuxt SSR 数据"""
    json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not json_blocks:
        return None
    return json.loads(json_blocks[0])


# ===== Step 2: 获取玩家比赛历史 =====
def fetch_player_matches(player_name, profile_id, retries=3):
    """从 stats.cc 玩家页面获取比赛历史"""
    url = f'https://stats.cc/siege/{player_name}/{profile_id}'
    
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = (attempt + 1) * 15
                print(f"    [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                print(f"    [!] HTTP {r.status_code}")
                return None
            
            nuxt = parse_nuxt_page(r.text)
            if not nuxt:
                return None
            
            # 提取比赛历史
            matches = []
            for i in range(len(nuxt)):
                item = nuxt[i]
                if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
                    match = deref(nuxt, i, max_depth=20)
                    if match and isinstance(match.get('id'), str) and len(match.get('id', '')) > 10:
                        matches.append({
                            'match_id': match.get('id'),
                            'map': match.get('map'),
                            'playlist': match.get('playlist'),
                            'mode': match.get('mode'),
                            'scores': match.get('scores'),
                            'started_at': match.get('started_at'),
                            'ended_at': match.get('ended_at'),
                            'outcome': match.get('outcome'),
                        })
            
            return matches
            
        except Exception as e:
            print(f"    [!] Error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    
    return None


# ===== Step 3: 获取比赛详情（回合级干员数据）=====
def fetch_match_detail(match_id, retries=3):
    """从 stats.cc 比赛详情页获取完整回合数据"""
    url = f'https://stats.cc/siege/matches/{match_id}'
    
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = (attempt + 1) * 15
                print(f"      [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                return None
            
            nuxt = parse_nuxt_page(r.text)
            if not nuxt:
                return None
            
            # 1. 提取比赛元数据
            match_meta = None
            for i in range(len(nuxt)):
                item = nuxt[i]
                if isinstance(item, dict) and 'map' in item and 'scores' in item and 'playlist' in item:
                    match_meta = deref(nuxt, i, max_depth=15)
                    break
            
            # 2. 提取每回合每玩家的干员选择 + 表现
            round_data = []
            for i in range(len(nuxt)):
                item = nuxt[i]
                if isinstance(item, dict) and 'operator' in item and 'outcome' in item and 'profile_id' in item:
                    resolved = deref(nuxt, i, max_depth=12)
                    if resolved:
                        round_data.append(resolved)
            
            # 3. 提取玩家汇总数据
            player_summaries = []
            for i in range(len(nuxt)):
                item = nuxt[i]
                if isinstance(item, dict) and 'username' in item and 'rounds' in item and 'round_wins' in item and 'team' in item:
                    resolved = deref(nuxt, i, max_depth=12)
                    if resolved:
                        player_summaries.append(resolved)
            
            if not round_data:
                return None
            
            return {
                'match_id': match_id,
                'map': match_meta.get('map') if match_meta else None,
                'playlist': match_meta.get('playlist') if match_meta else None,
                'mode': match_meta.get('mode') if match_meta else None,
                'scores': match_meta.get('scores') if match_meta else None,
                'started_at': match_meta.get('started_at') if match_meta else None,
                'ended_at': match_meta.get('ended_at') if match_meta else None,
                'player_summaries': player_summaries,
                'round_records': round_data,
                'total_rounds': len(round_data) // max(len(player_summaries), 1) if player_summaries else 0,
                'total_players': len(player_summaries),
            }
            
        except Exception as e:
            print(f"      [!] Error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    
    return None


# ===== 进度管理 =====
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'completed_players': [],
        'completed_matches': [],
        'failed_players': [],
        'failed_matches': [],
        'player_match_map': {},  # player_id -> [match_ids]
        'stats': {
            'total_players_processed': 0,
            'total_matches_fetched': 0,
            'total_match_details_fetched': 0,
            'total_round_records': 0,
            'start_time': datetime.now().isoformat(),
        }
    }


def save_progress(progress):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ===== 主流程 =====
def main():
    parser = argparse.ArgumentParser(description='R6 Siege 玩家对局数据批量采集')
    parser.add_argument('--max-players', type=int, default=100, help='最多采集多少个玩家 (default: 100)')
    parser.add_argument('--max-matches-per-player', type=int, default=20, help='每个玩家最多采集多少场对局详情 (default: 20)')
    parser.add_argument('--delay', type=float, default=2.0, help='请求间隔秒数 (default: 2.0)')
    parser.add_argument('--resume', action='store_true', help='从中断处继续')
    parser.add_argument('--leaderboard', type=str, 
                        default=os.path.join(BASE_DIR, 'output', 'leaderboard', 'leaderboard_full.json'),
                        help='排行榜数据文件路径')
    args = parser.parse_args()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载排行榜数据
    if not os.path.exists(args.leaderboard):
        print(f"[!] 排行榜文件不存在: {args.leaderboard}")
        print("    请先运行 fetch_leaderboard.py 获取排行榜数据")
        return
    
    with open(args.leaderboard, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    print("=" * 70)
    print("R6 Siege 玩家对局数据批量采集")
    print("=" * 70)
    print(f"排行榜玩家数: {len(players)}")
    print(f"本次采集上限: {args.max_players} 玩家")
    print(f"每人对局上限: {args.max_matches_per_player}")
    print(f"请求间隔: {args.delay}s")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    # 加载/创建进度
    progress = load_progress() if args.resume else load_progress()
    completed_players = set(progress['completed_players'])
    completed_matches = set(progress['completed_matches'])
    
    # 所有采集到的对局详情
    all_match_details = []
    # 加载已有数据
    existing_data_file = os.path.join(OUTPUT_DIR, 'all_match_details.json')
    if args.resume and os.path.exists(existing_data_file):
        with open(existing_data_file, 'r', encoding='utf-8') as f:
            all_match_details = json.load(f)
        print(f"[RESUME] 已有 {len(all_match_details)} 场比赛数据")
    
    players_to_process = [p for p in players[:args.max_players] if p['profileId'] not in completed_players]
    print(f"待处理玩家: {len(players_to_process)}")
    print()
    
    total_new_matches = 0
    total_new_details = 0
    
    for idx, player in enumerate(players_to_process):
        player_name = player['displayName']
        profile_id = player['profileId']
        rank = player.get('rank', 'unknown')
        rp = player.get('rankPoints', 0)
        
        print(f"\n[{idx+1}/{len(players_to_process)}] {player_name} (#{player.get('leaderboardPosition', '?')}, {rank}, RP:{rp})")
        
        # Step 2: 获取比赛历史
        print(f"  Step 2: 获取比赛历史...")
        matches = fetch_player_matches(player_name, profile_id)
        
        if matches is None:
            print(f"  [FAIL] 无法获取比赛历史")
            progress['failed_players'].append(profile_id)
            save_progress(progress)
            time.sleep(args.delay)
            continue
        
        # 只保留 ranked 比赛
        ranked_matches = [m for m in matches if m.get('playlist') == 'ranked']
        print(f"  找到 {len(matches)} 场比赛, 其中 ranked: {len(ranked_matches)}")
        
        # 记录玩家的 match_ids
        progress['player_match_map'][profile_id] = {
            'displayName': player_name,
            'rank': rank,
            'rankPoints': rp,
            'match_ids': [m['match_id'] for m in ranked_matches],
        }
        
        total_new_matches += len(ranked_matches)
        
        # Step 3: 获取比赛详情
        new_matches = [m for m in ranked_matches if m['match_id'] not in completed_matches]
        to_fetch = new_matches[:args.max_matches_per_player]
        
        print(f"  Step 3: 获取比赛详情 ({len(to_fetch)} 场新比赛)...")
        
        for midx, match in enumerate(to_fetch):
            match_id = match['match_id']
            map_name = match.get('map', '?')
            
            print(f"    [{midx+1}/{len(to_fetch)}] {match_id[:12]}... ({map_name})", end=' ')
            
            detail = fetch_match_detail(match_id)
            
            if detail:
                # 补充来源玩家信息
                detail['source_player'] = {
                    'displayName': player_name,
                    'profileId': profile_id,
                    'rank': rank,
                    'rankPoints': rp,
                }
                all_match_details.append(detail)
                completed_matches.add(match_id)
                progress['completed_matches'].append(match_id)
                progress['stats']['total_match_details_fetched'] += 1
                progress['stats']['total_round_records'] += len(detail.get('round_records', []))
                total_new_details += 1
                
                rounds = len(detail.get('round_records', []))
                players_count = detail.get('total_players', 0)
                print(f"OK ({players_count}p, {rounds}r)")
            else:
                print(f"FAIL")
                progress['failed_matches'].append(match_id)
            
            time.sleep(args.delay)
        
        # 标记玩家完成
        completed_players.add(profile_id)
        progress['completed_players'].append(profile_id)
        progress['stats']['total_players_processed'] += 1
        progress['stats']['total_matches_fetched'] += len(ranked_matches)
        
        # 每5个玩家保存一次
        if (idx + 1) % 5 == 0:
            save_progress(progress)
            with open(existing_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_match_details, f, ensure_ascii=False, indent=2)
            print(f"\n  [SAVE] 已保存: {len(all_match_details)} 场比赛, {progress['stats']['total_round_records']} 条回合记录")
        
        time.sleep(args.delay)
    
    # 最终保存
    save_progress(progress)
    with open(existing_data_file, 'w', encoding='utf-8') as f:
        json.dump(all_match_details, f, ensure_ascii=False, indent=2)
    
    # 生成摘要
    summary = generate_summary(all_match_details, players, progress)
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"采集完成!")
    print(f"{'=' * 70}")
    print(f"玩家处理: {progress['stats']['total_players_processed']}")
    print(f"比赛历史: {progress['stats']['total_matches_fetched']}")
    print(f"比赛详情: {progress['stats']['total_match_details_fetched']}")
    print(f"回合记录: {progress['stats']['total_round_records']}")
    print(f"新增对局: {total_new_details}")
    print(f"数据文件: {existing_data_file}")
    print(f"摘要文件: {SUMMARY_FILE}")


def generate_summary(all_match_details, leaderboard_players, progress):
    """生成数据统计摘要"""
    # 段位分布
    rank_distribution = {}
    for p in leaderboard_players:
        rank = p.get('rank', 'unknown')
        rank_distribution[rank] = rank_distribution.get(rank, 0) + 1
    
    # 地图分布
    map_distribution = {}
    for m in all_match_details:
        map_name = m.get('map', 'unknown')
        map_distribution[map_name] = map_distribution.get(map_name, 0) + 1
    
    # 干员使用统计
    operator_usage = {'attack': {}, 'defense': {}}
    # 干员的攻防判断：如果outcome中同一干员交替出现在不同阵营，我们通过回合数来区分
    all_operators = set()
    for m in all_match_details:
        for rd in m.get('round_records', []):
            op = rd.get('operator', '')
            if op:
                all_operators.add(op)
    
    # 收集所有涉及到的玩家
    all_player_ids = set()
    for m in all_match_details:
        for ps in m.get('player_summaries', []):
            pid = ps.get('profile_id')
            if pid:
                all_player_ids.add(pid)
    
    # 干员使用频率
    operator_counts = {}
    operator_wins = {}
    for m in all_match_details:
        for rd in m.get('round_records', []):
            op = rd.get('operator', '')
            outcome = rd.get('outcome', '')
            if op:
                operator_counts[op] = operator_counts.get(op, 0) + 1
                if outcome == 'win':
                    operator_wins[op] = operator_wins.get(op, 0) + 1
    
    # 段位参与分布（从 source_player 获取）
    rank_in_data = {}
    for m in all_match_details:
        sp = m.get('source_player', {})
        rank = sp.get('rank', 'unknown')
        rank_in_data[rank] = rank_in_data.get(rank, 0) + 1
    
    return {
        'generated_at': datetime.now().isoformat(),
        'overview': {
            'total_leaderboard_players': len(leaderboard_players),
            'total_players_processed': progress['stats']['total_players_processed'],
            'total_matches_in_history': progress['stats']['total_matches_fetched'],
            'total_match_details': len(all_match_details),
            'total_round_records': progress['stats']['total_round_records'],
            'total_unique_players_in_matches': len(all_player_ids),
            'total_unique_operators': len(all_operators),
            'total_unique_maps': len(map_distribution),
        },
        'rank_distribution_leaderboard': dict(sorted(rank_distribution.items(), key=lambda x: -x[1])),
        'rank_distribution_in_data': dict(sorted(rank_in_data.items(), key=lambda x: -x[1])),
        'map_distribution': dict(sorted(map_distribution.items(), key=lambda x: -x[1])),
        'operator_usage_top20': dict(sorted(operator_counts.items(), key=lambda x: -x[1])[:20]),
        'operator_win_rates': {
            op: {
                'total': operator_counts.get(op, 0),
                'wins': operator_wins.get(op, 0),
                'win_rate': round(operator_wins.get(op, 0) / max(operator_counts.get(op, 1), 1) * 100, 2)
            }
            for op in sorted(operator_counts.keys(), key=lambda x: -operator_counts[x])[:30]
        },
        'failed_players': len(progress['failed_players']),
        'failed_matches': len(progress['failed_matches']),
    }


if __name__ == '__main__':
    main()

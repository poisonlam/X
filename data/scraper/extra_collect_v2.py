"""
从已有比赛数据中提取额外玩家，并采集他们的比赛数据 (v2 增强版)
================================================================
增强功能：
1. Session 健康检测 + 自动重建
2. 数据脱敏检测（通过 id_mapping 模块）
3. 事件日志输出（供监控面板读取）
4. 查漏补缺机制

用法:
  python extra_collect_v2.py extract
  python extra_collect_v2.py plan --shards 8
  python extra_collect_v2.py run --shard-id 0 --total-shards 8
  python extra_collect_v2.py status --total-shards 8
  python extra_collect_v2.py merge --total-shards 8
"""
import requests
import re
import sys
import io
import json
import os
import time
import argparse
import random
from datetime import datetime
from collections import deque

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入名称映射模块
try:
    from id_mapping import get_mapper
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from id_mapping import get_mapper

# 导入 v2 公共组件
try:
    from parallel_collect_v2 import (
        get_session, bump_request_count,
        deref, parse_nuxt_page,
        SessionHealthMonitor, emit_event,
        fetch_match_detail,
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from parallel_collect_v2 import (
        get_session, bump_request_count,
        deref, parse_nuxt_page,
        SessionHealthMonitor, emit_event,
        fetch_match_detail,
    )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'extra_match_data')
LB_DIR = os.path.join(BASE_DIR, 'output', 'leaderboard')
MAIN_MATCH_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
EXTRA_PLAYERS_FILE = os.path.join(OUTPUT_DIR, '_extra_players.json')
ANOMALY_PLAYERS_FILE = os.path.join(OUTPUT_DIR, '_anomaly_players.json')
EVENT_LOG_DIR = os.path.join(OUTPUT_DIR, '_events')


def load_anomaly_players():
    if os.path.exists(ANOMALY_PLAYERS_FILE):
        try:
            with open(ANOMALY_PLAYERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_anomaly_player(player_name, profile_id, reason="HTTP 500 无比赛数据"):
    anomaly_list = load_anomaly_players()
    existing_ids = {p['profile_id'] for p in anomaly_list}
    if profile_id not in existing_ids:
        anomaly_list.append({
            'player_name': player_name,
            'profile_id': profile_id,
            'reason': reason,
            'recorded_at': datetime.now().isoformat(),
        })
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(ANOMALY_PLAYERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(anomaly_list, f, ensure_ascii=False, indent=2)


def emit_extra_event(shard_id, event_type, data=None):
    """写入额外采集的事件日志"""
    os.makedirs(EVENT_LOG_DIR, exist_ok=True)
    event = {
        'timestamp': datetime.now().isoformat(),
        'shard_id': shard_id,
        'type': event_type,
        'source': 'extra',
        'data': data or {},
    }
    event_file = os.path.join(EVENT_LOG_DIR, f'extra_shard_{shard_id}_events.jsonl')
    try:
        with open(event_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    except Exception:
        pass
    
    status_file = os.path.join(EVENT_LOG_DIR, f'extra_shard_{shard_id}_status.json')
    status = {
        'shard_id': shard_id,
        'source': 'extra',
        'last_event': event_type,
        'last_event_time': event['timestamp'],
        'last_event_data': data or {},
    }
    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False)
    except Exception:
        pass


# ===== 数据获取函数（额外玩家特化版）=====
def fetch_player_matches_extra(player_name, profile_id, retries=4, mapper=None):
    """获取玩家比赛历史 + 段位信息（额外玩家版）"""
    session = get_session()
    bump_request_count()
    url = f'https://stats.cc/siege/{player_name}/{profile_id}'
    
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=(10, 25))
            if r.status_code == 429:
                wait = min(5 * (2 ** attempt), 60)
                print(f"    [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 404:
                return None
            
            if r.status_code == 500 or r.status_code == 200:
                nuxt = parse_nuxt_page(r.text)
                if nuxt:
                    # 提取玩家段位信息
                    player_info = {}
                    for i in range(len(nuxt)):
                        item = nuxt[i]
                        if isinstance(item, dict) and 'rank' in item and 'rankPoints' in item and 'wins' in item:
                            resolved = deref(nuxt, i, max_depth=15)
                            if resolved and isinstance(resolved.get('rankPoints'), (int, float)):
                                player_info = resolved
                                break
                    
                    matches = []
                    for i in range(len(nuxt)):
                        item = nuxt[i]
                        if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
                            match = deref(nuxt, i, max_depth=20)
                            if match and isinstance(match.get('id'), str) and len(match.get('id', '')) > 10:
                                raw_map = match.get('map', '')
                                if mapper and raw_map:
                                    mapper.normalize_map(raw_map)
                                matches.append({
                                    'match_id': match.get('id'),
                                    'map': raw_map,
                                    'playlist': match.get('playlist'),
                                    'mode': match.get('mode'),
                                    'scores': match.get('scores'),
                                    'started_at': match.get('started_at'),
                                    'ended_at': match.get('ended_at'),
                                    'outcome': match.get('outcome'),
                                })
                    
                    if matches:
                        if r.status_code == 500:
                            print(f"    [*] HTTP 500 但解析到 {len(matches)} 个比赛")
                        return {'matches': matches, 'player_info': player_info}
                    elif r.status_code == 500:
                        return []
                    elif r.status_code == 200:
                        return {'matches': [], 'player_info': player_info}
            
            if r.status_code != 200:
                print(f"    [!] HTTP {r.status_code} (attempt {attempt+1})")
                if r.status_code >= 500 and attempt < retries - 1:
                    wait = min(10 * (2 ** attempt), 120)
                    time.sleep(wait)
                    continue
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return None
            
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"    [!] Connection error: {e}")
            if attempt < retries - 1:
                time.sleep(3)
        except requests.exceptions.Timeout:
            print(f"    [!] Timeout (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(2)
        except Exception as e:
            print(f"    [!] Error: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


# ===== Shard helpers =====
def shard_output_dir(shard_id):
    return os.path.join(OUTPUT_DIR, f'shard_{shard_id}')

def shard_progress_file(shard_id):
    return os.path.join(OUTPUT_DIR, f'_shard_{shard_id}_progress.json')

def shard_data_file(shard_id):
    return os.path.join(shard_output_dir(shard_id), 'match_details.json')


def load_all_known_match_ids():
    """加载所有已知的 match IDs（避免重复采集）"""
    known = set()
    for shard_id in range(20):
        pfile = os.path.join(MAIN_MATCH_DIR, f'_shard_{shard_id}_progress.json')
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            known.update(sp.get('completed_matches', []))
    
    gp_file = os.path.join(MAIN_MATCH_DIR, '_progress.json')
    if os.path.exists(gp_file):
        with open(gp_file, 'r', encoding='utf-8') as f:
            gp = json.load(f)
        known.update(gp.get('completed_matches', []))
    
    # 共享 match IDs
    shared_file = os.path.join(MAIN_MATCH_DIR, '_shared_match_ids.json')
    if os.path.exists(shared_file):
        try:
            with open(shared_file, 'r', encoding='utf-8') as f:
                known.update(json.load(f))
        except:
            pass
    
    for shard_id in range(20):
        pfile = shard_progress_file(shard_id)
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            known.update(sp.get('completed_matches', []))
    
    return known


# ===== Extract =====
def cmd_extract(args):
    """从已采集的比赛数据中提取额外玩家"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    known_lb_ids = set()
    lb_files = [
        os.path.join(LB_DIR, 'leaderboard_full.json'),
        os.path.join(LB_DIR, 'leaderboard_console.json'),
        os.path.join(LB_DIR, 'leaderboard_global.json'),
    ]
    for f in lb_files:
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            ids = set(p['profileId'] for p in data if p.get('profileId'))
            known_lb_ids.update(ids)
            print(f"Loaded {len(ids)} players from {os.path.basename(f)}")
    
    print(f"Total known leaderboard players: {len(known_lb_ids)}")
    
    extra_players = {}
    
    for shard_id in range(20):
        for base_dir in [MAIN_MATCH_DIR, OUTPUT_DIR]:
            shard_dir = os.path.join(base_dir, f'shard_{shard_id}')
            match_file = os.path.join(shard_dir, 'match_details.json')
            if not os.path.exists(match_file):
                continue
            
            dir_label = 'main' if base_dir == MAIN_MATCH_DIR else 'extra'
            print(f"Processing {dir_label}/shard_{shard_id}...", end=' ', flush=True)
            with open(match_file, 'r', encoding='utf-8') as fh:
                matches = json.load(fh)
            
            count = 0
            for match in matches:
                for ps in match.get('player_summaries', []):
                    pid = ps.get('profile_id', '')
                    uname = ps.get('username', '')
                    if pid and pid not in known_lb_ids:
                        if pid not in extra_players:
                            extra_players[pid] = {
                                'profileId': pid,
                                'displayName': uname,
                                'appearances': 0,
                                'first_seen_in_match': match.get('match_id', ''),
                            }
                        extra_players[pid]['appearances'] += 1
                        if uname and not extra_players[pid]['displayName']:
                            extra_players[pid]['displayName'] = uname
                        count += 1
            
            print(f"{len(matches)} matches, {count} extra appearances")
    
    player_list = sorted(extra_players.values(), key=lambda x: -x['appearances'])
    player_list = [p for p in player_list if p.get('displayName')]
    
    with open(EXTRA_PLAYERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(player_list, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"提取完成!")
    print(f"额外玩家总数: {len(player_list)}")
    print(f"  出现 >= 5 次: {len([p for p in player_list if p['appearances'] >= 5])}")
    print(f"  出现 >= 3 次: {len([p for p in player_list if p['appearances'] >= 3])}")
    print(f"保存到: {EXTRA_PLAYERS_FILE}")


# ===== Plan =====
def cmd_plan(args):
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print("[ERROR] Extra players file not found. Run 'extract' first.")
        return
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    done = set()
    for shard_id in range(args.shards):
        pfile = shard_progress_file(shard_id)
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            done.update(sp.get('completed_players', []))
    
    remaining = [p for p in players if p['profileId'] not in done]
    
    print("=" * 70)
    print("额外玩家采集 v2 - 分片规划")
    print("=" * 70)
    print(f"总数: {len(players)}, 已完成: {len(done)}, 剩余: {len(remaining)}")
    print(f"分片数: {args.shards}")
    print()
    for shard_id in range(args.shards):
        count = len([i for i in range(len(remaining)) if i % args.shards == shard_id])
        print(f"  Shard {shard_id}: {count} 玩家")


# ===== Run =====
def cmd_run(args):
    shard_id = args.shard_id
    total_shards = args.total_shards
    max_matches = args.max_matches
    delay = args.delay
    batch_size = args.batch_size
    
    os.makedirs(shard_output_dir(shard_id), exist_ok=True)
    os.makedirs(EVENT_LOG_DIR, exist_ok=True)
    
    mapper = get_mapper()
    health = SessionHealthMonitor(shard_id + 100, threshold=args.health_threshold)  # +100 避免与PC分片冲突
    
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print("[ERROR] Extra players file not found. Run 'extract' first.")
        return
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        all_extra_players = json.load(f)
    
    progress_file = shard_progress_file(shard_id)
    shard_completed = set()
    shard_completed_matches = set()
    
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            sp = json.load(f)
            shard_completed = set(sp.get('completed_players', []))
            shard_completed_matches = set(sp.get('completed_matches', []))
    
    remaining = [p for p in all_extra_players if p['profileId'] not in shard_completed]
    shard_players = [p for i, p in enumerate(remaining) if i % total_shards == shard_id]
    
    data_file = shard_data_file(shard_id)
    all_details = []
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            all_details = json.load(f)
        for d in all_details:
            shard_completed_matches.add(d['match_id'])
    
    all_known_matches = load_all_known_match_ids()
    all_known_matches.update(shard_completed_matches)
    
    print("=" * 70)
    print(f"Extra Shard {shard_id}/{total_shards-1} - v2 增强版")
    print("=" * 70)
    print(f"总额外玩家: {len(all_extra_players)}")
    print(f"本分片待处理: {len(shard_players)}")
    print(f"已完成: {len(shard_completed)}")
    print(f"已有比赛数据: {len(all_details)}")
    print(f"全局已知match IDs: {len(all_known_matches)}")
    print(f"Session审查阈值: {args.health_threshold}")
    print()
    
    emit_extra_event(shard_id, 'shard_start', {
        'total_players': len(shard_players),
        'existing_matches': len(all_details),
    })
    
    new_players_done = 0
    new_matches_done = 0
    players_with_rank_info = 0
    
    for idx, player in enumerate(shard_players):
        player_name = player['displayName']
        profile_id = player['profileId']
        appearances = player.get('appearances', 0)
        
        print(f"[ExS{shard_id}][{idx+1}/{len(shard_players)}] {player_name} (seen {appearances}x)")
        
        result = fetch_player_matches_extra(player_name, profile_id, mapper=mapper)
        
        if result is None:
            health.record_error(player_name)
            print(f"  [FAIL] Cannot get data (consecutive errors: {health.consecutive_errors})")
            
            if health.should_review():
                session_ok, needs_backtrack, bt_players = health.do_review()
                if not session_ok:
                    time.sleep(30)
            
            time.sleep(delay * 2)
            continue
        
        elif isinstance(result, list) and len(result) == 0:
            health.record_success(player_name, 0)
            save_anomaly_player(player_name, profile_id)
            shard_completed.add(profile_id)
            
            emit_extra_event(shard_id, 'match_not_found', {
                'player': player_name,
                'consecutive_empty': health.consecutive_empty,
            })
            
            if health.should_review():
                health.do_review()
            
            time.sleep(delay)
            continue
        
        elif not isinstance(result, dict):
            save_anomaly_player(player_name, profile_id, f"result异常: {type(result).__name__}")
            shard_completed.add(profile_id)
            health.record_success(player_name, 0)
            time.sleep(delay)
            continue
        
        else:
            matches = result.get('matches', [])
            health.record_success(player_name, len(matches))
        
        player_info = result.get('player_info', {})
        rank = player_info.get('rank', '')
        rp = player_info.get('rankPoints', 0)
        if rank:
            players_with_rank_info += 1
        
        ranked_matches = [m for m in matches if m.get('playlist') == 'ranked']
        print(f"  Found {len(matches)} matches, ranked: {len(ranked_matches)}")
        
        new_matches = [m for m in ranked_matches if m['match_id'] not in all_known_matches]
        to_fetch = new_matches[:max_matches]
        print(f"  New matches to fetch: {len(to_fetch)}")
        
        for midx, match in enumerate(to_fetch):
            match_id = match['match_id']
            map_name = match.get('map', '?')
            
            print(f"    [{midx+1}/{len(to_fetch)}] {match_id[:12]}... ({map_name})", end=' ', flush=True)
            
            detail = fetch_match_detail(match_id, mapper=mapper)
            
            if detail:
                detail['source_player'] = {
                    'displayName': player_name,
                    'profileId': profile_id,
                    'rank': rank,
                    'rankPoints': rp,
                    'source': 'extra_v2',
                }
                all_details.append(detail)
                all_known_matches.add(match_id)
                shard_completed_matches.add(match_id)
                new_matches_done += 1
                print(f"OK ({detail.get('total_players',0)}p, {len(detail.get('round_records',[]))}r)")
                
                emit_extra_event(shard_id, 'match_found', {
                    'match_id': match_id,
                    'map': map_name,
                    'source_player': player_name,
                })
            else:
                print(f"FAIL")
            
            time.sleep(delay + random.uniform(0.3, 1.0))
        
        shard_completed.add(profile_id)
        new_players_done += 1
        
        emit_extra_event(shard_id, 'player_done', {
            'player': player_name,
            'new_matches': len(to_fetch),
            'has_rank': bool(rank),
        })
        
        if (idx + 1) % batch_size == 0 or idx == len(shard_players) - 1:
            _save_progress(shard_id, shard_completed, shard_completed_matches)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(all_details, f, ensure_ascii=False)
            print(f"  [SAVE] ExShard {shard_id}: {len(shard_completed)} players, {len(all_details)} matches")
        
        time.sleep(delay + random.uniform(0.3, 1.0))
    
    _save_progress(shard_id, shard_completed, shard_completed_matches)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    mapper.save()
    
    emit_extra_event(shard_id, 'shard_done', {
        'players_done': new_players_done,
        'matches_done': new_matches_done,
        'total_matches': len(all_details),
        'players_with_rank': players_with_rank_info,
        'session_reviews': health.review_count,
        'session_rebuilds': health.total_session_rebuilds,
    })
    
    print(f"\n{'=' * 70}")
    print(f"Extra Shard {shard_id} 完成! (v2)")
    print(f"{'=' * 70}")
    print(f"玩家处理: {new_players_done}, 有段位: {players_with_rank_info}")
    print(f"新比赛: {new_matches_done}, 总比赛: {len(all_details)}")
    print(f"Session 审查: {health.review_count}, 重建: {health.total_session_rebuilds}")


def _save_progress(shard_id, completed_players, completed_matches):
    progress = {
        'shard_id': shard_id,
        'completed_players': list(completed_players),
        'completed_matches': list(completed_matches),
        'last_updated': datetime.now().isoformat(),
        'version': 'v2',
        'stats': {
            'total_players_done': len(completed_players),
            'total_matches_done': len(completed_matches),
        }
    }
    # 原子写入: 先写临时文件再 rename，避免监控端读到半写文件导致进度跳变
    target = shard_progress_file(shard_id)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    os.replace(tmp, target)  # 原子替换


# ===== Status =====
def cmd_status(args):
    total_shards = args.total_shards
    
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print("[ERROR] Extra players file not found.")
        return
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        total_extra = len(json.load(f))
    
    print("=" * 70)
    print("额外玩家采集进度 (v2)")
    print("=" * 70)
    print(f"总额外玩家: {total_extra}")
    
    total_done = 0
    total_matches = 0
    
    for shard_id in range(total_shards):
        pfile = shard_progress_file(shard_id)
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            p_done = len(sp.get('completed_players', []))
            m_done = len(sp.get('completed_matches', []))
            last = sp.get('last_updated', 'N/A')
            version = sp.get('version', 'v1')
            total_done += p_done
            total_matches += m_done
            
            df = shard_data_file(shard_id)
            size = os.path.getsize(df) / 1024 / 1024 if os.path.exists(df) else 0
            print(f"  ExShard {shard_id}: {p_done} players, {m_done} matches, {size:.1f}MB ({version}) [{last}]")
        else:
            print(f"  ExShard {shard_id}: Not started")
    
    print(f"\n  TOTAL: {total_done}/{total_extra} ({total_done/max(total_extra,1)*100:.1f}%), {total_matches} matches")


# ===== Merge =====
def cmd_merge(args):
    total_shards = args.total_shards
    
    print("=" * 70)
    print("合并额外玩家比赛数据 (v2)")
    print("=" * 70)
    
    all_details = []
    seen_match_ids = set()
    all_completed = set()
    
    for shard_id in range(total_shards):
        df = shard_data_file(shard_id)
        pf = shard_progress_file(shard_id)
        
        if os.path.exists(df):
            with open(df, 'r', encoding='utf-8') as f:
                data = json.load(f)
            new = 0
            for d in data:
                mid = d.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_details.append(d)
                    seen_match_ids.add(mid)
                    new += 1
            print(f"  ExShard {shard_id}: {len(data)} matches ({new} new)")
        
        if os.path.exists(pf):
            with open(pf, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            all_completed.update(sp.get('completed_players', []))
    
    out_file = os.path.join(OUTPUT_DIR, 'all_extra_match_details.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    print(f"\n总计: {len(all_details)} unique matches, {len(all_completed)} players done")
    print(f"保存到: {out_file}")


# ===== Main =====
def main():
    parser = argparse.ArgumentParser(description='额外玩家数据采集 v2')
    subparsers = parser.add_subparsers(dest='command')
    
    subparsers.add_parser('extract', help='提取额外玩家')
    
    plan_p = subparsers.add_parser('plan', help='分片规划')
    plan_p.add_argument('--shards', type=int, default=8)
    
    run_p = subparsers.add_parser('run', help='运行分片')
    run_p.add_argument('--shard-id', type=int, required=True)
    run_p.add_argument('--total-shards', type=int, required=True)
    run_p.add_argument('--max-matches', type=int, default=5)
    run_p.add_argument('--delay', type=float, default=1.0)
    run_p.add_argument('--batch-size', type=int, default=3)
    run_p.add_argument('--health-threshold', type=int, default=5)
    
    status_p = subparsers.add_parser('status', help='查看进度')
    status_p.add_argument('--total-shards', type=int, default=8)
    
    merge_p = subparsers.add_parser('merge', help='合并数据')
    merge_p.add_argument('--total-shards', type=int, default=8)
    
    args = parser.parse_args()
    
    if args.command == 'extract':
        cmd_extract(args)
    elif args.command == 'plan':
        cmd_plan(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'merge':
        cmd_merge(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

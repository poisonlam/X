"""
从已有比赛数据中提取额外玩家，并采集他们的比赛数据
=============================================================
这些玩家出现在已采集的比赛中（作为队友或对手），但不在排行榜中。
他们分布在各个段位，是扩展数据覆盖范围的最佳来源。

两个步骤：
  Step 1: extract — 从所有分片中提取额外玩家列表
  Step 2: run     — 分片采集额外玩家的比赛数据

用法:
  # 提取额外玩家列表
  python extract_and_collect_extra_players.py extract

  # 查看分片规划
  python extract_and_collect_extra_players.py plan --shards 5

  # 运行指定分片
  python extract_and_collect_extra_players.py run --shard-id 0 --total-shards 5 --delay 2.5

  # 查看进度
  python extract_and_collect_extra_players.py status --total-shards 5

  # 合并所有分片
  python extract_and_collect_extra_players.py merge --total-shards 5
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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',  # 不要br! requests不支持brotli解压
}

# ===== 全局 Session（复用 TCP 连接，避免重复 TLS 握手）=====
_session = None

def get_session():
    """获取全局 requests.Session，复用 TCP 连接"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=0
        )
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
    return _session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'extra_match_data')
LB_DIR = os.path.join(BASE_DIR, 'output', 'leaderboard')
MAIN_MATCH_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
EXTRA_PLAYERS_FILE = os.path.join(OUTPUT_DIR, '_extra_players.json')
ANOMALY_PLAYERS_FILE = os.path.join(OUTPUT_DIR, '_anomaly_players.json')  # 数据异常玩家池


def load_anomaly_players():
    """加载数据异常的玩家池"""
    if os.path.exists(ANOMALY_PLAYERS_FILE):
        try:
            with open(ANOMALY_PLAYERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_anomaly_player(player_name, profile_id, reason="HTTP 500 无比赛数据"):
    """将数据异常的玩家记录到异常池"""
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
        print(f"    [ANOMALY] 已记录到异常玩家池: {player_name} ({reason})")


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
    json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not json_blocks:
        return None
    return json.loads(json_blocks[0])


# ===== 健康检查 =====
def check_server_health():
    """用一个独立请求检测 stats.cc 是否可用（不依赖当前失败的玩家）"""
    session = get_session()
    try:
        r = session.get('https://stats.cc/siege/matches/3f4a671e-7fe1-4f35-a7e4-d99522109330', timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ===== 数据获取函数 =====
def fetch_player_matches(player_name, profile_id, retries=4):
    """从 stats.cc 玩家页面获取比赛历史（Session复用 + 智能重试）
    
    关键改进：500 响应也尝试解析数据（stats.cc 有时返回 500 但包含有效数据）
    返回值：dict{'matches':[], 'player_info':{}} 成功 | [] 无数据但已处理 | None 真正失败
    """
    session = get_session()
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
                print(f"    [!] 404 Not Found - skipping")
                return None
            
            # 关键改进: 即使 500 也尝试解析数据
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
                    
                    if matches:
                        if r.status_code == 500:
                            print(f"    [*] HTTP 500 但解析到 {len(matches)} 个比赛（数据可用）")
                        return {'matches': matches, 'player_info': player_info}
                    elif r.status_code == 500:
                        # 500 且无数据 → 该玩家数据源有问题
                        print(f"    [!] HTTP 500 无比赛数据 - 该玩家数据源异常，跳过")
                        return []  # 空列表表示"已处理但无数据"
                    elif r.status_code == 200:
                        return {'matches': [], 'player_info': player_info}
            
            if r.status_code != 200:
                print(f"    [!] HTTP {r.status_code} (attempt {attempt+1})")
                if r.status_code >= 500 and attempt < retries - 1:
                    wait = min(10 * (2 ** attempt), 120)
                    print(f"    [!] Server error, waiting {wait}s...")
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


def fetch_match_detail(match_id, retries=4):
    """从 stats.cc 比赛详情页获取完整回合数据（Session复用 + 智能重试）"""
    session = get_session()
    url = f'https://stats.cc/siege/matches/{match_id}'
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=(10, 25))
            if r.status_code == 429:
                wait = min(5 * (2 ** attempt), 60)
                print(f"      [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                print(f"      [!] HTTP {r.status_code} (attempt {attempt+1})")
                if r.status_code >= 500 and attempt < retries - 1:
                    wait = min(10 * (2 ** attempt), 120)
                    print(f"      [!] Server error, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return None
            nuxt = parse_nuxt_page(r.text)
            if not nuxt:
                return None
            
            match_meta = None
            for i in range(len(nuxt)):
                item = nuxt[i]
                if isinstance(item, dict) and 'map' in item and 'scores' in item and 'playlist' in item:
                    match_meta = deref(nuxt, i, max_depth=15)
                    break
            
            round_data = []
            for i in range(len(nuxt)):
                item = nuxt[i]
                if isinstance(item, dict) and 'operator' in item and 'outcome' in item and 'profile_id' in item:
                    resolved = deref(nuxt, i, max_depth=12)
                    if resolved:
                        round_data.append(resolved)
            
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
        except requests.exceptions.ConnectionError as e:
            print(f"      [!] Connection error: {e}")
            if attempt < retries - 1:
                time.sleep(3)
        except requests.exceptions.Timeout:
            print(f"      [!] Timeout (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(2)
        except Exception as e:
            print(f"      [!] Error: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


# ===== Step 1: Extract extra players from existing match data =====
def cmd_extract(args):
    """从已采集的比赛数据中提取所有不在排行榜中的额外玩家"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载所有排行榜玩家 ID
    known_lb_ids = set()
    lb_files = [
        os.path.join(LB_DIR, 'leaderboard_full.json'),        # PC
        os.path.join(LB_DIR, 'leaderboard_console.json'),      # Console
        os.path.join(LB_DIR, 'leaderboard_global.json'),       # Global
    ]
    for f in lb_files:
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            ids = set(p['profileId'] for p in data if p.get('profileId'))
            known_lb_ids.update(ids)
            print(f"Loaded {len(ids)} players from {os.path.basename(f)}")
    
    print(f"Total known leaderboard players: {len(known_lb_ids)}")
    
    # 从所有比赛分片中提取玩家
    extra_players = {}  # profile_id -> {username, appearances, ...}
    
    # 加载主排行榜采集的比赛数据
    for shard_id in range(20):  # 检查最多20个分片
        shard_dir = os.path.join(MAIN_MATCH_DIR, f'shard_{shard_id}')
        match_file = os.path.join(shard_dir, 'match_details.json')
        if not os.path.exists(match_file):
            continue
        
        print(f"Processing shard_{shard_id}...", end=' ', flush=True)
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
                    # 更新用户名（可能之前是空的）
                    if uname and not extra_players[pid]['displayName']:
                        extra_players[pid]['displayName'] = uname
                    count += 1
        
        print(f"{len(matches)} matches, found {count} extra player appearances")
    
    # 也检查额外采集的比赛数据
    for shard_id in range(20):
        shard_dir = os.path.join(OUTPUT_DIR, f'shard_{shard_id}')
        match_file = os.path.join(shard_dir, 'match_details.json')
        if not os.path.exists(match_file):
            continue
        
        print(f"Processing extra shard_{shard_id}...", end=' ', flush=True)
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
        
        print(f"{len(matches)} matches, found {count} extra player appearances")
    
    # 按出现次数排序（出现多的优先采集——他们更活跃，更可能有段位数据）
    player_list = sorted(extra_players.values(), key=lambda x: -x['appearances'])
    
    # 过滤掉没有用户名的（无法访问其页面）
    player_list = [p for p in player_list if p.get('displayName')]
    
    with open(EXTRA_PLAYERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(player_list, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"提取完成!")
    print(f"{'=' * 70}")
    print(f"额外玩家总数: {len(player_list)}")
    print(f"  有用户名的: {len([p for p in player_list if p['displayName']])}")
    print(f"  出现 >= 5 次: {len([p for p in player_list if p['appearances'] >= 5])}")
    print(f"  出现 >= 3 次: {len([p for p in player_list if p['appearances'] >= 3])}")
    print(f"  出现 >= 2 次: {len([p for p in player_list if p['appearances'] >= 2])}")
    print(f"  出现 == 1 次: {len([p for p in player_list if p['appearances'] == 1])}")
    print(f"\n保存到: {EXTRA_PLAYERS_FILE}")


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
    
    # 从主排行榜分片
    for shard_id in range(20):
        pfile = os.path.join(MAIN_MATCH_DIR, f'_shard_{shard_id}_progress.json')
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            known.update(sp.get('completed_matches', []))
    
    # 从全局进度
    gp_file = os.path.join(MAIN_MATCH_DIR, '_progress.json')
    if os.path.exists(gp_file):
        with open(gp_file, 'r', encoding='utf-8') as f:
            gp = json.load(f)
        known.update(gp.get('completed_matches', []))
    
    # 从额外分片
    for shard_id in range(20):
        pfile = shard_progress_file(shard_id)
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            known.update(sp.get('completed_matches', []))
    
    return known


# ===== Plan =====
def cmd_plan(args):
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print("[ERROR] Extra players file not found. Run 'extract' first.")
        return
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    # 加载已完成的额外玩家
    done = set()
    for shard_id in range(args.shards):
        pfile = shard_progress_file(shard_id)
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            done.update(sp.get('completed_players', []))
    
    remaining = [p for p in players if p['profileId'] not in done]
    
    print("=" * 70)
    print("额外玩家采集 - 分片规划")
    print("=" * 70)
    print(f"额外玩家总数: {len(players)}")
    print(f"已完成: {len(done)}")
    print(f"剩余: {len(remaining)}")
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
    
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print("[ERROR] Extra players file not found. Run 'extract' first.")
        return
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        all_extra_players = json.load(f)
    
    # 加载分片进度
    progress_file = shard_progress_file(shard_id)
    shard_completed = set()
    shard_completed_matches = set()
    
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            sp = json.load(f)
            shard_completed = set(sp.get('completed_players', []))
            shard_completed_matches = set(sp.get('completed_matches', []))
    
    # 获取剩余玩家
    remaining = [p for p in all_extra_players if p['profileId'] not in shard_completed]
    
    # 分片
    shard_players = [p for i, p in enumerate(remaining) if i % total_shards == shard_id]
    
    # 加载已有比赛数据
    data_file = shard_data_file(shard_id)
    all_details = []
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            all_details = json.load(f)
        for d in all_details:
            shard_completed_matches.add(d['match_id'])
    
    # 加载全局已知 match IDs
    all_known_matches = load_all_known_match_ids()
    all_known_matches.update(shard_completed_matches)
    
    print("=" * 70)
    print(f"Extra Players Shard {shard_id}/{total_shards-1} - R6 Siege 额外玩家比赛采集")
    print("=" * 70)
    print(f"总额外玩家: {len(all_extra_players)}")
    print(f"本分片待处理: {len(shard_players)}")
    print(f"已完成: {len(shard_completed)}")
    print(f"已有比赛数据: {len(all_details)}")
    print(f"全局已知match IDs: {len(all_known_matches)}")
    print(f"每人对局上限: {max_matches}")
    print(f"请求间隔: {delay}s")
    print()
    
    new_players_done = 0
    new_matches_done = 0
    players_with_rank_info = 0
    consecutive_server_errors = 0  # 连续服务器错误计数
    skipped_for_retry = []  # 因服务器错误跳过的玩家（不标记已完成）
    
    for idx, player in enumerate(shard_players):
        player_name = player['displayName']
        profile_id = player['profileId']
        appearances = player.get('appearances', 0)
        
        print(f"[ExS{shard_id}][{idx+1}/{len(shard_players)}] {player_name} (seen {appearances}x)")
        
        # 获取比赛历史 + 玩家信息
        result = fetch_player_matches(player_name, profile_id)
        
        if result is None:
            # 真正的网络/服务器故障
            consecutive_server_errors += 1
            print(f"  [FAIL] Cannot get data (consecutive fails: {consecutive_server_errors})")
            
            if consecutive_server_errors >= 10:
                pause_time = min(60, consecutive_server_errors * 10)  # 最多60秒
                print(f"  [!] {consecutive_server_errors} consecutive failures! Checking server health in {pause_time}s...")
                
                _save_progress(shard_id, shard_completed, shard_completed_matches)
                if all_details:
                    with open(data_file, 'w', encoding='utf-8') as f:
                        json.dump(all_details, f, ensure_ascii=False)
                
                time.sleep(pause_time)
                
                # 关键修复：用独立的健康检查
                if check_server_health():
                    print(f"  [OK] Server is healthy! Current player may have data issues. Marking as done and moving on...")
                    consecutive_server_errors = 0
                    save_anomaly_player(player_name, profile_id, "连续失败但服务器正常，玩家数据异常")
                    shard_completed.add(profile_id)
                else:
                    print(f"  [!] Server is truly down, skipping (NOT marking as done)")
                    skipped_for_retry.append(profile_id)
                    time.sleep(delay)
                    continue
            else:
                shard_completed.add(profile_id)
                time.sleep(delay)
                continue
        elif isinstance(result, list) and len(result) == 0:
            # 500无数据或无比赛记录 → 正常跳过，记录到异常池
            print(f"  [SKIP] 无比赛数据（玩家数据源异常或无记录）")
            save_anomaly_player(player_name, profile_id)
            shard_completed.add(profile_id)
            consecutive_server_errors = 0
            time.sleep(delay)
            continue
        else:
            consecutive_server_errors = 0
        
        # 万能保护：如果result不是dict，绝不继续（防止崩溃）
        if not isinstance(result, dict):
            print(f"  [GUARD] result类型异常({type(result).__name__})，跳过")
            save_anomaly_player(player_name, profile_id, f"result异常: type={type(result).__name__}")
            shard_completed.add(profile_id)
            time.sleep(delay)
            continue
        
        matches = result.get('matches', [])
        player_info = result.get('player_info', {})
        
        # 记录段位信息
        rank = player_info.get('rank', '')
        rp = player_info.get('rankPoints', 0)
        if rank:
            players_with_rank_info += 1
            print(f"  Rank: {rank}, RP: {rp}")
        
        ranked_matches = [m for m in matches if m.get('playlist') == 'ranked']
        print(f"  Found {len(matches)} matches, ranked: {len(ranked_matches)}")
        
        # 过滤已知
        new_matches = [m for m in ranked_matches if m['match_id'] not in all_known_matches]
        to_fetch = new_matches[:max_matches]
        
        print(f"  New matches to fetch: {len(to_fetch)}")
        
        for midx, match in enumerate(to_fetch):
            match_id = match['match_id']
            map_name = match.get('map', '?')
            
            print(f"    [{midx+1}/{len(to_fetch)}] {match_id[:12]}... ({map_name})", end=' ', flush=True)
            
            detail = fetch_match_detail(match_id)
            
            if detail:
                detail['source_player'] = {
                    'displayName': player_name,
                    'profileId': profile_id,
                    'rank': rank,
                    'rankPoints': rp,
                    'source': 'extra_from_matches',
                }
                all_details.append(detail)
                all_known_matches.add(match_id)
                shard_completed_matches.add(match_id)
                new_matches_done += 1
                print(f"OK ({detail.get('total_players',0)}p, {len(detail.get('round_records',[]))}r)")
            else:
                print(f"FAIL")
            
            time.sleep(delay + random.uniform(0.3, 1.5))
        
        shard_completed.add(profile_id)
        new_players_done += 1
        
        # 保存
        if (idx + 1) % batch_size == 0 or idx == len(shard_players) - 1:
            _save_progress(shard_id, shard_completed, shard_completed_matches)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(all_details, f, ensure_ascii=False)
            print(f"  [SAVE] ExShard {shard_id}: {len(shard_completed)} players, {len(all_details)} matches, {players_with_rank_info} with rank")
        
        time.sleep(delay + random.uniform(0.5, 2.0))
    
    _save_progress(shard_id, shard_completed, shard_completed_matches)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"Extra Shard {shard_id} 完成!")
    print(f"{'=' * 70}")
    print(f"玩家处理: {new_players_done}")
    print(f"有段位信息: {players_with_rank_info}")
    print(f"新比赛详情: {new_matches_done}")
    print(f"总比赛详情: {len(all_details)}")
    if skipped_for_retry:
        print(f"因服务器错误跳过(待重试): {len(skipped_for_retry)}")


def _save_progress(shard_id, completed_players, completed_matches):
    progress = {
        'shard_id': shard_id,
        'completed_players': list(completed_players),
        'completed_matches': list(completed_matches),
        'last_updated': datetime.now().isoformat(),
        'stats': {
            'total_players_done': len(completed_players),
            'total_matches_done': len(completed_matches),
        }
    }
    with open(shard_progress_file(shard_id), 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ===== Status =====
def cmd_status(args):
    total_shards = args.total_shards
    
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print("[ERROR] Extra players file not found. Run 'extract' first.")
        return
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        total_extra = len(json.load(f))
    
    print("=" * 70)
    print("额外玩家采集进度")
    print("=" * 70)
    print(f"总额外玩家: {total_extra}")
    print()
    
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
            total_done += p_done
            total_matches += m_done
            
            # 检查数据文件大小
            df = shard_data_file(shard_id)
            size = os.path.getsize(df) / 1024 / 1024 if os.path.exists(df) else 0
            print(f"  ExShard {shard_id}: {p_done} players, {m_done} matches, {size:.1f}MB, updated: {last}")
        else:
            print(f"  ExShard {shard_id}: Not started")
    
    print(f"\n  TOTAL: {total_done}/{total_extra} players ({total_done/max(total_extra,1)*100:.1f}%), {total_matches} matches")


# ===== Merge =====
def cmd_merge(args):
    total_shards = args.total_shards
    
    print("=" * 70)
    print("合并额外玩家比赛数据")
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
    parser = argparse.ArgumentParser(description='提取并采集额外玩家数据')
    subparsers = parser.add_subparsers(dest='command')
    
    # extract
    subparsers.add_parser('extract', help='从比赛数据中提取额外玩家列表')
    
    # plan
    plan_p = subparsers.add_parser('plan', help='查看分片规划')
    plan_p.add_argument('--shards', type=int, default=5)
    
    # run
    run_p = subparsers.add_parser('run', help='运行指定分片')
    run_p.add_argument('--shard-id', type=int, required=True)
    run_p.add_argument('--total-shards', type=int, required=True)
    run_p.add_argument('--max-matches', type=int, default=5, help='每人最多采集几场（额外玩家建议少一些以覆盖更多人）')
    run_p.add_argument('--delay', type=float, default=1.0)
    run_p.add_argument('--batch-size', type=int, default=3)
    
    # status
    status_p = subparsers.add_parser('status', help='查看进度')
    status_p.add_argument('--total-shards', type=int, default=5)
    
    # merge
    merge_p = subparsers.add_parser('merge', help='合并数据')
    merge_p.add_argument('--total-shards', type=int, default=5)
    
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

"""
R6 Siege 玩家对局数据 - 分片并行采集脚本
=========================================
支持将玩家列表分片，每个进程/agent 独立处理自己的分片，
最后通过 merge 命令合并所有分片的结果。

用法:
  # 查看分片规划
  python parallel_collect.py plan --shards 5

  # 运行指定分片 (0-indexed)
  python parallel_collect.py run --shard-id 0 --total-shards 5 --delay 2.5
  python parallel_collect.py run --shard-id 1 --total-shards 5 --delay 2.5
  ...

  # 合并所有分片结果
  python parallel_collect.py merge --total-shards 5

  # 查看进度
  python parallel_collect.py status --total-shards 5
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
        # 设置连接池大小
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=0  # 我们自己控制重试逻辑
        )
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
    return _session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
LEADERBOARD_FILE = os.path.join(BASE_DIR, 'output', 'leaderboard', 'leaderboard_full.json')
GLOBAL_PROGRESS_FILE = os.path.join(OUTPUT_DIR, '_progress.json')
SHARED_MATCH_IDS_FILE = os.path.join(OUTPUT_DIR, '_shared_match_ids.json')  # 跨分片去重共享文件
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
    # 避免重复
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


def load_shared_match_ids():
    """加载跨分片共享的已采集 match IDs"""
    if os.path.exists(SHARED_MATCH_IDS_FILE):
        try:
            with open(SHARED_MATCH_IDS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    return set()


def save_shared_match_ids(match_ids):
    """保存跨分片共享的已采集 match IDs（原子写入）"""
    # 先合并已有的（其他分片可能已经写入了新的）
    existing = load_shared_match_ids()
    merged = existing | match_ids
    tmp_file = SHARED_MATCH_IDS_FILE + '.tmp'
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(list(merged), f)
        os.replace(tmp_file, SHARED_MATCH_IDS_FILE)  # 原子替换
    except Exception as e:
        print(f"  [WARN] Failed to save shared match IDs: {e}")


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


# ===== 健康检查用的已知可用玩家 =====
_HEALTH_CHECK_PLAYER = ('Slypt-_-', '621b2e6e-0000-0000-0000-000000000000')  # 仅用于服务器健康检测

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
    """
    session = get_session()
    url = f'https://stats.cc/siege/{player_name}/{profile_id}'
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=(10, 25))  # (连接超时, 读取超时)
            if r.status_code == 429:
                wait = min(5 * (2 ** attempt), 60)  # 指数退避: 5, 10, 20, 40s
                print(f"    [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 404:
                # 玩家不存在，跳过不重试
                print(f"    [!] 404 Not Found - skipping")
                return None
            
            # 关键改进: 即使 500 也尝试解析（stats.cc 某些玩家页面返回 500 但有数据）
            if r.status_code == 500 or r.status_code == 200:
                nuxt = parse_nuxt_page(r.text)
                if nuxt:
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
                        return matches
                    elif r.status_code == 500:
                        # 500 且无数据 → 该玩家数据源有问题，不重试（避免死循环）
                        print(f"    [!] HTTP 500 无比赛数据 - 该玩家数据源异常，跳过")
                        return []  # 返回空列表而非None，表示"已处理但无数据"
                    elif r.status_code == 200:
                        return []  # 200 但没有比赛数据
            
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
            
            # 200 但没有 nuxt 数据
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
                wait = min(5 * (2 ** attempt), 60)  # 指数退避: 5, 10, 20, 40s
                print(f"      [!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 404:
                # Match不存在/已删除，跳过不重试
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


# ===== 分片逻辑 =====
def get_remaining_players():
    """获取尚未处理的玩家列表"""
    with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
        all_players = json.load(f)
    
    # 加载全局已完成列表
    completed = set()
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        with open(GLOBAL_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            completed = set(progress.get('completed_players', []))
    
    # 也检查各分片的进度
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith('_shard_') and fname.endswith('_progress.json'):
            fpath = os.path.join(OUTPUT_DIR, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                shard_progress = json.load(f)
                completed.update(shard_progress.get('completed_players', []))
    
    remaining = [p for p in all_players if p['profileId'] not in completed]
    return remaining, completed


def get_shard_players(shard_id, total_shards):
    """获取指定分片的玩家列表"""
    remaining, completed = get_remaining_players()
    
    # 均匀分片
    shard_players = []
    for i, p in enumerate(remaining):
        if i % total_shards == shard_id:
            shard_players.append(p)
    
    return shard_players, completed


def shard_output_dir(shard_id):
    return os.path.join(OUTPUT_DIR, f'shard_{shard_id}')


def shard_progress_file(shard_id):
    return os.path.join(OUTPUT_DIR, f'_shard_{shard_id}_progress.json')


def shard_data_file(shard_id):
    return os.path.join(shard_output_dir(shard_id), 'match_details.json')


# ===== 命令: plan =====
def cmd_plan(args):
    remaining, completed = get_remaining_players()
    total = len(remaining)
    
    print("=" * 70)
    print("分片规划")
    print("=" * 70)
    print(f"已完成玩家: {len(completed)}")
    print(f"剩余玩家: {total}")
    print(f"分片数: {args.shards}")
    print()
    
    for shard_id in range(args.shards):
        count = len([i for i in range(total) if i % args.shards == shard_id])
        print(f"  Shard {shard_id}: {count} 玩家")
    
    print()
    print("运行命令:")
    for shard_id in range(args.shards):
        print(f"  python parallel_collect.py run --shard-id {shard_id} --total-shards {args.shards} --delay 2.5 --max-matches 10")
    
    print(f"\n合并命令:")
    print(f"  python parallel_collect.py merge --total-shards {args.shards}")


# ===== 命令: run =====
def cmd_run(args):
    shard_id = args.shard_id
    total_shards = args.total_shards
    max_matches = args.max_matches
    delay = args.delay
    batch_size = args.batch_size  # 每批处理多少个玩家后保存
    
    os.makedirs(shard_output_dir(shard_id), exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 加载分片进度
    progress_file = shard_progress_file(shard_id)
    shard_completed = set()
    shard_completed_matches = set()
    
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            sp = json.load(f)
            shard_completed = set(sp.get('completed_players', []))
            shard_completed_matches = set(sp.get('completed_matches', []))
    
    # 获取分片玩家
    shard_players, global_completed = get_shard_players(shard_id, total_shards)
    
    # 排除本分片已完成的
    todo_players = [p for p in shard_players if p['profileId'] not in shard_completed]
    
    # 加载已有比赛数据
    data_file = shard_data_file(shard_id)
    all_details = []
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            all_details = json.load(f)
        # 更新已完成match set
        for d in all_details:
            shard_completed_matches.add(d['match_id'])
    
    # 也加载全局已完成的 matches (避免重复采集)
    global_match_ids = set()
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        with open(GLOBAL_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            gp = json.load(f)
            global_match_ids = set(gp.get('completed_matches', []))
    
    # 方案B: 加载跨分片共享的已采集 match IDs
    shared_match_ids = load_shared_match_ids()
    
    all_known_matches = shard_completed_matches | global_match_ids | shared_match_ids
    
    print("=" * 70)
    print(f"Shard {shard_id}/{total_shards-1} - R6 Siege 对局数据采集 (优化版)")
    print("=" * 70)
    print(f"分片玩家总数: {len(shard_players)}")
    print(f"已完成: {len(shard_completed)}")
    print(f"待处理: {len(todo_players)}")
    print(f"已有比赛数据: {len(all_details)}")
    print(f"已知match IDs: {len(all_known_matches)} (含共享: {len(shared_match_ids)})")
    print(f"每人对局上限: {max_matches}")
    print(f"请求间隔: {delay}s")
    print(f"批次大小: {batch_size}")
    print(f"优化: Session复用 + 指数退避 + 404跳过 + gzip + 跨分片去重")
    print()
    
    new_players_done = 0
    new_matches_done = 0
    consecutive_429 = 0
    consecutive_server_errors = 0  # 连续服务器错误计数
    
    for idx, player in enumerate(todo_players):
        player_name = player['displayName']
        profile_id = player['profileId']
        rank = player.get('rank', 'unknown')
        rp = player.get('rankPoints', 0)
        pos = player.get('leaderboardPosition', '?')
        
        print(f"[S{shard_id}][{idx+1}/{len(todo_players)}] {player_name} (#{pos}, {rank}, RP:{rp})")
        
        # Step 1: 获取比赛历史
        matches = fetch_player_matches(player_name, profile_id)
        
        if matches is None:
            # 真正的网络/服务器故障（非玩家数据问题）
            consecutive_server_errors += 1
            print(f"  [FAIL] Cannot get match history (consecutive fails: {consecutive_server_errors})")
            
            # 如果连续失败超过10次，检查服务器健康状态
            if consecutive_server_errors >= 10:
                pause_time = min(60, consecutive_server_errors * 10)  # 最多暂停60秒（大幅缩短）
                print(f"  [!] {consecutive_server_errors} consecutive failures! Checking server health in {pause_time}s...")
                
                # 先保存已有进度
                _save_shard_progress(shard_id, shard_completed, shard_completed_matches)
                save_shared_match_ids(shard_completed_matches)
                if all_details:
                    with open(data_file, 'w', encoding='utf-8') as f:
                        json.dump(all_details, f, ensure_ascii=False)
                
                time.sleep(pause_time)
                
                # 关键修复：用独立的健康检查，不用当前失败的玩家！
                if check_server_health():
                    print(f"  [OK] Server is healthy! Current player may have data issues. Marking as done and moving on...")
                    consecutive_server_errors = 0
                    save_anomaly_player(player_name, profile_id, "连续失败但服务器正常，玩家数据异常")
                    shard_completed.add(profile_id)  # 服务器正常但该玩家失败→标记已处理
                else:
                    # 服务器真的挂了，不标记为完成
                    print(f"  [!] Server is truly down, skipping (NOT marking as done)")
                    time.sleep(delay)
                    continue
            else:
                # 少量连续失败：标记为已完成（可能是该玩家本身的问题）
                shard_completed.add(profile_id)
                time.sleep(delay)
                continue
        elif matches is None:
            # matches返回None（可能是未预期的异常），记录到异常池并跳过
            print(f"  [SKIP] matches返回None，记录到异常池")
            save_anomaly_player(player_name, profile_id, "fetch_matches返回None")
            shard_completed.add(profile_id)
            consecutive_server_errors = 0
            time.sleep(delay)
            continue
        elif isinstance(matches, list) and len(matches) == 0:
            # 玩家数据源异常（500无数据）或没有比赛记录 → 正常跳过，记录到异常池
            print(f"  [SKIP] 无比赛数据（玩家数据源异常或无记录）")
            save_anomaly_player(player_name, profile_id)
            shard_completed.add(profile_id)
            consecutive_server_errors = 0  # 请求本身成功了，重置计数器
            time.sleep(delay)
            continue
        else:
            consecutive_server_errors = 0  # 重置连续错误计数
        
        # 万能保护：如果matches不是非空列表，绝不继续（防止崩溃）
        if not isinstance(matches, list) or len(matches) == 0:
            print(f"  [GUARD] matches类型异常({type(matches).__name__})或为空，跳过")
            save_anomaly_player(player_name, profile_id, f"matches异常: type={type(matches).__name__}")
            shard_completed.add(profile_id)
            time.sleep(delay)
            continue
        
        ranked_matches = [m for m in matches if m.get('playlist') == 'ranked']
        print(f"  Found {len(matches)} matches, ranked: {len(ranked_matches)}")
        
        # 过滤已采集的
        new_matches = [m for m in ranked_matches if m['match_id'] not in all_known_matches]
        to_fetch = new_matches[:max_matches]
        
        print(f"  New matches to fetch: {len(to_fetch)}")
        
        # Step 2: 获取比赛详情
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
                }
                all_details.append(detail)
                all_known_matches.add(match_id)
                shard_completed_matches.add(match_id)
                new_matches_done += 1
                consecutive_429 = 0
                
                rounds = len(detail.get('round_records', []))
                players_count = detail.get('total_players', 0)
                print(f"OK ({players_count}p, {rounds}r)")
            else:
                print(f"FAIL")
            
            # 优化后的延迟
            actual_delay = delay + random.uniform(0.1, 0.5)
            time.sleep(actual_delay)
        
        # 标记完成
        shard_completed.add(profile_id)
        new_players_done += 1
        
        # 保存进度（每 batch_size 个玩家或每次都保存）
        if (idx + 1) % batch_size == 0 or idx == len(todo_players) - 1:
            _save_shard_progress(shard_id, shard_completed, shard_completed_matches)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(all_details, f, ensure_ascii=False)
            # 方案B: 同步更新共享 match IDs
            save_shared_match_ids(shard_completed_matches)
            print(f"  [SAVE] Shard {shard_id}: {len(shard_completed)} players, {len(all_details)} matches saved")
            
            # 定期从共享文件刷新（获取其他分片新发现的 match IDs）
            fresh_shared = load_shared_match_ids()
            new_from_others = len(fresh_shared - all_known_matches)
            all_known_matches.update(fresh_shared)
            if new_from_others > 0:
                print(f"  [DEDUP] 从其他分片获得 {new_from_others} 个新 match IDs，当前已知: {len(all_known_matches)}")
        
        # 优化后的延迟：更紧凑的抖动
        time.sleep(delay + random.uniform(0.1, 0.5))
    
    # 最终保存
    _save_shard_progress(shard_id, shard_completed, shard_completed_matches)
    save_shared_match_ids(shard_completed_matches)  # 同步共享 match IDs
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"Shard {shard_id} 完成!")
    print(f"{'=' * 70}")
    print(f"玩家处理: {new_players_done}")
    print(f"新比赛详情: {new_matches_done}")
    print(f"总比赛详情: {len(all_details)}")


def _save_shard_progress(shard_id, completed_players, completed_matches):
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


# ===== 命令: status =====
def cmd_status(args):
    total_shards = args.total_shards
    remaining, completed = get_remaining_players()
    
    print("=" * 70)
    print("采集进度总览")
    print("=" * 70)
    print(f"全局已完成玩家: {len(completed)}")
    print(f"剩余玩家: {len(remaining)}")
    print()
    
    total_shard_players = 0
    total_shard_matches = 0
    
    for shard_id in range(total_shards):
        pfile = shard_progress_file(shard_id)
        if os.path.exists(pfile):
            with open(pfile, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            p_done = len(sp.get('completed_players', []))
            m_done = len(sp.get('completed_matches', []))
            last_update = sp.get('last_updated', 'N/A')
            total_shard_players += p_done
            total_shard_matches += m_done
            print(f"  Shard {shard_id}: {p_done} players, {m_done} matches (updated: {last_update})")
        else:
            print(f"  Shard {shard_id}: Not started")
    
    print(f"\n  Total across shards: {total_shard_players} players, {total_shard_matches} matches")


# ===== 命令: merge =====
def cmd_merge(args):
    total_shards = args.total_shards
    
    print("=" * 70)
    print("合并所有分片数据")
    print("=" * 70)
    
    all_details = []
    all_completed_players = set()
    all_completed_matches = set()
    seen_match_ids = set()
    
    # 先加载全局已有数据
    global_data_file = os.path.join(OUTPUT_DIR, 'all_match_details.json')
    if os.path.exists(global_data_file):
        with open(global_data_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        for d in existing:
            mid = d.get('match_id')
            if mid and mid not in seen_match_ids:
                all_details.append(d)
                seen_match_ids.add(mid)
        print(f"Loaded existing global data: {len(all_details)} matches")
    
    # 加载全局进度
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        with open(GLOBAL_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            gp = json.load(f)
            all_completed_players.update(gp.get('completed_players', []))
            all_completed_matches.update(gp.get('completed_matches', []))
    
    # 合并各分片
    for shard_id in range(total_shards):
        data_file = shard_data_file(shard_id)
        progress_file = shard_progress_file(shard_id)
        
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                shard_data = json.load(f)
            new_count = 0
            for d in shard_data:
                mid = d.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_details.append(d)
                    seen_match_ids.add(mid)
                    new_count += 1
            print(f"  Shard {shard_id}: {len(shard_data)} matches ({new_count} new)")
        
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                sp = json.load(f)
                all_completed_players.update(sp.get('completed_players', []))
                all_completed_matches.update(sp.get('completed_matches', []))
    
    # 保存合并后的数据
    with open(global_data_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    # 更新全局进度
    global_progress = {
        'completed_players': list(all_completed_players),
        'completed_matches': list(all_completed_matches),
        'failed_players': [],
        'failed_matches': [],
        'player_match_map': {},
        'stats': {
            'total_players_processed': len(all_completed_players),
            'total_matches_fetched': 0,
            'total_match_details_fetched': len(all_details),
            'total_round_records': sum(len(d.get('round_records', [])) for d in all_details),
            'merged_at': datetime.now().isoformat(),
        }
    }
    with open(GLOBAL_PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(global_progress, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"合并完成!")
    print(f"{'=' * 70}")
    print(f"总玩家: {len(all_completed_players)}")
    print(f"总比赛详情: {len(all_details)} (去重)")
    print(f"总回合记录: {global_progress['stats']['total_round_records']}")
    print(f"数据文件: {global_data_file} ({os.path.getsize(global_data_file):,} bytes)")


# ===== 主入口 =====
def main():
    parser = argparse.ArgumentParser(description='R6 Siege 分片并行采集')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # plan
    plan_parser = subparsers.add_parser('plan', help='查看分片规划')
    plan_parser.add_argument('--shards', type=int, default=5, help='分片数')
    
    # run
    run_parser = subparsers.add_parser('run', help='运行指定分片')
    run_parser.add_argument('--shard-id', type=int, required=True, help='分片 ID (0-indexed)')
    run_parser.add_argument('--total-shards', type=int, required=True, help='总分片数')
    run_parser.add_argument('--max-matches', type=int, default=10, help='每人最多采集几场比赛详情')
    run_parser.add_argument('--delay', type=float, default=1.0, help='请求间隔秒数（优化后默认1.0s）')
    run_parser.add_argument('--batch-size', type=int, default=3, help='每几个玩家保存一次')
    
    # status
    status_parser = subparsers.add_parser('status', help='查看进度')
    status_parser.add_argument('--total-shards', type=int, default=5, help='总分片数')
    
    # merge
    merge_parser = subparsers.add_parser('merge', help='合并所有分片数据')
    merge_parser.add_argument('--total-shards', type=int, default=5, help='总分片数')
    
    args = parser.parse_args()
    
    if args.command == 'plan':
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

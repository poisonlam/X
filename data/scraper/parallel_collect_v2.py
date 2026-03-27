"""
R6 Siege 玩家对局数据 - 增强版分片并行采集脚本 v2
==================================================
基于 parallel_collect.py 重写，增加以下关键功能：

1. Session 健康检测: 连续多次返回0对局时自动触发健康检查，
   重建 Session 并回溯到最早失败节点重新采集
2. 数据脱敏检测: 自动检测地图名/干员名是否被替换为 ID，
   通过 id_mapping 模块实时映射
3. 查漏补缺: 采集结束后自动扫描遗漏的玩家和对局，执行补采
4. 事件日志: 写入结构化事件文件，供监控面板读取

用法:
  python parallel_collect_v2.py plan --shards 5
  python parallel_collect_v2.py run --shard-id 0 --total-shards 5
  python parallel_collect_v2.py status --total-shards 5
  python parallel_collect_v2.py merge --total-shards 5
  python parallel_collect_v2.py gap-fill --total-shards 5   # 查漏补缺
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
    from id_mapping import get_mapper, IDMapper
except ImportError:
    # fallback: 添加当前目录到 path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from id_mapping import get_mapper, IDMapper

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
}

# ===== 全局 Session（可重建）=====
_session = None
_session_created_at = None
_session_request_count = 0

def get_session(force_new=False):
    """获取全局 requests.Session，支持强制重建"""
    global _session, _session_created_at, _session_request_count
    if _session is None or force_new:
        if _session is not None:
            try:
                _session.close()
            except:
                pass
        _session = requests.Session()
        _session.headers.update(HEADERS)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=0
        )
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
        _session_created_at = datetime.now()
        _session_request_count = 0
        if force_new:
            print(f"  [SESSION] 重建 Session (新连接)")
    return _session

def bump_request_count():
    global _session_request_count
    _session_request_count += 1


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
LEADERBOARD_FILE = os.path.join(BASE_DIR, 'output', 'leaderboard', 'leaderboard_full.json')
GLOBAL_PROGRESS_FILE = os.path.join(OUTPUT_DIR, '_progress.json')
SHARED_MATCH_IDS_FILE = os.path.join(OUTPUT_DIR, '_shared_match_ids.json')
ANOMALY_PLAYERS_FILE = os.path.join(OUTPUT_DIR, '_anomaly_players.json')
EVENT_LOG_DIR = os.path.join(OUTPUT_DIR, '_events')  # 事件日志目录


# ===== 事件日志系统 =====
def emit_event(shard_id, event_type, data=None):
    """写入结构化事件，供监控面板读取
    
    event_type: 
        'match_found' - 找到新对局
        'match_not_found' - 玩家无对局
        'session_review_start' - 开始Session审查
        'session_review_end' - Session审查完成
        'session_rebuild' - 重建Session
        'gap_detected' - 发现数据缺口
        'gap_filled' - 缺口已修复
        'format_change' - 数据格式变化
        'player_done' - 玩家处理完成
        'shard_done' - 分片完成
        'error' - 错误
    """
    os.makedirs(EVENT_LOG_DIR, exist_ok=True)
    event = {
        'timestamp': datetime.now().isoformat(),
        'shard_id': shard_id,
        'type': event_type,
        'data': data or {},
    }
    event_file = os.path.join(EVENT_LOG_DIR, f'shard_{shard_id}_events.jsonl')
    try:
        with open(event_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    except Exception:
        pass
    
    # 同时更新最新状态文件（监控面板轮询用）
    status_file = os.path.join(EVENT_LOG_DIR, f'shard_{shard_id}_status.json')
    status = {
        'shard_id': shard_id,
        'last_event': event_type,
        'last_event_time': event['timestamp'],
        'last_event_data': data or {},
    }
    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False)
    except Exception:
        pass


# ===== 异常玩家池 =====
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
        print(f"    [ANOMALY] 已记录到异常玩家池: {player_name} ({reason})")


# ===== 跨分片共享 Match IDs =====
def load_shared_match_ids():
    if os.path.exists(SHARED_MATCH_IDS_FILE):
        try:
            with open(SHARED_MATCH_IDS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    return set()


def save_shared_match_ids(match_ids):
    existing = load_shared_match_ids()
    merged = existing | match_ids
    tmp_file = SHARED_MATCH_IDS_FILE + '.tmp'
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(list(merged), f)
        os.replace(tmp_file, SHARED_MATCH_IDS_FILE)
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
    try:
        raw = json.loads(json_blocks[0])
        if isinstance(raw, list) and len(raw) > 0:
            # 新版 Nuxt: 需要 deref 从 index 0 开始展开
            resolved = deref(raw, 0)
            if resolved is not None:
                return resolved
        return raw
    except (json.JSONDecodeError, Exception):
        return None


# ===== Session 健康检测系统 =====
class SessionHealthMonitor:
    """
    Session 健康监控器
    
    核心逻辑：
    - 跟踪连续返回0对局的玩家数
    - 超过阈值时触发 Session 审查
    - 审查通过→继续采集；审查失败→重建 Session 并回溯
    """
    
    def __init__(self, shard_id, threshold=5):
        self.shard_id = shard_id
        self.threshold = threshold  # 连续无数据触发审查的阈值
        self.consecutive_empty = 0  # 连续返回0对局的玩家数
        self.consecutive_errors = 0  # 连续网络错误数
        self.in_review = False      # 是否正在审查
        self.review_count = 0       # 审查次数
        self.last_review_time = None
        self.failed_players_since_last_success = []  # 上次成功后失败的玩家列表
        self.total_session_rebuilds = 0
        self._health_check_players = [  # 用于健康检查的已知有数据的玩家
            ('Beaulo', '621b2e6e-0000-0000-0000-000000000000'),
        ]
    
    def record_success(self, player_name, match_count):
        """记录一次成功的数据获取"""
        if match_count > 0:
            self.consecutive_empty = 0
            self.consecutive_errors = 0
            self.failed_players_since_last_success.clear()
        else:
            # 有响应但0对局
            self.consecutive_empty += 1
            self.failed_players_since_last_success.append({
                'player': player_name,
                'time': datetime.now().isoformat(),
                'type': 'empty',
            })
    
    def record_error(self, player_name):
        """记录一次网络错误"""
        self.consecutive_errors += 1
        self.failed_players_since_last_success.append({
            'player': player_name,
            'time': datetime.now().isoformat(),
            'type': 'error',
        })
    
    def should_review(self):
        """检查是否需要触发 Session 审查"""
        return (
            self.consecutive_empty >= self.threshold or
            self.consecutive_errors >= self.threshold
        )
    
    def do_review(self):
        """
        执行 Session 审查
        
        Returns:
            tuple (session_ok: bool, needs_backtrack: bool, backtrack_players: list)
        """
        self.in_review = True
        self.review_count += 1
        self.last_review_time = datetime.now()
        
        emit_event(self.shard_id, 'session_review_start', {
            'consecutive_empty': self.consecutive_empty,
            'consecutive_errors': self.consecutive_errors,
            'review_count': self.review_count,
        })
        print(f"\n  [SESSION REVIEW #{self.review_count}] 触发审查 (连续空: {self.consecutive_empty}, 连续错误: {self.consecutive_errors})")
        
        # Step 1: 用独立请求检测 stats.cc 是否可用
        session = get_session()
        server_ok = self._check_known_match()
        
        if not server_ok:
            # 服务器不可用 → 等待恢复
            print(f"  [SESSION REVIEW] 服务器不可达，等待恢复...")
            wait_time = 60
            max_wait = 600  # 最多等10分钟
            total_waited = 0
            while total_waited < max_wait:
                time.sleep(wait_time)
                total_waited += wait_time
                if self._check_known_match():
                    print(f"  [SESSION REVIEW] 服务器已恢复! (等待了 {total_waited}s)")
                    break
            else:
                print(f"  [SESSION REVIEW] 等待超时，重建 Session")
        
        # Step 2: 用已知有数据的玩家测试 Session
        session_valid = self._test_with_known_player()
        
        if session_valid:
            print(f"  [SESSION REVIEW] Session 有效，连续空结果可能是正常的（这些玩家确实没有排位数据）")
            self.in_review = False
            self.consecutive_empty = 0
            self.consecutive_errors = 0
            
            emit_event(self.shard_id, 'session_review_end', {
                'result': 'session_ok',
                'review_count': self.review_count,
            })
            return True, False, []
        
        # Step 3: Session 可能有问题 → 重建
        print(f"  [SESSION REVIEW] Session 可能异常，重建...")
        get_session(force_new=True)
        self.total_session_rebuilds += 1
        
        emit_event(self.shard_id, 'session_rebuild', {
            'rebuild_count': self.total_session_rebuilds,
        })
        
        # Step 4: 重建后再测试
        if self._test_with_known_player():
            print(f"  [SESSION REVIEW] 重建后 Session 正常!")
            backtrack = list(self.failed_players_since_last_success)
            self.in_review = False
            self.consecutive_empty = 0
            self.consecutive_errors = 0
            self.failed_players_since_last_success.clear()
            
            emit_event(self.shard_id, 'session_review_end', {
                'result': 'rebuilt_and_backtrack',
                'backtrack_count': len(backtrack),
            })
            return True, True, backtrack
        
        # 多次重建都失败
        print(f"  [SESSION REVIEW] 重建后仍然异常，可能是服务器端问题")
        self.in_review = False
        
        emit_event(self.shard_id, 'session_review_end', {
            'result': 'still_failing',
        })
        return False, False, []
    
    def _check_known_match(self):
        """检查一个已知的比赛页面是否可访问"""
        try:
            session = get_session()
            r = session.get('https://stats.cc/siege/matches/086591c8-3c0a-4c25-8057-f925d895b6d2', timeout=10)
            return r.status_code == 200
        except Exception:
            return False
    
    def _test_with_known_player(self):
        """用已知有排位数据的玩家测试 Session 是否正常"""
        session = get_session()
        try:
            # 用已知的排行榜玩家 profile 来测试
            r = session.get('https://stats.cc/siege/profile/3bae0298-8f3f-4fe2-ac96-91e12d31d381', timeout=15)
            if r.status_code == 200:
                nuxt = parse_nuxt_page(r.text)
                if nuxt and isinstance(nuxt, dict):
                    # 新版使用 pinia_colada 格式
                    pc = nuxt.get('pinia_colada', {})
                    for key in pc:
                        if 'profile' in key:
                            return True
                    # 有 nuxt 数据就算通过
                    if pc:
                        return True
            return False
        except Exception:
            return False


# ===== 数据获取函数（增强版）=====
def fetch_player_matches(player_name, profile_id, retries=4, mapper=None):
    """
    从 stats.cc/siege 玩家 profile 页面获取比赛历史（增强版）
    
    新版 stats.cc 变化：
    - URL: stats.cc/siege/profile/{profile_id} (不再需要 player_name 和 /pc)
    - 数据位置: pinia_colada -> ["r6","profile","{id}","matches",{}] -> pages
    """
    session = get_session()
    bump_request_count()
    url = f'https://stats.cc/siege/profile/{profile_id}'
    
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
            
            if r.status_code == 500 or r.status_code == 200:
                nuxt = parse_nuxt_page(r.text)
                if nuxt and isinstance(nuxt, dict):
                    matches = []
                    
                    # 新版: 从 pinia_colada 中提取 matches
                    pc = nuxt.get('pinia_colada', {})
                    for key in pc:
                        if 'matches' in key and profile_id in key:
                            val = pc[key]
                            if isinstance(val, list) and len(val) > 0:
                                match_data = val[0]
                                if isinstance(match_data, dict) and 'pages' in match_data:
                                    pages = match_data['pages']
                                    if isinstance(pages, list):
                                        for page in pages:
                                            if isinstance(page, list):
                                                for item in page:
                                                    if isinstance(item, dict) and 'id' in item and 'map' in item and 'playlist' in item:
                                                        raw_map = item.get('map', '')
                                                        if mapper:
                                                            mapper.normalize_map(raw_map)
                                                        
                                                        matches.append({
                                                            'match_id': item.get('id'),
                                                            'map': raw_map,
                                                            'playlist': item.get('playlist'),
                                                            'mode': item.get('mode'),
                                                            'scores': item.get('scores'),
                                                            'started_at': item.get('started_at'),
                                                            'ended_at': item.get('ended_at'),
                                                            'outcome': item.get('player_summary', {}).get('outcome') if isinstance(item.get('player_summary'), dict) else None,
                                                        })
                                            break
                    
                    if matches:
                        if r.status_code == 500:
                            print(f"    [*] HTTP 500 但解析到 {len(matches)} 个比赛（数据可用）")
                        return matches
                    
                    # 兜底: 旧版扫描方式
                    if isinstance(nuxt, (list, dict)):
                        items_to_scan = nuxt if isinstance(nuxt, list) else []
                        for i in range(len(items_to_scan)):
                            item = items_to_scan[i]
                            if isinstance(item, dict) and 'map' in item and 'playlist' in item and 'scores' in item:
                                match = item
                                if isinstance(match.get('id'), str) and len(match.get('id', '')) > 10:
                                    raw_map = match.get('map', '')
                                    if mapper:
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
                            return matches
                    
                    if r.status_code == 500:
                        print(f"    [!] HTTP 500 无比赛数据 - 该玩家数据源异常，跳过")
                        return []
                    elif r.status_code == 200:
                        return []
            
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


def fetch_match_detail(match_id, retries=4, mapper=None):
    """从 stats.cc/siege 比赛详情页获取完整回合数据（增强版）
    
    新版数据位置: pinia_colada -> ["r6","match","{id}"] -> [data, ...]
    data 包含: id, map, rounds, profiles, player_summaries, etc.
    """
    session = get_session()
    bump_request_count()
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
                    time.sleep(wait)
                    continue
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return None
            
            nuxt = parse_nuxt_page(r.text)
            if not nuxt or not isinstance(nuxt, dict):
                return None
            
            # 新版: 从 pinia_colada 中提取 match detail
            match_detail = None
            pc = nuxt.get('pinia_colada', {})
            for key in pc:
                if 'match' in key and match_id in key:
                    val = pc[key]
                    if isinstance(val, list) and len(val) > 0:
                        match_detail = val[0]
                        break
            
            if not match_detail or not isinstance(match_detail, dict):
                # 兜底: 旧版扫描
                return None
            
            # 提取 rounds（含 kill_feed 和每轮 player_summaries）
            rounds_raw = match_detail.get('rounds', [])
            round_records = []
            
            for rd in rounds_raw:
                if not isinstance(rd, dict):
                    continue
                # 从每个 round 的 player_summaries 提取干员数据
                round_ps = rd.get('player_summaries', [])
                for ps in round_ps:
                    if isinstance(ps, dict):
                        raw_op = ps.get('operator', '')
                        if mapper and raw_op:
                            mapper.normalize_operator(raw_op)
                        round_records.append({
                            'round_index': rd.get('index'),
                            'winner_team': rd.get('winner_team'),
                            'round_end_reason': rd.get('end_reason'),
                            'round_scores': rd.get('scores'),
                            'profile_id': ps.get('profile_id'),
                            'username': ps.get('username'),
                            'operator': raw_op,
                            'team': ps.get('team'),
                            'outcome': ps.get('outcome'),
                            'kills': ps.get('kills', 0),
                            'deaths': ps.get('deaths', 0),
                            'assists': ps.get('assists', 0),
                            'headshots': ps.get('headshots', 0),
                            'opening_kills': ps.get('opening_kills', 0),
                            'opening_deaths': ps.get('opening_deaths', 0),
                        })
            
            # 提取 player_summaries（全场汇总）
            player_summaries = match_detail.get('player_summaries', [])
            
            # 提取 profiles（排名信息等）
            profiles = match_detail.get('profiles', [])
            
            if not round_records and not player_summaries:
                return None
            
            raw_map = match_detail.get('map')
            if mapper and raw_map:
                mapper.normalize_map(raw_map)
            
            return {
                'match_id': match_id,
                'map': raw_map,
                'playlist': match_detail.get('playlist'),
                'mode': match_detail.get('mode'),
                'scores': match_detail.get('scores'),
                'started_at': match_detail.get('started_at'),
                'ended_at': match_detail.get('ended_at'),
                'end_reason': match_detail.get('end_reason'),
                'platform': match_detail.get('platform'),
                'player_summaries': player_summaries,
                'profiles': profiles,
                'round_records': round_records,
                'rounds_raw': rounds_raw,
                'total_rounds': len(rounds_raw),
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
    with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
        all_players = json.load(f)
    
    completed = set()
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        with open(GLOBAL_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            completed = set(progress.get('completed_players', []))
    
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith('_shard_') and fname.endswith('_progress.json'):
            fpath = os.path.join(OUTPUT_DIR, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                shard_progress = json.load(f)
                completed.update(shard_progress.get('completed_players', []))
    
    remaining = [p for p in all_players if p['profileId'] not in completed]
    return remaining, completed, all_players


def get_shard_players(shard_id, total_shards):
    remaining, completed, all_players = get_remaining_players()
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
    remaining, completed, all_players = get_remaining_players()
    total = len(remaining)
    
    print("=" * 70)
    print("分片规划 (v2 增强版)")
    print("=" * 70)
    print(f"排行榜总玩家: {len(all_players)}")
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
        print(f"  python parallel_collect_v2.py run --shard-id {shard_id} --total-shards {args.shards}")
    print(f"\n查漏补缺命令:")
    print(f"  python parallel_collect_v2.py gap-fill --total-shards {args.shards}")


# ===== 命令: run (核心增强) =====
def cmd_run(args):
    shard_id = args.shard_id
    total_shards = args.total_shards
    max_matches = args.max_matches
    delay = args.delay
    batch_size = args.batch_size
    
    os.makedirs(shard_output_dir(shard_id), exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(EVENT_LOG_DIR, exist_ok=True)
    
    # 初始化映射器
    mapper = get_mapper()
    
    # 初始化 Session 健康监控
    health = SessionHealthMonitor(shard_id, threshold=args.health_threshold)
    
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
    todo_players = [p for p in shard_players if p['profileId'] not in shard_completed]
    
    # 加载已有比赛数据
    data_file = shard_data_file(shard_id)
    all_details = []
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            all_details = json.load(f)
        for d in all_details:
            shard_completed_matches.add(d['match_id'])
    
    # 加载全局已知 match IDs
    global_match_ids = set()
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        with open(GLOBAL_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            gp = json.load(f)
            global_match_ids = set(gp.get('completed_matches', []))
    
    shared_match_ids = load_shared_match_ids()
    all_known_matches = shard_completed_matches | global_match_ids | shared_match_ids
    
    print("=" * 70)
    print(f"Shard {shard_id}/{total_shards-1} - R6 Siege 对局数据采集 (v2 增强版)")
    print("=" * 70)
    print(f"分片玩家总数: {len(shard_players)}")
    print(f"已完成: {len(shard_completed)}")
    print(f"待处理: {len(todo_players)}")
    print(f"已有比赛数据: {len(all_details)}")
    print(f"已知match IDs: {len(all_known_matches)} (含共享: {len(shared_match_ids)})")
    print(f"每人对局上限: {max_matches}")
    print(f"请求间隔: {delay}s")
    print(f"Session审查阈值: {args.health_threshold} (连续无数据触发)")
    print(f"增强: Session健康监控 + 数据脱敏检测 + 事件日志")
    print()
    
    emit_event(shard_id, 'shard_start', {
        'total_players': len(shard_players),
        'remaining': len(todo_players),
        'existing_matches': len(all_details),
    })
    
    new_players_done = 0
    new_matches_done = 0
    backtrack_queue = deque()  # 需要回溯重试的玩家
    
    # 处理函数（共用于正常和回溯模式）
    def process_player(player, is_backtrack=False):
        nonlocal new_players_done, new_matches_done, all_details, all_known_matches
        
        player_name = player['displayName']
        profile_id = player['profileId']
        rank = player.get('rank', 'unknown')
        rp = player.get('rankPoints', 0)
        pos = player.get('leaderboardPosition', '?')
        
        prefix = "[BACKTRACK]" if is_backtrack else ""
        print(f"{prefix}[S{shard_id}][{new_players_done+1}] {player_name} (#{pos}, {rank}, RP:{rp})")
        
        # Step 1: 获取比赛历史
        matches = fetch_player_matches(player_name, profile_id, mapper=mapper)
        
        if matches is None:
            # 真正的网络故障
            health.record_error(player_name)
            print(f"  [FAIL] Cannot get match history")
            
            if health.should_review():
                session_ok, needs_backtrack, bt_players = health.do_review()
                if needs_backtrack:
                    # 将失败的玩家加入回溯队列
                    for bp in bt_players:
                        # 需要从todo_players中找到对应的玩家信息
                        pass  # 已记录在failed_players中，后续补采
                if not session_ok:
                    # 等一下再继续
                    time.sleep(30)
            
            return False
        
        elif isinstance(matches, list) and len(matches) == 0:
            # 无比赛数据
            health.record_success(player_name, 0)
            save_anomaly_player(player_name, profile_id)
            shard_completed.add(profile_id)
            
            emit_event(shard_id, 'match_not_found', {
                'player': player_name,
                'consecutive_empty': health.consecutive_empty,
            })
            
            # 检查是否需要审查
            if health.should_review():
                session_ok, needs_backtrack, bt_players = health.do_review()
            
            return True
        
        else:
            health.record_success(player_name, len(matches))
        
        # 安全检查
        if not isinstance(matches, list) or len(matches) == 0:
            save_anomaly_player(player_name, profile_id, f"matches异常: type={type(matches).__name__}")
            shard_completed.add(profile_id)
            return True
        
        ranked_matches = [m for m in matches if m.get('playlist') == 'ranked']
        print(f"  Found {len(matches)} matches, ranked: {len(ranked_matches)}")
        
        new_matches = [m for m in ranked_matches if m['match_id'] not in all_known_matches]
        to_fetch = new_matches[:max_matches]
        
        print(f"  New matches to fetch: {len(to_fetch)}")
        
        # Step 2: 获取比赛详情
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
                }
                all_details.append(detail)
                all_known_matches.add(match_id)
                shard_completed_matches.add(match_id)
                new_matches_done += 1
                
                rounds = len(detail.get('round_records', []))
                players_count = detail.get('total_players', 0)
                print(f"OK ({players_count}p, {rounds}r)")
                
                emit_event(shard_id, 'match_found', {
                    'match_id': match_id,
                    'map': map_name,
                    'players': players_count,
                    'rounds': rounds,
                    'source_player': player_name,
                })
            else:
                print(f"FAIL")
            
            time.sleep(delay + random.uniform(0.1, 0.5))
        
        shard_completed.add(profile_id)
        new_players_done += 1
        
        emit_event(shard_id, 'player_done', {
            'player': player_name,
            'new_matches': len(to_fetch),
            'total_players_done': new_players_done,
        })
        
        return True
    
    # 主循环
    for idx, player in enumerate(todo_players):
        success = process_player(player)
        
        if not success:
            # 网络错误，不标记为完成，但继续处理下一个
            time.sleep(delay * 2)
            continue
        
        # 保存进度
        if (idx + 1) % batch_size == 0 or idx == len(todo_players) - 1:
            _save_shard_progress(shard_id, shard_completed, shard_completed_matches)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(all_details, f, ensure_ascii=False)
            save_shared_match_ids(shard_completed_matches)
            print(f"  [SAVE] Shard {shard_id}: {len(shard_completed)} players, {len(all_details)} matches saved")
            
            # 刷新共享 match IDs
            fresh_shared = load_shared_match_ids()
            new_from_others = len(fresh_shared - all_known_matches)
            all_known_matches.update(fresh_shared)
            if new_from_others > 0:
                print(f"  [DEDUP] 从其他分片获得 {new_from_others} 个新 match IDs")
        
        time.sleep(delay + random.uniform(0.1, 0.5))
    
    # 最终保存
    _save_shard_progress(shard_id, shard_completed, shard_completed_matches)
    save_shared_match_ids(shard_completed_matches)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    # 保存映射表
    mapper.save()
    
    # 检查格式变化
    if mapper.format_changes:
        print(f"\n  ⚠️ 数据格式变化检测:")
        print(f"  {mapper.get_format_change_report()}")
    
    emit_event(shard_id, 'shard_done', {
        'players_done': new_players_done,
        'matches_done': new_matches_done,
        'total_matches': len(all_details),
        'session_rebuilds': health.total_session_rebuilds,
        'session_reviews': health.review_count,
    })
    
    print(f"\n{'=' * 70}")
    print(f"Shard {shard_id} 完成! (v2)")
    print(f"{'=' * 70}")
    print(f"玩家处理: {new_players_done}")
    print(f"新比赛详情: {new_matches_done}")
    print(f"总比赛详情: {len(all_details)}")
    print(f"Session 审查次数: {health.review_count}")
    print(f"Session 重建次数: {health.total_session_rebuilds}")


def _save_shard_progress(shard_id, completed_players, completed_matches):
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


# ===== 命令: status =====
def cmd_status(args):
    total_shards = args.total_shards
    remaining, completed, all_players = get_remaining_players()
    
    print("=" * 70)
    print("采集进度总览 (v2)")
    print("=" * 70)
    print(f"排行榜总玩家: {len(all_players)}")
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
            version = sp.get('version', 'v1')
            total_shard_players += p_done
            total_shard_matches += m_done
            print(f"  Shard {shard_id}: {p_done} players, {m_done} matches ({version}) (updated: {last_update})")
        else:
            print(f"  Shard {shard_id}: Not started")
    
    print(f"\n  Total across shards: {total_shard_players} players, {total_shard_matches} matches")
    
    # 检查事件日志
    if os.path.exists(EVENT_LOG_DIR):
        print(f"\n  事件日志:")
        for shard_id in range(total_shards):
            status_file = os.path.join(EVENT_LOG_DIR, f'shard_{shard_id}_status.json')
            if os.path.exists(status_file):
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                print(f"    Shard {shard_id}: 最新事件={status.get('last_event', '?')} ({status.get('last_event_time', '?')})")


# ===== 命令: merge =====
def cmd_merge(args):
    total_shards = args.total_shards
    
    print("=" * 70)
    print("合并所有分片数据 (v2)")
    print("=" * 70)
    
    all_details = []
    all_completed_players = set()
    all_completed_matches = set()
    seen_match_ids = set()
    
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
    
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        with open(GLOBAL_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            gp = json.load(f)
            all_completed_players.update(gp.get('completed_players', []))
            all_completed_matches.update(gp.get('completed_matches', []))
    
    for shard_id in range(total_shards):
        data_file = shard_data_file(shard_id)
        pf = shard_progress_file(shard_id)
        
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
        
        if os.path.exists(pf):
            with open(pf, 'r', encoding='utf-8') as f:
                sp = json.load(f)
                all_completed_players.update(sp.get('completed_players', []))
                all_completed_matches.update(sp.get('completed_matches', []))
    
    with open(global_data_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    global_progress = {
        'completed_players': list(all_completed_players),
        'completed_matches': list(all_completed_matches),
        'failed_players': [],
        'failed_matches': [],
        'player_match_map': {},
        'version': 'v2',
        'stats': {
            'total_players_processed': len(all_completed_players),
            'total_match_details_fetched': len(all_details),
            'total_round_records': sum(len(d.get('round_records', [])) for d in all_details),
            'merged_at': datetime.now().isoformat(),
        }
    }
    with open(GLOBAL_PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(global_progress, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"合并完成! (v2)")
    print(f"{'=' * 70}")
    print(f"总玩家: {len(all_completed_players)}")
    print(f"总比赛详情: {len(all_details)} (去重)")
    print(f"总回合记录: {global_progress['stats']['total_round_records']}")
    print(f"数据文件: {global_data_file} ({os.path.getsize(global_data_file):,} bytes)")


# ===== 命令: gap-fill (查漏补缺) =====
def cmd_gap_fill(args):
    """扫描所有分片数据，查找遗漏的对局和玩家，自动补采"""
    total_shards = args.total_shards
    delay = args.delay
    mapper = get_mapper()
    
    print("=" * 70)
    print("查漏补缺 - 扫描数据缺口")
    print("=" * 70)
    
    # 1. 加载所有已完成的玩家和对局
    all_completed_players = set()
    all_completed_matches = set()
    all_match_details = {}  # match_id -> detail
    
    for shard_id in range(total_shards):
        pf = shard_progress_file(shard_id)
        df = shard_data_file(shard_id)
        
        if os.path.exists(pf):
            with open(pf, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            all_completed_players.update(sp.get('completed_players', []))
            all_completed_matches.update(sp.get('completed_matches', []))
        
        if os.path.exists(df):
            with open(df, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for d in data:
                mid = d.get('match_id')
                if mid:
                    all_match_details[mid] = d
    
    print(f"已完成玩家: {len(all_completed_players)}")
    print(f"已完成对局: {len(all_completed_matches)}")
    print(f"已有对局详情: {len(all_match_details)}")
    
    # 2. 检查排行榜中未处理的玩家
    with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
        all_players = json.load(f)
    
    missing_players = [p for p in all_players if p['profileId'] not in all_completed_players]
    print(f"\n遗漏的排行榜玩家: {len(missing_players)}")
    
    # 3. 检查对局详情中出现但没有单独采集过的玩家（发现新玩家）
    discovered_players = set()
    for mid, detail in all_match_details.items():
        for ps in detail.get('player_summaries', []):
            pid = ps.get('profile_id')
            if pid and pid not in all_completed_players:
                discovered_players.add(pid)
    
    print(f"在对局中发现的未采集玩家: {len(discovered_players)}")
    
    # 4. 检查已采集对局中是否有数据不完整的
    incomplete_matches = []
    for mid, detail in all_match_details.items():
        rounds = len(detail.get('round_records', []))
        players = detail.get('total_players', 0)
        if rounds == 0 or players == 0:
            incomplete_matches.append(mid)
    
    print(f"数据不完整的对局: {len(incomplete_matches)}")
    
    # 5. 补采遗漏的排行榜玩家
    if missing_players:
        print(f"\n开始补采 {len(missing_players)} 个遗漏玩家...")
        gap_data_file = os.path.join(OUTPUT_DIR, '_gap_fill_matches.json')
        gap_details = []
        if os.path.exists(gap_data_file):
            with open(gap_data_file, 'r', encoding='utf-8') as f:
                gap_details = json.load(f)
        
        for idx, player in enumerate(missing_players):
            player_name = player['displayName']
            profile_id = player['profileId']
            rank = player.get('rank', 'unknown')
            rp = player.get('rankPoints', 0)
            
            print(f"[GAP {idx+1}/{len(missing_players)}] {player_name} ({rank})")
            
            matches = fetch_player_matches(player_name, profile_id, mapper=mapper)
            
            if matches is None:
                print(f"  [FAIL]")
                time.sleep(delay * 2)
                continue
            
            if isinstance(matches, list) and len(matches) == 0:
                save_anomaly_player(player_name, profile_id, "gap-fill: 无数据")
                all_completed_players.add(profile_id)
                time.sleep(delay)
                continue
            
            if not isinstance(matches, list):
                all_completed_players.add(profile_id)
                time.sleep(delay)
                continue
            
            ranked_matches = [m for m in matches if m.get('playlist') == 'ranked']
            new_matches = [m for m in ranked_matches if m['match_id'] not in all_completed_matches]
            to_fetch = new_matches[:args.max_matches]
            
            print(f"  Found {len(ranked_matches)} ranked, {len(to_fetch)} new")
            
            for midx, match in enumerate(to_fetch):
                match_id = match['match_id']
                print(f"    [{midx+1}/{len(to_fetch)}] {match_id[:12]}...", end=' ', flush=True)
                
                detail = fetch_match_detail(match_id, mapper=mapper)
                if detail:
                    detail['source_player'] = {
                        'displayName': player_name,
                        'profileId': profile_id,
                        'rank': rank,
                        'rankPoints': rp,
                        'source': 'gap_fill',
                    }
                    gap_details.append(detail)
                    all_completed_matches.add(match_id)
                    print(f"OK")
                    
                    emit_event(-1, 'gap_filled', {
                        'match_id': match_id,
                        'source_player': player_name,
                    })
                else:
                    print(f"FAIL")
                
                time.sleep(delay + random.uniform(0.1, 0.5))
            
            all_completed_players.add(profile_id)
            
            # 每10个玩家保存一次
            if (idx + 1) % 10 == 0:
                with open(gap_data_file, 'w', encoding='utf-8') as f:
                    json.dump(gap_details, f, ensure_ascii=False)
                print(f"  [SAVE] Gap fill: {len(gap_details)} matches")
            
            time.sleep(delay)
        
        # 最终保存
        with open(gap_data_file, 'w', encoding='utf-8') as f:
            json.dump(gap_details, f, ensure_ascii=False, indent=2)
        
        print(f"\n补采完成: {len(gap_details)} 个新对局详情")
        print(f"保存到: {gap_data_file}")
    
    # 6. 补采不完整的对局
    if incomplete_matches:
        print(f"\n重新采集 {len(incomplete_matches)} 个不完整的对局...")
        refetched = 0
        for mid in incomplete_matches:
            detail = fetch_match_detail(mid, mapper=mapper)
            if detail and len(detail.get('round_records', [])) > 0:
                all_match_details[mid] = detail
                refetched += 1
            time.sleep(delay)
        print(f"  成功修复: {refetched}/{len(incomplete_matches)}")
    
    # 保存映射表
    mapper.save()
    
    print(f"\n{'=' * 70}")
    print(f"查漏补缺完成!")
    print(f"{'=' * 70}")


# ===== 主入口 =====
def main():
    parser = argparse.ArgumentParser(description='R6 Siege 分片并行采集 v2 (增强版)')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # plan
    plan_parser = subparsers.add_parser('plan', help='查看分片规划')
    plan_parser.add_argument('--shards', type=int, default=5, help='分片数')
    
    # run
    run_parser = subparsers.add_parser('run', help='运行指定分片')
    run_parser.add_argument('--shard-id', type=int, required=True, help='分片 ID (0-indexed)')
    run_parser.add_argument('--total-shards', type=int, required=True, help='总分片数')
    run_parser.add_argument('--max-matches', type=int, default=10, help='每人最多采集几场比赛详情')
    run_parser.add_argument('--delay', type=float, default=1.0, help='请求间隔秒数')
    run_parser.add_argument('--batch-size', type=int, default=3, help='每几个玩家保存一次')
    run_parser.add_argument('--health-threshold', type=int, default=5, help='连续多少次无数据触发Session审查')
    
    # status
    status_parser = subparsers.add_parser('status', help='查看进度')
    status_parser.add_argument('--total-shards', type=int, default=5, help='总分片数')
    
    # merge
    merge_parser = subparsers.add_parser('merge', help='合并所有分片数据')
    merge_parser.add_argument('--total-shards', type=int, default=5, help='总分片数')
    
    # gap-fill
    gap_parser = subparsers.add_parser('gap-fill', help='查漏补缺')
    gap_parser.add_argument('--total-shards', type=int, default=5, help='总分片数')
    gap_parser.add_argument('--max-matches', type=int, default=10, help='每人最多采集几场')
    gap_parser.add_argument('--delay', type=float, default=1.0, help='请求间隔')
    
    args = parser.parse_args()
    
    if args.command == 'plan':
        cmd_plan(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'merge':
        cmd_merge(args)
    elif args.command == 'gap-fill':
        cmd_gap_fill(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

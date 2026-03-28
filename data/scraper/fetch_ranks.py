"""
批量采集玩家段位信息 V2
从 stats.cc 提取精确的 5 级段位 slug + RP 值
取最新赛季的段位，如果没有则取最近一个有段位的赛季

用法:
  python fetch_ranks.py run --shard-id 0 --total-shards 24 --delay 0.8
  python fetch_ranks.py status
"""
import json
import os
import sys
import io
import re
import time
import random
import argparse
import requests
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = BASE_DIR / 'output' / 'rank_data'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLAYERS_FILE = BASE_DIR / 'output' / '_players_need_rank.json'

# 完整的 5 级段位 (V/IV/III/II/I per tier) + champion
ALL_VALID_RANKS = set()
for tier in ['copper', 'bronze', 'silver', 'gold', 'platinum', 'emerald', 'diamond']:
    for div in ['v', 'iv', 'iii', 'ii', 'i']:
        ALL_VALID_RANKS.add(f'{tier}-{div}')
ALL_VALID_RANKS.add('champion')
ALL_VALID_RANKS.add('unranked')

# RP -> 段位映射 (游戏内 5 级制)
RP_RANK_MAP = [
    (5000, 'champion'),
    (4400, 'diamond-i'), (4300, 'diamond-ii'), (4200, 'diamond-iii'), (4100, 'diamond-iv'), (4000, 'diamond-v'),
    (3900, 'emerald-i'), (3800, 'emerald-ii'), (3700, 'emerald-iii'), (3600, 'emerald-iv'), (3500, 'emerald-v'),
    (3400, 'platinum-i'), (3300, 'platinum-ii'), (3200, 'platinum-iii'), (3100, 'platinum-iv'), (3000, 'platinum-v'),
    (2900, 'gold-i'), (2800, 'gold-ii'), (2700, 'gold-iii'), (2600, 'gold-iv'), (2500, 'gold-v'),
    (2400, 'silver-i'), (2300, 'silver-ii'), (2200, 'silver-iii'), (2100, 'silver-iv'), (2000, 'silver-v'),
    (1900, 'bronze-i'), (1800, 'bronze-ii'), (1700, 'bronze-iii'), (1600, 'bronze-iv'), (1500, 'bronze-v'),
    (1400, 'copper-i'), (1300, 'copper-ii'), (1200, 'copper-iii'), (1100, 'copper-iv'), (1000, 'copper-v'),
    (0, 'copper-v'),
]

def rp_to_rank(rp):
    for threshold, rank in RP_RANK_MAP:
        if rp >= threshold:
            return rank
    return 'copper-v'

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
})


def extract_rank_and_rp(text):
    """从 stats.cc Nuxt 数据提取最新赛季的段位和 RP"""
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
    if not m:
        return None, None
    
    try:
        nuxt = json.loads(m.group(1))
    except:
        return None, None
    
    # 策略: 找所有包含 rank + rank_points 的对象 (赛季记录)
    # 这些对象的结构: {wins, losses, abandons, rank_points_delta, rank, rank_points, created_at}
    # rank 和 rank_points 都是引用索引
    best_rp = None
    best_rank = None
    best_date = None
    
    for i, item in enumerate(nuxt):
        if not isinstance(item, dict):
            continue
        if 'rank_points' not in item or 'rank' not in item:
            continue
        if 'wins' not in item and 'losses' not in item:
            continue  # 不是赛季记录
        
        # 解引用 rank_points
        rp_ref = item['rank_points']
        rp_val = None
        if isinstance(rp_ref, int) and rp_ref < len(nuxt) and isinstance(nuxt[rp_ref], (int, float)):
            rp_val = int(nuxt[rp_ref])
        elif isinstance(rp_ref, (int, float)) and rp_ref > 500:
            rp_val = int(rp_ref)
        
        if rp_val is None or rp_val < 100:
            continue
        
        # 解引用 rank (slug)
        rank_ref = item['rank']
        rank_slug = None
        if isinstance(rank_ref, int) and rank_ref < len(nuxt):
            rv = nuxt[rank_ref]
            if isinstance(rv, str):
                rank_slug = rv
            elif isinstance(rv, dict) and 'slug' in rv:
                slug_ref = rv['slug']
                if isinstance(slug_ref, int) and slug_ref < len(nuxt):
                    rank_slug = nuxt[slug_ref]
                elif isinstance(slug_ref, str):
                    rank_slug = slug_ref
        
        # 解引用 created_at (日期)
        date_str = None
        if 'created_at' in item:
            date_ref = item['created_at']
            if isinstance(date_ref, int) and date_ref < len(nuxt) and isinstance(nuxt[date_ref], str):
                date_str = nuxt[date_ref]
            elif isinstance(date_ref, str):
                date_str = date_ref
        
        # 取最新的记录 (第一个出现的通常是最新的)
        if best_rp is None:
            best_rp = rp_val
            best_rank = rank_slug
            best_date = date_str
        elif date_str and best_date and date_str > best_date:
            best_rp = rp_val
            best_rank = rank_slug
            best_date = date_str
    
    if best_rp:
        # 用 RP 精确映射到 5 级段位 (忽略 stats.cc 的 3 级 slug)
        mapped_rank = rp_to_rank(best_rp)
        return mapped_rank, best_rp
    
    # 回退: 找第一个 rank 对象引用
    for i, item in enumerate(nuxt):
        if isinstance(item, dict) and 'rank' in item and len(item) < 5:
            rank_ref = item['rank']
            if isinstance(rank_ref, int) and rank_ref < len(nuxt):
                rv = nuxt[rank_ref]
                if isinstance(rv, str) and rv in ALL_VALID_RANKS:
                    return rv, None
    
    return None, None


class AdaptiveDelay:
    def __init__(self, base_delay=0.8):
        self.base = base_delay
        self.current = base_delay
        self.consecutive_429 = 0

    def success(self):
        self.consecutive_429 = 0
        self.current = max(self.base, self.current * 0.95)

    def rate_limited(self):
        self.consecutive_429 += 1
        self.current = min(self.current * 2, 30)

    def wait(self):
        jitter = random.uniform(0.05, 0.3)
        time.sleep(self.current + jitter)


def load_progress(shard_id):
    pf = OUTPUT_DIR / f'shard_{shard_id}_progress.json'
    if pf.exists():
        return json.load(open(pf, 'r', encoding='utf-8'))
    return {'completed': {}}


def save_progress(shard_id, progress):
    pf = OUTPUT_DIR / f'shard_{shard_id}_progress.json'
    with open(pf, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False)


def run_shard(shard_id, total_shards, delay):
    sys.stdout.flush()
    print(f"[Shard {shard_id}/{total_shards}] Loading players...", flush=True)
    all_players = json.load(open(PLAYERS_FILE, 'r', encoding='utf-8'))
    shard_players = [p for i, p in enumerate(all_players) if i % total_shards == shard_id]
    
    progress = load_progress(shard_id)
    completed = progress['completed']
    
    # 加载全局已完成列表（跨分片去重）
    global_done_file = OUTPUT_DIR / '_global_completed.json'
    global_done = set()
    if global_done_file.exists():
        try:
            global_done = set(json.load(open(global_done_file, 'r', encoding='utf-8')).keys())
        except:
            pass
    
    # error/timeout 的需要重试，不算完成
    retry_statuses = {'error', 'timeout'}
    done_pids = set()
    for pid, val in completed.items():
        rank = val.get('rank', '') if isinstance(val, dict) else val
        if rank not in retry_statuses:
            done_pids.add(pid)
    
    todo = [p for p in shard_players if p not in done_pids and p not in global_done]
    
    print(f"[Shard {shard_id}] Total: {len(shard_players)}, Done: {len(completed)}, GlobalSkip: {len(shard_players)-len(todo)-len(completed)}, Todo: {len(todo)}", flush=True)
    
    ad = AdaptiveDelay(delay)
    batch_size = 50
    
    for idx, pid in enumerate(todo):
        url = f'https://stats.cc/siege/{pid}'
        rank = None
        rp = None
        
        for attempt in range(3):
            try:
                r = SESSION.get(url, timeout=12)
                if r.status_code == 200:
                    rank, rp = extract_rank_and_rp(r.text)
                    if rank is None:
                        rank = 'unknown'
                    ad.success()
                    break
                elif r.status_code == 429:
                    ad.rate_limited()
                    print(f"  [429] Shard {shard_id}, waiting {ad.current:.1f}s", flush=True)
                    ad.wait()
                else:
                    rank = 'error'
                    break
            except requests.Timeout:
                if attempt < 2:
                    time.sleep(2)
                else:
                    rank = 'timeout'
            except Exception:
                rank = 'error'
                break
        
        completed[pid] = {'rank': rank or 'unknown', 'rp': rp}
        
        if (idx + 1) % batch_size == 0 or idx == len(todo) - 1:
            progress['completed'] = completed
            save_progress(shard_id, progress)
        
        if (idx + 1) % 200 == 0:
            pct = len(completed) / len(shard_players) * 100 if shard_players else 0
            print(f"  [S{shard_id}] {len(completed)}/{len(shard_players)} ({pct:.1f}%) delay={ad.current:.2f}s last={rank} rp={rp}", flush=True)
        
        ad.wait()
    
    progress['completed'] = completed
    save_progress(shard_id, progress)
    print(f"[Shard {shard_id}] Done! {len(completed)}/{len(shard_players)}", flush=True)


def show_status():
    if not PLAYERS_FILE.exists():
        print("No player list"); return
    
    all_players = json.load(open(PLAYERS_FILE, 'r', encoding='utf-8'))
    total = len(all_players)
    
    all_completed = {}
    # 先加载全局已完成
    global_done_file = OUTPUT_DIR / '_global_completed.json'
    if global_done_file.exists():
        try:
            gd = json.load(open(global_done_file, 'r', encoding='utf-8'))
            for pid, val in gd.items():
                if isinstance(val, dict):
                    all_completed[pid] = val
                else:
                    all_completed[pid] = {'rank': val, 'rp': None}
        except:
            pass
    # 再加载各分片进度
    for pf in sorted(OUTPUT_DIR.glob('shard_*_progress.json')):
        data = json.load(open(pf, 'r', encoding='utf-8'))
        for pid, val in data.get('completed', {}).items():
            if isinstance(val, dict):
                all_completed[pid] = val
            else:
                all_completed[pid] = {'rank': val, 'rp': None}
    
    done = len(all_completed)
    print(f"Total: {total}")
    print(f"Done: {done} ({done/total*100:.1f}%)")
    print(f"Remaining: {total - done}")
    
    from collections import Counter
    ranks = Counter(v['rank'] for v in all_completed.values())
    has_rp = sum(1 for v in all_completed.values() if v.get('rp'))
    print(f"Has RP data: {has_rp}/{done}")
    print(f"\nRank distribution ({done}):")
    for rank, count in sorted(ranks.items(), key=lambda x: -x[1]):
        print(f"  {rank:20s}: {count:6d} ({count/done*100:5.1f}%)")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command')
    
    run_p = sub.add_parser('run')
    run_p.add_argument('--shard-id', type=int, required=True)
    run_p.add_argument('--total-shards', type=int, required=True)
    run_p.add_argument('--delay', type=float, default=0.8)
    
    sub.add_parser('status')
    args = parser.parse_args()
    
    if args.command == 'run':
        run_shard(args.shard_id, args.total_shards, args.delay)
    elif args.command == 'status':
        show_status()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

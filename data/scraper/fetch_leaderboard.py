"""
从 stats.cc 排行榜批量爬取所有玩家数据
通过解析 Nuxt SSR __NUXT_DATA__ 获取，无需 API Key
支持断点续爬、自动探测最大页数、自适应速率控制

用法:
  python fetch_leaderboard.py --all                    # 自动爬取所有页
  python fetch_leaderboard.py --pages 100              # 爬100页
  python fetch_leaderboard.py --resume                 # 从上次中断处继续
  python fetch_leaderboard.py --start-page 7 --all     # 从第7页开始爬到底
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
    'Referer': 'https://stats.cc/siege/leaderboards/pc/ranked/rankPoints',
}

# ===== 全局 Session =====
_session = None

def get_session():
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


def deref(data, idx, depth=0, max_depth=20, cache=None):
    """递归解引用 Nuxt 3 __NUXT_DATA__ 中的数据"""
    if cache is None:
        cache = {}
    if idx in cache:
        return cache[idx]
    if depth > max_depth:
        return f"[MAX_DEPTH at {idx}]"
    if idx >= len(data):
        return None
    
    item = data[idx]
    
    if isinstance(item, (str, float, bool)) or item is None:
        return item
    
    # 整数可能是数据本身，也可能是引用——需要根据上下文判断
    # 这里我们在 dict value 和 list 中调用时才解引用
    if isinstance(item, int):
        return item
    
    if isinstance(item, list):
        if len(item) == 2 and isinstance(item[0], str) and item[0] in ('ShallowReactive', 'Reactive', 'ShallowRef', 'Ref', 'Set'):
            result = deref(data, item[1], depth + 1, max_depth, cache)
            cache[idx] = result
            return result
        else:
            # 列表中的元素如果是整数，当作索引解引用
            result = []
            for i in item:
                if isinstance(i, int):
                    result.append(deref(data, i, depth + 1, max_depth, cache))
                else:
                    result.append(i)
            cache[idx] = result
            return result
    
    if isinstance(item, dict):
        result = {}
        for key, val_idx in item.items():
            if isinstance(val_idx, int):
                result[key] = deref(data, val_idx, depth + 1, max_depth, cache)
            else:
                result[key] = val_idx
        cache[idx] = result
        return result
    
    return item


def fetch_leaderboard_page(page, platform='pc', mode='ranked', stat='rankPoints', retries=5):
    """获取排行榜单页数据，带智能重试"""
    url = f'https://stats.cc/siege/leaderboards/{platform}/{mode}/{stat}?page={page}'
    
    for attempt in range(retries):
        try:
            session = get_session()
            r = session.get(url, timeout=(10, 25))
            if r.status_code != 200:
                print(f"  [!] Page {page}: HTTP {r.status_code} (attempt {attempt+1}/{retries})")
                if r.status_code == 429:
                    wait = min((attempt + 1) * 15, 90)  # 15, 30, 45, 60, 75s
                    print(f"  [!] Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                elif r.status_code == 403:
                    wait = (attempt + 1) * 20
                    print(f"  [!] Forbidden, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                elif r.status_code >= 500:
                    wait = (attempt + 1) * 5
                    print(f"  [!] Server error, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return None
            
            # 解析 NUXT DATA
            json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if not json_blocks:
                print(f"  [!] Page {page}: No NUXT data found")
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return None
            
            nuxt_data = json.loads(json_blocks[0])
            
            # 找到 leaderboard 数据的 key
            root_idx = 3
            if root_idx >= len(nuxt_data):
                print(f"  [!] Page {page}: NUXT data structure changed")
                return None
            root = nuxt_data[root_idx]
            
            lb_key = None
            lb_index = None
            if isinstance(root, dict):
                for key, val in root.items():
                    if 'leaderboard' in key.lower():
                        lb_key = key
                        lb_index = val
                        break
            
            if lb_index is None:
                print(f"  [!] Page {page}: No leaderboard key in NUXT data")
                return None
            
            # 解引用
            lb_data = deref(nuxt_data, lb_index, max_depth=25)
            
            if not isinstance(lb_data, dict) or 'profiles' not in lb_data:
                print(f"  [!] Page {page}: Unexpected data structure")
                return None
            
            # 空页面 = 到达排行榜末尾
            if len(lb_data.get('profiles', [])) == 0:
                print(f"  [END] Page {page}: Empty page - reached end of leaderboard")
                return 'END'
            
            return lb_data
            
        except json.JSONDecodeError as e:
            print(f"  [!] Page {page}: JSON parse error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
        except requests.exceptions.Timeout:
            print(f"  [!] Page {page}: Timeout (attempt {attempt+1}/{retries})")
            if attempt < retries - 1:
                time.sleep(10)
        except Exception as e:
            print(f"  [!] Page {page}: Error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    
    return None


def extract_player_data(lb_data):
    """从排行榜数据中提取简化的玩家信息"""
    players = []
    for entry in lb_data.get('profiles', []):
        profile = entry.get('profile', {})
        
        # 提取当前赛季排位数据
        seasonal = profile.get('seasonalRecords', {})
        ranked_data = {}
        for season_name, season_data in seasonal.items():
            if isinstance(season_data, dict) and 'ranked' in season_data:
                ranked_data = season_data['ranked']
                break
        
        player = {
            'displayName': profile.get('displayName', ''),
            'profileId': profile.get('profileId', ''),
            'platform': profile.get('platform', ''),
            'level': profile.get('level', 0),
            'headshotRate': profile.get('headshotRate', 0),
            'leaderboardPosition': entry.get('position', profile.get('leaderboardPosition', 0)),
            'rank': ranked_data.get('rank', ''),
            'maxRank': ranked_data.get('maxRank', ''),
            'rankPoints': ranked_data.get('rankPoints', 0),
            'maxRankPoints': ranked_data.get('maxRankPoints', 0),
            'kills': ranked_data.get('kills', 0),
            'deaths': ranked_data.get('deaths', 0),
            'wins': ranked_data.get('wins', 0),
            'losses': ranked_data.get('losses', 0),
            'abandons': ranked_data.get('abandons', 0),
            'kd': round(ranked_data.get('kills', 0) / max(ranked_data.get('deaths', 1), 1), 3),
            'winRate': round(ranked_data.get('wins', 0) / max(ranked_data.get('wins', 0) + ranked_data.get('losses', 0), 1) * 100, 2),
        }
        players.append(player)
    
    return players


def main():
    parser = argparse.ArgumentParser(description='Fetch R6 Siege leaderboard from stats.cc')
    parser.add_argument('--pages', type=int, default=0, help='Number of pages to fetch (0 = auto-detect with --all)')
    parser.add_argument('--all', action='store_true', help='Auto-detect and fetch ALL available pages')
    parser.add_argument('--start-page', type=int, default=1, help='Start from this page (default: 1)')
    parser.add_argument('--resume', action='store_true', help='Resume from where we left off (auto-detect last page)')
    parser.add_argument('--platform', type=str, default='pc', choices=['pc', 'console', 'global'], help='Platform')
    parser.add_argument('--delay', type=float, default=3.0, help='Base delay between requests in seconds (default: 3.0)')
    parser.add_argument('--output-dir', type=str, default='./output/leaderboard', help='Output directory')
    parser.add_argument('--save-raw', action='store_true', help='Also save raw page data')
    parser.add_argument('--max-pages', type=int, default=500, help='Safety limit on max pages (default: 500)')
    
    args = parser.parse_args()
    
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载已有数据
    full_path = os.path.join(output_dir, 'leaderboard_full.json')
    progress_path = os.path.join(output_dir, '_lb_progress.json')
    existing_players = []
    existing_ids = set()
    last_page_fetched = 0
    
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            existing_players = json.load(f)
        existing_ids = set(p['profileId'] for p in existing_players if p.get('profileId'))
        print(f"[LOAD] Existing data: {len(existing_players)} players ({len(existing_ids)} unique)")
    
    if os.path.exists(progress_path):
        with open(progress_path, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            last_page_fetched = progress.get('last_page_fetched', 0)
            print(f"[LOAD] Last successfully fetched page: {last_page_fetched}")
    
    # 确定起始页
    start_page = args.start_page
    if args.resume and last_page_fetched > 0:
        start_page = last_page_fetched + 1
        print(f"[RESUME] Continuing from page {start_page}")
    
    # 确定结束页
    if args.all:
        end_page = start_page + args.max_pages - 1  # 安全上限，实际会在空页时停止
        mode_str = f"AUTO-DETECT (up to page {end_page})"
    elif args.pages > 0:
        end_page = start_page + args.pages - 1
        mode_str = f"page {start_page} to {end_page}"
    else:
        end_page = start_page + 100 - 1  # 默认100页
        mode_str = f"page {start_page} to {end_page} (default)"
    
    print("=" * 70)
    print("R6 Siege Leaderboard Fetcher v2 (stats.cc)")
    print("=" * 70)
    print(f"Platform: {args.platform}")
    print(f"Mode: {mode_str}")
    print(f"Base delay: {args.delay}s (with jitter)")
    print(f"Output: {output_dir}")
    print(f"Existing: {len(existing_players)} players")
    print()
    
    all_players = list(existing_players)  # 保留已有数据
    seen_ids = set(existing_ids)
    failed_pages = []
    consecutive_fails = 0
    consecutive_empty = 0
    new_players_added = 0
    pages_fetched = 0
    
    for page in range(start_page, end_page + 1):
        print(f"[Page {page}] Fetching...")
        
        lb_data = fetch_leaderboard_page(page, platform=args.platform)
        
        # 到达排行榜末尾
        if lb_data == 'END':
            print(f"\n🏁 Reached end of leaderboard at page {page}")
            break
        
        if lb_data is None:
            print(f"  [FAIL] Page {page}")
            failed_pages.append(page)
            consecutive_fails += 1
            
            # 连续失败太多次，可能被封了，加大等待
            if consecutive_fails >= 3:
                wait = min(consecutive_fails * 30, 180)
                print(f"  [!] {consecutive_fails} consecutive failures, waiting {wait}s...")
                time.sleep(wait)
            
            if consecutive_fails >= 10:
                print(f"\n⚠️ Too many consecutive failures ({consecutive_fails}), stopping.")
                break
            
            time.sleep(args.delay)
            continue
        
        consecutive_fails = 0  # 重置连续失败计数
        
        players = extract_player_data(lb_data)
        
        if not players:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print(f"\n🏁 {consecutive_empty} consecutive empty pages, reached end of leaderboard")
                break
            time.sleep(args.delay)
            continue
        
        consecutive_empty = 0
        
        # 去重添加
        new_count = 0
        for p in players:
            pid = p.get('profileId', '')
            if pid and pid not in seen_ids:
                all_players.append(p)
                seen_ids.add(pid)
                new_count += 1
        
        new_players_added += new_count
        pages_fetched += 1
        
        # 打印本页摘要
        first = players[0]
        last = players[-1]
        ranks = set(p['rank'] for p in players)
        print(f"  [OK] {len(players)} players (+{new_count} new), positions {first['leaderboardPosition']}-{last['leaderboardPosition']}")
        print(f"       Ranks: {', '.join(sorted(ranks))}")
        print(f"       RP range: {last['rankPoints']}-{first['rankPoints']}")
        print(f"       Total unique: {len(seen_ids)}")
        
        # 保存原始数据
        if args.save_raw:
            raw_path = os.path.join(output_dir, f'raw_page_{page:03d}.json')
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(lb_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 更新进度
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_page_fetched': page,
                'total_players': len(all_players),
                'unique_players': len(seen_ids),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        # 每5页保存一次中间结果
        if page % 5 == 0:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(all_players, f, ensure_ascii=False, indent=2)
            print(f"  [SAVE] Checkpoint: {len(all_players)} players total")
        
        # 自适应延迟：加上随机抖动避免被识别为爬虫
        delay = args.delay + random.uniform(0.5, 2.0)
        if page % 20 == 0:
            # 每20页多休息一会儿
            delay += random.uniform(3, 8)
            print(f"  [PAUSE] Extended pause: {delay:.1f}s")
        time.sleep(delay)
    
    # 保存完整结果
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS")
    print(f"{'=' * 70}")
    print(f"Pages fetched this run: {pages_fetched}")
    print(f"New players added: {new_players_added}")
    print(f"Total players: {len(all_players)} ({len(seen_ids)} unique)")
    print(f"Failed pages: {len(failed_pages)} {failed_pages[:20] if failed_pages else ''}")
    print(f"Saved: {full_path} ({os.path.getsize(full_path):,} bytes)")
    
    # 按段位统计
    rank_counts = {}
    for p in all_players:
        rank = p.get('rank', 'unknown')
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    print(f"\nRank distribution:")
    for rank, count in sorted(rank_counts.items(), key=lambda x: -x[1]):
        pct = count / len(all_players) * 100
        bar = '█' * int(pct / 2)
        print(f"  {rank:20s}: {count:6d} ({pct:5.1f}%) {bar}")
    
    # 保存仅包含玩家名和段位的轻量文件
    names_path = os.path.join(output_dir, 'player_names.json')
    names_data = [{
        'name': p['displayName'], 
        'profileId': p['profileId'],
        'rank': p['rank'], 
        'rankPoints': p['rankPoints'], 
        'position': p['leaderboardPosition']
    } for p in all_players]
    with open(names_path, 'w', encoding='utf-8') as f:
        json.dump(names_data, f, ensure_ascii=False, indent=2)
    print(f"Saved player names: {names_path}")
    
    if failed_pages:
        fail_path = os.path.join(output_dir, 'failed_pages.json')
        with open(fail_path, 'w') as f:
            json.dump(failed_pages, f)
        print(f"Failed pages saved: {fail_path}")
    
    print(f"\n✅ Done! Use --resume to continue from page {page}")
    print(f"   Next step: python batch_collect.py --max-players {len(all_players)} --resume")


if __name__ == '__main__':
    main()

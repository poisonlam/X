"""
从 stats.cc 爬取额外排行榜数据（Console、Global）
并与已有 PC 排行榜数据去重，生成额外玩家列表

用法:
  python fetch_extra_leaderboards.py --platform console --all
  python fetch_extra_leaderboards.py --platform global --all
  python fetch_extra_leaderboards.py --platform console --resume
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
    # Note: Do NOT set Accept-Encoding manually - let requests handle it
    # Setting 'br' (brotli) causes issues if brotli decoder is not installed
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'leaderboard')
PC_LB_FILE = os.path.join(OUTPUT_DIR, 'leaderboard_full.json')


def deref(data, idx, depth=0, max_depth=20, cache=None):
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
    if isinstance(item, int):
        return item
    if isinstance(item, list):
        if len(item) == 2 and isinstance(item[0], str) and item[0] in ('ShallowReactive', 'Reactive', 'ShallowRef', 'Ref', 'Set'):
            result = deref(data, item[1], depth + 1, max_depth, cache)
            cache[idx] = result
            return result
        else:
            result = [deref(data, i, depth + 1, max_depth, cache) if isinstance(i, int) else i for i in item]
            cache[idx] = result
            return result
    if isinstance(item, dict):
        result = {}
        for key, val_idx in item.items():
            result[key] = deref(data, val_idx, depth + 1, max_depth, cache) if isinstance(val_idx, int) else val_idx
        cache[idx] = result
        return result
    return item


def fetch_leaderboard_page(page, platform='console', mode='ranked', stat='rankPoints', retries=5):
    url = f'https://stats.cc/siege/leaderboards/{platform}/{mode}/{stat}?page={page}'
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                print(f"  [!] Page {page}: HTTP {r.status_code} (attempt {attempt+1}/{retries})")
                if r.status_code == 429:
                    wait = min((attempt + 1) * 15, 90)
                    print(f"  [!] Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                elif r.status_code >= 500:
                    time.sleep((attempt + 1) * 5)
                    continue
                return None
            
            json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if not json_blocks:
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return None
            
            nuxt_data = json.loads(json_blocks[0])
            root_idx = 3
            if root_idx >= len(nuxt_data):
                return None
            root = nuxt_data[root_idx]
            
            lb_index = None
            if isinstance(root, dict):
                for key, val in root.items():
                    if 'leaderboard' in key.lower():
                        lb_index = val
                        break
            
            if lb_index is None:
                return None
            
            lb_data = deref(nuxt_data, lb_index, max_depth=25)
            
            if not isinstance(lb_data, dict) or 'profiles' not in lb_data:
                return None
            
            if len(lb_data.get('profiles', [])) == 0:
                print(f"  [END] Page {page}: Empty page - reached end of leaderboard")
                return 'END'
            
            return lb_data
            
        except Exception as e:
            print(f"  [!] Page {page}: Error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None


def extract_player_data(lb_data, platform_tag):
    players = []
    for entry in lb_data.get('profiles', []):
        profile = entry.get('profile', {})
        seasonal = profile.get('seasonalRecords', {})
        ranked_data = {}
        for season_name, season_data in seasonal.items():
            if isinstance(season_data, dict) and 'ranked' in season_data:
                ranked_data = season_data['ranked']
                break
        
        player = {
            'displayName': profile.get('displayName', ''),
            'profileId': profile.get('profileId', ''),
            'platform': profile.get('platform', platform_tag),
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
            'source': f'{platform_tag}_leaderboard',
        }
        players.append(player)
    return players


def main():
    parser = argparse.ArgumentParser(description='Fetch extra R6 Siege leaderboards from stats.cc')
    parser.add_argument('--platform', type=str, default='console', choices=['console', 'global'], help='Platform')
    parser.add_argument('--all', action='store_true', help='Fetch all pages')
    parser.add_argument('--pages', type=int, default=100, help='Number of pages (default: 100)')
    parser.add_argument('--resume', action='store_true', help='Resume from last page')
    parser.add_argument('--delay', type=float, default=3.0, help='Base delay')
    parser.add_argument('--max-pages', type=int, default=200, help='Safety limit')
    args = parser.parse_args()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    platform = args.platform
    out_file = os.path.join(OUTPUT_DIR, f'leaderboard_{platform}.json')
    progress_file = os.path.join(OUTPUT_DIR, f'_lb_{platform}_progress.json')
    
    # 加载已有 PC 排行榜的 profileId 用于去重统计
    pc_ids = set()
    if os.path.exists(PC_LB_FILE):
        with open(PC_LB_FILE, 'r', encoding='utf-8') as f:
            pc_data = json.load(f)
        pc_ids = set(p['profileId'] for p in pc_data if p.get('profileId'))
        print(f"[INFO] PC leaderboard: {len(pc_ids)} known players")
    
    # 加载已有数据
    existing_players = []
    seen_ids = set()
    last_page = 0
    
    if os.path.exists(out_file):
        with open(out_file, 'r', encoding='utf-8') as f:
            existing_players = json.load(f)
        seen_ids = set(p['profileId'] for p in existing_players if p.get('profileId'))
        print(f"[LOAD] Existing {platform} data: {len(existing_players)} players")
    
    if args.resume and os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            prog = json.load(f)
        last_page = prog.get('last_page_fetched', 0)
        print(f"[RESUME] From page {last_page + 1}")
    
    start_page = last_page + 1 if args.resume and last_page > 0 else 1
    end_page = start_page + (args.max_pages if args.all else args.pages) - 1
    
    print("=" * 70)
    print(f"R6 Siege Leaderboard Fetcher - {platform.upper()}")
    print("=" * 70)
    print(f"Pages: {start_page} to {end_page}")
    print(f"Delay: {args.delay}s")
    print()
    
    all_players = list(existing_players)
    new_total = 0
    new_non_pc = 0
    failed_pages = []
    consecutive_fails = 0
    
    for page in range(start_page, end_page + 1):
        print(f"[Page {page}] Fetching {platform} leaderboard...")
        
        lb_data = fetch_leaderboard_page(page, platform=platform)
        
        if lb_data == 'END':
            print(f"\n[END] Reached end at page {page}")
            break
        
        if lb_data is None:
            failed_pages.append(page)
            consecutive_fails += 1
            if consecutive_fails >= 10:
                print(f"\n[STOP] Too many consecutive failures")
                break
            if consecutive_fails >= 3:
                time.sleep(min(consecutive_fails * 30, 120))
            time.sleep(args.delay)
            continue
        
        consecutive_fails = 0
        players = extract_player_data(lb_data, platform)
        
        if not players:
            continue
        
        new_count = 0
        non_pc_count = 0
        for p in players:
            pid = p.get('profileId', '')
            if pid and pid not in seen_ids:
                all_players.append(p)
                seen_ids.add(pid)
                new_count += 1
                if pid not in pc_ids:
                    non_pc_count += 1
        
        new_total += new_count
        new_non_pc += non_pc_count
        
        first = players[0]
        last_p = players[-1]
        print(f"  [OK] {len(players)} players (+{new_count} new, {non_pc_count} not in PC LB)")
        print(f"       RP range: {last_p.get('rankPoints',0)}-{first.get('rankPoints',0)}")
        print(f"       Total unique: {len(seen_ids)}")
        
        # 保存进度
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                'last_page_fetched': page,
                'total_players': len(all_players),
                'unique_players': len(seen_ids),
                'new_non_pc': new_non_pc,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        if page % 5 == 0:
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(all_players, f, ensure_ascii=False, indent=2)
            print(f"  [SAVE] Checkpoint: {len(all_players)} players")
        
        delay = args.delay + random.uniform(0.5, 2.0)
        if page % 20 == 0:
            delay += random.uniform(3, 8)
        time.sleep(delay)
    
    # 最终保存
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS - {platform.upper()} Leaderboard")
    print(f"{'=' * 70}")
    print(f"New players: {new_total}")
    print(f"New (not in PC LB): {new_non_pc}")
    print(f"Total: {len(all_players)}")
    print(f"Failed pages: {len(failed_pages)}")
    print(f"Saved: {out_file}")
    
    # 生成合并的额外玩家列表（去除 PC 排行榜已有的）
    extra_players = [p for p in all_players if p['profileId'] not in pc_ids]
    extra_file = os.path.join(OUTPUT_DIR, f'extra_players_{platform}.json')
    with open(extra_file, 'w', encoding='utf-8') as f:
        json.dump(extra_players, f, ensure_ascii=False, indent=2)
    print(f"Extra players (not in PC LB): {len(extra_players)}")
    print(f"Saved extra: {extra_file}")


if __name__ == '__main__':
    main()

"""
排行榜全量采集 - 分批运行避免超时
每批爬取一组页面，保存后输出进度
"""
import requests
import re
import sys
import io
import json
import os
import time
import random
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.stdout.reconfigure(line_buffering=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://stats.cc/siege/leaderboards/pc/ranked/rankPoints',
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'leaderboard')
FULL_PATH = os.path.join(OUTPUT_DIR, 'leaderboard_full.json')
PROGRESS_PATH = os.path.join(OUTPUT_DIR, '_lb_progress.json')


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
        result = {k: deref(data, v, depth+1, max_depth, cache) if isinstance(v, int) else v for k, v in item.items()}
        cache[idx] = result
        return result
    return item


def fetch_page(page, retries=5):
    url = f'https://stats.cc/siege/leaderboards/pc/ranked/rankPoints?page={page}'
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = min((attempt + 1) * 20, 120)
                print(f"    429 rate-limited, wait {wait}s...", flush=True)
                time.sleep(wait)
                continue
            if r.status_code == 403:
                wait = (attempt + 1) * 25
                print(f"    403 forbidden, wait {wait}s...", flush=True)
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                time.sleep((attempt + 1) * 5)
                continue
            if r.status_code != 200:
                return None

            json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if not json_blocks:
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return None

            nuxt_data = json.loads(json_blocks[0])
            if 3 >= len(nuxt_data):
                return None
            root = nuxt_data[3]
            if not isinstance(root, dict):
                return None

            lb_index = None
            for key, val in root.items():
                if 'leaderboard' in key.lower():
                    lb_index = val
                    break
            if lb_index is None:
                return None

            lb_data = deref(nuxt_data, lb_index)
            if not isinstance(lb_data, dict) or 'profiles' not in lb_data:
                return None
            if len(lb_data['profiles']) == 0:
                return 'END'
            return lb_data

        except requests.exceptions.Timeout:
            print(f"    Timeout attempt {attempt+1}", flush=True)
            time.sleep(10)
        except Exception as e:
            print(f"    Error: {e}", flush=True)
            time.sleep(5)
    return None


def extract_players(lb_data):
    players = []
    for entry in lb_data.get('profiles', []):
        profile = entry.get('profile', {})
        seasonal = profile.get('seasonalRecords', {})
        ranked_data = {}
        for sn, sd in seasonal.items():
            if isinstance(sd, dict) and 'ranked' in sd:
                ranked_data = sd['ranked']
                break
        kills = ranked_data.get('kills', 0)
        deaths = ranked_data.get('deaths', 0)
        wins = ranked_data.get('wins', 0)
        losses = ranked_data.get('losses', 0)
        players.append({
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
            'kills': kills, 'deaths': deaths,
            'wins': wins, 'losses': losses,
            'abandons': ranked_data.get('abandons', 0),
            'kd': round(kills / max(deaths, 1), 3),
            'winRate': round(wins / max(wins + losses, 1) * 100, 2),
        })
    return players


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0, help='Start page (0=auto from progress)')
    parser.add_argument('--batch', type=int, default=20, help='Pages per batch')
    parser.add_argument('--max-page', type=int, default=200, help='Max page to fetch')
    parser.add_argument('--delay', type=float, default=3.0, help='Base delay')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load existing
    all_players = []
    seen_ids = set()
    if os.path.exists(FULL_PATH):
        with open(FULL_PATH, 'r', encoding='utf-8') as f:
            all_players = json.load(f)
        seen_ids = set(p['profileId'] for p in all_players if p.get('profileId'))

    last_page = 0
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, 'r') as f:
            last_page = json.load(f).get('last_page', 0)

    start = args.start if args.start > 0 else max(last_page + 1, 1)
    end = min(start + args.batch - 1, args.max_page)

    print(f"=== Leaderboard Fetch: pages {start}-{end} | existing: {len(all_players)} ({len(seen_ids)} unique) ===", flush=True)

    new_added = 0
    failed = []
    consec_fail = 0

    for page in range(start, end + 1):
        result = fetch_page(page)

        if result == 'END':
            print(f"  p{page}: END of leaderboard", flush=True)
            # Save final progress with reached_end flag
            with open(PROGRESS_PATH, 'w') as f:
                json.dump({'last_page': page, 'total': len(all_players), 'unique': len(seen_ids),
                           'reached_end': True, 'ts': datetime.now().isoformat()}, f, indent=2)
            break

        if result is None:
            failed.append(page)
            consec_fail += 1
            print(f"  p{page}: FAIL (consec={consec_fail})", flush=True)
            if consec_fail >= 8:
                print(f"  Too many fails, stopping batch", flush=True)
                break
            time.sleep(args.delay + random.uniform(1, 3))
            continue

        consec_fail = 0
        players = extract_players(result)
        nc = 0
        for p in players:
            pid = p.get('profileId', '')
            if pid and pid not in seen_ids:
                all_players.append(p)
                seen_ids.add(pid)
                nc += 1
        new_added += nc

        rp_range = f"{players[-1]['rankPoints']}-{players[0]['rankPoints']}" if players else "?"
        ranks = set(p['rank'] for p in players)
        print(f"  p{page}: +{nc} new | total={len(seen_ids)} | RP={rp_range} | ranks={','.join(sorted(ranks))}", flush=True)

        # Save progress
        with open(PROGRESS_PATH, 'w') as f:
            json.dump({'last_page': page, 'total': len(all_players), 'unique': len(seen_ids),
                       'ts': datetime.now().isoformat()}, f, indent=2)

        # Checkpoint every 5 pages
        if page % 5 == 0 or page == end:
            with open(FULL_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_players, f, ensure_ascii=False, indent=2)

        delay = args.delay + random.uniform(0.5, 2.5)
        if page % 15 == 0:
            delay += random.uniform(3, 8)
        time.sleep(delay)

    # Final save
    with open(FULL_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)

    # Save names file
    names_data = [{'name': p['displayName'], 'profileId': p['profileId'], 'rank': p['rank'],
                   'rankPoints': p['rankPoints'], 'position': p['leaderboardPosition']} for p in all_players]
    with open(os.path.join(OUTPUT_DIR, 'player_names.json'), 'w', encoding='utf-8') as f:
        json.dump(names_data, f, ensure_ascii=False, indent=2)

    # Rank distribution
    rank_counts = {}
    for p in all_players:
        r = p.get('rank', 'unknown')
        rank_counts[r] = rank_counts.get(r, 0) + 1

    print(f"\n=== BATCH DONE: pages {start}-{end} ===", flush=True)
    print(f"New: +{new_added} | Total: {len(all_players)} ({len(seen_ids)} unique) | Failed: {len(failed)}", flush=True)
    print(f"Rank distribution:", flush=True)
    for rank, count in sorted(rank_counts.items(), key=lambda x: -x[1]):
        pct = count / len(all_players) * 100
        print(f"  {rank:20s}: {count:6d} ({pct:5.1f}%)", flush=True)

    if failed:
        print(f"Failed pages: {failed}", flush=True)

    # Check if reached end
    progress = {}
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, 'r') as f:
            progress = json.load(f)
    if not progress.get('reached_end'):
        next_start = end + 1
        print(f"\nNext batch: python run_full_leaderboard.py --start {next_start} --batch {args.batch}", flush=True)
    else:
        print(f"\n🏁 Leaderboard fully fetched!", flush=True)


if __name__ == '__main__':
    main()

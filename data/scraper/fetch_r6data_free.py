"""
从 r6data.eu 前端 API 获取彩虹六号围攻数据（无需 API Key）

发现 r6data.eu 的前端网站直接暴露了完整的 API 端点，无需认证即可访问。
这些端点与 api.r6data.eu 的功能相同，但不需要 api-key header。

用法:
  python fetch_r6data_free.py --player 玩家名 [--platform uplay] [--metadata] [--output-dir ./output]
"""
import requests
import json
import argparse
import os
import sys
import io
import time

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ========== 配置 ==========
BASE_URL = "https://r6data.eu"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://r6data.eu/',
}


def fetch_json(endpoint, params=None, retries=3):
    """从 r6data.eu 前端 API 获取 JSON 数据"""
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                wait = (attempt + 1) * 5
                print(f"  [!] Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  [!] HTTP {r.status_code} for {endpoint}: {r.text[:200]}")
                return None
        except Exception as e:
            print(f"  [!] Error fetching {endpoint}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def save_json(data, filepath):
    """保存 JSON 数据到文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Saved: {filepath} ({os.path.getsize(filepath)} bytes)")


def fetch_metadata(output_dir):
    """获取游戏元数据（干员、地图、武器、赛季、段位）"""
    print("\n" + "="*60)
    print("Fetching game metadata...")
    print("="*60)
    
    metadata_endpoints = {
        'operators': '/api/operators',
        'maps': '/api/maps',
        'weapons': '/api/weapons',
        'seasons': '/api/seasons',
        'ranks_v6': '/api/ranks?version=v6',
    }
    
    results = {}
    for name, endpoint in metadata_endpoints.items():
        print(f"\n[*] Fetching {name}...")
        data = fetch_json(endpoint)
        if data:
            filepath = os.path.join(output_dir, f"{name}.json")
            save_json(data, filepath)
            results[name] = data
            count = len(data) if isinstance(data, list) else 'N/A'
            print(f"  Items: {count}")
        else:
            print(f"  [FAIL] Could not fetch {name}")
        time.sleep(0.5)  # 礼貌性延迟
    
    return results


def fetch_player_account(player_name, platform, output_dir):
    """获取玩家账户信息"""
    print(f"\n[*] Fetching account info for: {player_name} ({platform})...")
    data = fetch_json('/api/stats', params={
        'type': 'accountInfo',
        'nameOnPlatform': player_name,
        'platformType': platform,
    })
    if data:
        filepath = os.path.join(output_dir, f"player_{player_name}_account.json")
        save_json(data, filepath)
        level = data.get('level', 'N/A')
        print(f"  Level: {level}")
    return data


def fetch_player_ranked(player_name, platform, output_dir):
    """获取玩家排位数据"""
    print(f"\n[*] Fetching ranked stats for: {player_name} ({platform})...")
    data = fetch_json('/api/stats', params={
        'type': 'stats',
        'nameOnPlatform': player_name,
        'platformType': platform,
        'platform_families': 'pc',
    })
    if data:
        filepath = os.path.join(output_dir, f"player_{player_name}_ranked.json")
        save_json(data, filepath)
    return data


def fetch_player_operator_stats(player_name, platform, output_dir, season=None, mode='ranked'):
    """获取玩家干员统计数据"""
    print(f"\n[*] Fetching operator stats for: {player_name} ({platform})...")
    params = {
        'type': 'operatorStats',
        'nameOnPlatform': player_name,
        'platformType': platform,
    }
    if season:
        params['seasonYear'] = season
    if mode:
        params['modes'] = mode
    
    data = fetch_json('/api/stats', params=params)
    if data:
        suffix = f"_{season}" if season else ""
        suffix += f"_{mode}" if mode else ""
        filepath = os.path.join(output_dir, f"player_{player_name}_operators{suffix}.json")
        save_json(data, filepath)
        
        # 打印干员统计摘要
        if isinstance(data, dict) and 'operators' in data:
            ops = data['operators']
            if isinstance(ops, list):
                print(f"  Operators with data: {len(ops)}")
                # 按击杀数排序前5
                sorted_ops = sorted(ops, key=lambda x: x.get('kills', 0), reverse=True)
                print(f"  Top 5 by kills:")
                for op in sorted_ops[:5]:
                    name = op.get('operatorName', op.get('name', 'Unknown'))
                    kills = op.get('kills', 0)
                    deaths = op.get('deaths', 0)
                    kd = kills / deaths if deaths > 0 else kills
                    print(f"    {name}: {kills} kills, {deaths} deaths, KD={kd:.2f}")
    return data


def fetch_player_seasonal_stats(player_name, platform, output_dir):
    """获取玩家赛季排位历史"""
    print(f"\n[*] Fetching seasonal stats for: {player_name} ({platform})...")
    data = fetch_json('/api/stats', params={
        'type': 'seasonalStats',
        'nameOnPlatform': player_name,
        'platformType': platform,
    })
    if data:
        filepath = os.path.join(output_dir, f"player_{player_name}_seasonal.json")
        save_json(data, filepath)
    return data


def fetch_player_ban_status(player_name, platform, output_dir):
    """检查玩家是否被封禁"""
    print(f"\n[*] Checking ban status for: {player_name}...")
    data = fetch_json(f'/api/isBanned/{player_name}', params={
        'platformType': platform,
    })
    if data:
        filepath = os.path.join(output_dir, f"player_{player_name}_ban.json")
        save_json(data, filepath)
        is_banned = data.get('isBanned', False)
        print(f"  Banned: {is_banned}")
    return data


def fetch_player_rank_history(player_name, platform, output_dir):
    """获取玩家段位积分历史"""
    print(f"\n[*] Fetching rank points history for: {player_name}...")
    data = fetch_json(f'/api/rankPointsHistory/{player_name}', params={
        'platformType': platform,
    })
    if data:
        filepath = os.path.join(output_dir, f"player_{player_name}_rank_history.json")
        save_json(data, filepath)
    return data


def main():
    parser = argparse.ArgumentParser(description='Fetch R6 Siege data from r6data.eu (free, no API key)')
    parser.add_argument('--player', '-p', type=str, help='Player name to look up')
    parser.add_argument('--platform', type=str, default='uplay', 
                        choices=['uplay', 'psn', 'xbl', 'steam'],
                        help='Platform (default: uplay)')
    parser.add_argument('--metadata', '-m', action='store_true', 
                        help='Fetch game metadata (operators, maps, weapons, seasons)')
    parser.add_argument('--season', '-s', type=str, default=None,
                        help='Season code for operator stats (e.g., Y10S4). Default: latest')
    parser.add_argument('--mode', type=str, default='ranked',
                        choices=['ranked', 'casual', 'unranked'],
                        help='Game mode for operator stats (default: ranked)')
    parser.add_argument('--output-dir', '-o', type=str, default='./output',
                        help='Output directory (default: ./output)')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Fetch all available data for the player')
    
    args = parser.parse_args()
    
    if not args.player and not args.metadata:
        parser.print_help()
        print("\nExample:")
        print("  python fetch_r6data_free.py --player Beaulo --metadata")
        print("  python fetch_r6data_free.py --player Beaulo --all")
        return
    
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*60)
    print("R6 Data Fetcher (r6data.eu - Free, No API Key)")
    print("="*60)
    print(f"Output: {output_dir}")
    
    # 1. 获取元数据
    if args.metadata:
        fetch_metadata(output_dir)
    
    # 2. 获取玩家数据
    if args.player:
        print(f"\n{'='*60}")
        print(f"Fetching data for player: {args.player} ({args.platform})")
        print(f"{'='*60}")
        
        # 账户信息
        fetch_player_account(args.player, args.platform, output_dir)
        time.sleep(0.5)
        
        # 排位数据
        fetch_player_ranked(args.player, args.platform, output_dir)
        time.sleep(0.5)
        
        # 干员统计
        fetch_player_operator_stats(args.player, args.platform, output_dir, 
                                    season=args.season, mode=args.mode)
        time.sleep(0.5)
        
        if args.all:
            # 赛季历史
            fetch_player_seasonal_stats(args.player, args.platform, output_dir)
            time.sleep(0.5)
            
            # 封禁状态
            fetch_player_ban_status(args.player, args.platform, output_dir)
            time.sleep(0.5)
            
            # 段位积分历史
            fetch_player_rank_history(args.player, args.platform, output_dir)
    
    print(f"\n{'='*60}")
    print("Done! All data saved to:", output_dir)
    print("="*60)


if __name__ == '__main__':
    main()

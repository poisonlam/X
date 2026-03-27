"""
测试 tracker.gg R6 API - 验证对局记录中是否包含每回合干员选择数据
"""
import requests
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://r6.tracker.network',
    'Referer': 'https://r6.tracker.network/',
}

# Test 1: 获取玩家比赛历史
print("=" * 70)
print("Test 1: Fetch match history from tracker.gg API")
print("=" * 70)

# 排行榜第1名: exolt2turNt
players_to_test = [
    ('Beaulo', 'uplay'),
]

for player_name, platform in players_to_test:
    print(f"\n--- Player: {player_name} ({platform}) ---")
    
    url = f'https://api.tracker.gg/api/v2/r6siege/standard/matches/{platform}/{player_name}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        print(f"HTTP {r.status_code}, {len(r.text)} bytes")
        
        if r.status_code == 200:
            data = r.json()
            
            # 保存完整数据
            with open('data/scraper/output/trackergg_matches_sample.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved full response")
            
            # 分析结构
            print(f"\nTop-level keys: {list(data.keys())}")
            
            matches_data = data.get('data', {})
            if isinstance(matches_data, dict):
                print(f"data keys: {list(matches_data.keys())}")
                matches = matches_data.get('matches', [])
            elif isinstance(matches_data, list):
                matches = matches_data
            else:
                matches = []
            
            print(f"\nTotal matches: {len(matches)}")
            
            if matches:
                # 分析第一场比赛
                first = matches[0]
                print(f"\n{'='*50}")
                print(f"FIRST MATCH DETAILED ANALYSIS:")
                print(f"{'='*50}")
                print(f"Match keys: {list(first.keys())}")
                
                # attributes
                attrs = first.get('attributes', {})
                print(f"\nAttributes: {json.dumps(attrs, ensure_ascii=False, indent=2)[:500]}")
                
                # metadata
                meta = first.get('metadata', {})
                print(f"\nMetadata keys: {list(meta.keys())}")
                print(f"  Map: {meta.get('sessionMapName', 'N/A')}")
                print(f"  Mode: {meta.get('sessionModeName', 'N/A')}")
                print(f"  Playlist: {meta.get('sessionPlaylistName', 'N/A')}")
                print(f"  Result: {meta.get('result', 'N/A')}")
                print(f"  hasRounds: {meta.get('hasRounds', 'N/A')}")
                
                # segments
                segments = first.get('segments', [])
                print(f"\nSegments count: {len(segments)}")
                
                for seg_idx, seg in enumerate(segments):
                    print(f"\n  Segment {seg_idx}:")
                    print(f"    type: {seg.get('type', 'N/A')}")
                    seg_meta = seg.get('metadata', {})
                    print(f"    metadata keys: {list(seg_meta.keys())[:20]}")
                    
                    # 干员列表
                    operators = seg_meta.get('operators', [])
                    if operators:
                        print(f"    OPERATORS: {len(operators)}")
                        for op in operators[:5]:
                            if isinstance(op, dict):
                                print(f"      - {op.get('name', 'N/A')} (img: {op.get('imageUrl', 'N/A')[:50]}...)")
                            else:
                                print(f"      - {op}")
                    
                    # 回合详情
                    rounds = seg_meta.get('rounds', [])
                    if rounds:
                        print(f"    ROUNDS: {len(rounds)}")
                        for rd in rounds[:10]:
                            if isinstance(rd, dict):
                                print(f"      Rd {rd.get('round', '?')}: {rd.get('outcome', '?')} | "
                                      f"Op: {rd.get('operatorName', 'N/A')} ({rd.get('operatorSide', 'N/A')}) | "
                                      f"Reason: {rd.get('endReasonName', 'N/A')}")
                    
                    # 统计数据
                    stats = seg.get('stats', {})
                    if stats:
                        stat_keys = list(stats.keys())
                        print(f"    Stats keys ({len(stat_keys)}): {stat_keys[:20]}")
                        for key in ['kills', 'deaths', 'assists', 'kdRatio', 'roundsWon', 'roundsLost', 'roundsPlayed']:
                            if key in stats:
                                val = stats[key]
                                if isinstance(val, dict):
                                    print(f"      {key}: {val.get('value', val.get('displayValue', 'N/A'))}")
                                else:
                                    print(f"      {key}: {val}")
                
                # 汇总所有比赛的地图和干员
                print(f"\n{'='*50}")
                print(f"SUMMARY OF ALL {len(matches)} MATCHES:")
                print(f"{'='*50}")
                
                maps_seen = {}
                operators_seen = {}
                total_rounds_with_operator = 0
                
                for m in matches:
                    meta = m.get('metadata', {})
                    map_name = meta.get('sessionMapName', 'Unknown')
                    result = meta.get('result', 'Unknown')
                    maps_seen[map_name] = maps_seen.get(map_name, 0) + 1
                    
                    for seg in m.get('segments', []):
                        seg_meta = seg.get('metadata', {})
                        for rd in seg_meta.get('rounds', []):
                            op_name = rd.get('operatorName', 'Unknown')
                            operators_seen[op_name] = operators_seen.get(op_name, 0) + 1
                            total_rounds_with_operator += 1
                
                print(f"\nMaps played:")
                for m, c in sorted(maps_seen.items(), key=lambda x: -x[1]):
                    print(f"  {m}: {c} matches")
                
                print(f"\nOperators used (top 15):")
                for op, c in sorted(operators_seen.items(), key=lambda x: -x[1])[:15]:
                    print(f"  {op}: {c} rounds")
                
                print(f"\nTotal rounds with operator data: {total_rounds_with_operator}")
                
        elif r.status_code == 451:
            print(f"Response (451): {r.text[:500]}")
        else:
            print(f"Response: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

# Test 2: 检查是否能获取更多比赛（分页）
print(f"\n\n{'='*70}")
print("Test 2: Check pagination / more matches")
print("="*70)

# 看看是否有 next 参数
url2 = f'https://api.tracker.gg/api/v2/r6siege/standard/matches/uplay/Beaulo?page=2'
try:
    r2 = requests.get(url2, headers=HEADERS, timeout=30)
    print(f"Page 2: HTTP {r2.status_code}, {len(r2.text)} bytes")
    if r2.status_code == 200:
        data2 = r2.json()
        matches2 = data2.get('data', {}).get('matches', [])
        print(f"  Matches on page 2: {len(matches2)}")
        if matches2:
            meta2 = matches2[0].get('metadata', {})
            print(f"  First match map: {meta2.get('sessionMapName')}")
except Exception as e:
    print(f"  Error: {e}")

# 也试试 sessionType 参数
url3 = f'https://api.tracker.gg/api/v2/r6siege/standard/matches/uplay/Beaulo?sessionType=ranked'
try:
    r3 = requests.get(url3, headers=HEADERS, timeout=30)
    print(f"\nRanked only: HTTP {r3.status_code}, {len(r3.text)} bytes")
    if r3.status_code == 200:
        data3 = r3.json()
        matches3 = data3.get('data', {}).get('matches', [])
        print(f"  Ranked matches: {len(matches3)}")
except Exception as e:
    print(f"  Error: {e}")

# Test 3: 检查玩家概览数据（包含段位）
print(f"\n\n{'='*70}")
print("Test 3: Player profile (with rank info)")
print("="*70)

url4 = f'https://api.tracker.gg/api/v2/r6siege/standard/profile/uplay/Beaulo'
try:
    r4 = requests.get(url4, headers=HEADERS, timeout=30)
    print(f"Profile: HTTP {r4.status_code}, {len(r4.text)} bytes")
    if r4.status_code == 200:
        data4 = r4.json()
        # 保存
        with open('data/scraper/output/trackergg_profile_sample.json', 'w', encoding='utf-8') as f:
            json.dump(data4, f, ensure_ascii=False, indent=2)
        print("  Saved profile data")
        
        # 看看段位信息在哪
        segments = data4.get('data', {}).get('segments', [])
        for seg in segments[:5]:
            seg_type = seg.get('type', '')
            seg_meta = seg.get('metadata', {})
            print(f"  Segment: {seg_type}, meta keys: {list(seg_meta.keys())[:10]}")
            if 'rankName' in seg_meta or 'rank' in seg_meta:
                print(f"    RANK: {seg_meta.get('rankName', seg_meta.get('rank', 'N/A'))}")
except Exception as e:
    print(f"  Error: {e}")

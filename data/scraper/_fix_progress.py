"""修复进度文件 - 从实际数据文件中重建 completed_players 和 completed_matches"""
import json, os, sys

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'match_data')

print("=" * 70)
print("检查并修复 shard 进度文件")
print("=" * 70)

for i in range(5):
    data_file = os.path.join(base, f'shard_{i}', 'match_details.json')
    progress_file = os.path.join(base, f'_shard_{i}_progress.json')
    
    if not os.path.exists(data_file):
        print(f"\nShard {i}: 无数据文件")
        continue
    
    # 从数据文件中提取所有 match IDs 和 source players
    with open(data_file, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    
    data_match_ids = set()
    data_player_ids = set()
    
    for m in matches:
        mid = m.get('match_id')
        if mid:
            data_match_ids.add(mid)
        # source_player 是发起采集这个 match 的玩家
        sp = m.get('source_player', {})
        if isinstance(sp, dict) and sp.get('profileId'):
            data_player_ids.add(sp['profileId'])
        # 也从 profiles 中收集
        profiles = m.get('profiles', [])
        if isinstance(profiles, list):
            for p in profiles:
                if isinstance(p, dict) and p.get('id'):
                    pass  # profiles 中的不一定是"已完成"的玩家
    
    # 读取当前进度文件
    progress_players = set()
    progress_matches = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        progress_players = set(progress.get('completed_players', []))
        progress_matches = set(progress.get('completed_matches', []))
    
    print(f"\nShard {i}:")
    print(f"  数据文件: {len(matches)} matches, {len(data_match_ids)} unique match IDs, {len(data_player_ids)} source players")
    print(f"  进度文件: {len(progress_players)} players, {len(progress_matches)} matches")
    
    # 检查是否需要修复
    needs_fix = False
    if len(progress_players) < len(data_player_ids):
        print(f"  [!] 进度文件少了 {len(data_player_ids) - len(progress_players)} 个 source players!")
        needs_fix = True
    if len(progress_matches) < len(data_match_ids):
        print(f"  [!] 进度文件少了 {len(data_match_ids) - len(progress_matches)} 个 match IDs!")
        needs_fix = True
    
    if needs_fix:
        # 合并: 取并集，不丢失任何进度
        merged_players = progress_players | data_player_ids
        merged_matches = progress_matches | data_match_ids
        
        print(f"  -> 修复后: {len(merged_players)} players, {len(merged_matches)} matches")
        
        from datetime import datetime
        new_progress = {
            'shard_id': i,
            'completed_players': list(merged_players),
            'completed_matches': list(merged_matches),
            'last_updated': datetime.now().isoformat(),
            'version': 'v2',
            'stats': {
                'total_players_done': len(merged_players),
                'total_matches_done': len(merged_matches),
            }
        }
        
        tmp = progress_file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(new_progress, f, ensure_ascii=False, indent=2)
        os.replace(tmp, progress_file)
        print(f"  [OK] 已修复!")
    else:
        print(f"  [OK] 进度一致，无需修复")

print(f"\n{'='*70}")
print("修复完成！")

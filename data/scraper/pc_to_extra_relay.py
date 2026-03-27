"""
PC → Extra 自动接力脚本
========================
监控PC分片进程，当PC分片完成后，自动启动新的Extra分片来利用释放的资源。

方案：
- 现有 8 个 Extra 分片（shard 0-7, total-shards=8）继续运行
- PC完成后，我们 **不增加Extra分片数**（因为分片是取模分配的，改变total-shards会打乱分配）
- 而是直接以更低的delay重启已有的8个Extra分片
  （它们会从断点续传，之前的进度不丢失）
- 同时，PC分片完成后不再占用请求配额，Extra可以更激进

但更好的方案是：
- 保持8个Extra分片不变
- 当PC完成后，额外启动 **5个补充Extra进程**
  这些补充进程使用 **独立的分片编号系统**（shard 0-4, total-shards=5）
  指向一个单独的进度文件和数据目录 (output/extra_match_data_boost/)
  它们采集的是被现有8个分片跳过的（因为分片取模不同）
  
最终采用方案：
- 当所有5个PC分片全部完成后
- 杀掉已有的8个Extra进程（它们现在有bug被修复了，需要重启）
- 以16个分片重新启动Extra采集（分片数翻倍，ETA减半）
- 16个分片会自动跳过已完成的玩家（progress文件断点续传）
  
  ⚠️ 分片数变更的风险：
  - 旧8分片中 shard_i 的 completed_players 是按 `i % 8 == shard_id` 分配的
  - 新16分片中 shard_j 的分配是 `j % 16 == shard_id`
  - 只要progress文件中的completed_players包含profile_id，不管分片分配怎么变，
    已完成的玩家都会被跳过（因为是全局过滤）
  - 但旧分片的match_details.json需要合并到新分片中
  
  实际上看代码，`cmd_run` 加载进度时：
    remaining = [p for p in all_extra_players if p['profileId'] not in shard_completed]
  这里 shard_completed 只加载了**本分片**的进度文件！
  所以换分片数后，新分片不知道旧分片已经处理了哪些玩家。
  
  解决方案：我们需要合并所有旧分片的进度，然后为新分片创建初始进度文件。

用法:
  python pc_to_extra_relay.py check     # 检查PC是否全部完成
  python pc_to_extra_relay.py migrate    # 迁移Extra进度到新分片数
  python pc_to_extra_relay.py launch     # 启动新的Extra分片进程
"""
import json
import os
import sys
import subprocess
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PC_MATCH_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
EXTRA_MATCH_DIR = os.path.join(BASE_DIR, 'output', 'extra_match_data')
EXTRA_PLAYERS_FILE = os.path.join(EXTRA_MATCH_DIR, '_extra_players.json')

OLD_TOTAL_SHARDS = 8
NEW_TOTAL_SHARDS = 16


def check_pc_complete():
    """检查所有PC分片是否已完成"""
    # 加载排行榜
    lb_file = os.path.join(BASE_DIR, 'output', 'leaderboard', 'leaderboard_full.json')
    if not os.path.exists(lb_file):
        print("[ERROR] Leaderboard file not found")
        return False
    
    with open(lb_file, 'r', encoding='utf-8') as f:
        all_players = json.load(f)
    
    total_players = len(all_players)
    
    # 收集所有PC分片的已完成玩家
    all_completed = set()
    for shard_id in range(20):  # 检查所有可能的分片
        pf = os.path.join(PC_MATCH_DIR, f'_shard_{shard_id}_progress.json')
        if os.path.exists(pf):
            with open(pf, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            all_completed.update(sp.get('completed_players', []))
    
    # 也检查全局进度
    gp_file = os.path.join(PC_MATCH_DIR, '_progress.json')
    if os.path.exists(gp_file):
        with open(gp_file, 'r', encoding='utf-8') as f:
            gp = json.load(f)
        all_completed.update(gp.get('completed_players', []))
    
    remaining = [p for p in all_players if p['profileId'] not in all_completed]
    pct = (1 - len(remaining) / total_players) * 100
    
    print(f"PC Progress: {len(all_completed)}/{total_players} ({pct:.1f}%)")
    print(f"Remaining: {len(remaining)} players")
    
    if len(remaining) == 0:
        print("\n✓ PC collection is COMPLETE!")
        return True
    else:
        # 估算剩余时间
        # PC速度约 62 players/hour/shard * 5 shards = 310/hour
        eta_hours = len(remaining) / 310
        print(f"\nPC NOT complete yet. ETA: ~{eta_hours:.1f} hours")
        return False


def migrate_extra_progress():
    """
    将旧的8分片进度迁移到16分片系统。
    
    策略：
    1. 收集所有旧分片的 completed_players 和 completed_matches
    2. 加载完整的 extra_players 列表
    3. 按新的16分片取模分配
    4. 为每个新分片创建 progress 文件，只包含属于该分片的已完成玩家
    5. 合并旧分片的 match_details.json 到新分片
    """
    print("=" * 70)
    print("迁移 Extra 进度: 8分片 → 16分片")
    print("=" * 70)
    
    # Step 1: 收集所有旧分片数据
    all_completed_players = set()
    all_completed_matches = set()
    all_match_details = []
    seen_match_ids = set()
    
    for sid in range(OLD_TOTAL_SHARDS):
        pf = os.path.join(EXTRA_MATCH_DIR, f'_shard_{sid}_progress.json')
        if os.path.exists(pf):
            with open(pf, 'r', encoding='utf-8') as f:
                sp = json.load(f)
            old_cp = sp.get('completed_players', [])
            old_cm = sp.get('completed_matches', [])
            all_completed_players.update(old_cp)
            all_completed_matches.update(old_cm)
            print(f"  Old shard {sid}: {len(old_cp)} players, {len(old_cm)} matches")
        
        # 加载比赛数据
        df = os.path.join(EXTRA_MATCH_DIR, f'shard_{sid}', 'match_details.json')
        if os.path.exists(df):
            with open(df, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for d in data:
                mid = d.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_match_details.append(d)
                    seen_match_ids.add(mid)
    
    print(f"\n  Total old: {len(all_completed_players)} players, {len(all_completed_matches)} matches")
    print(f"  Total match details: {len(all_match_details)} (deduped)")
    
    # Step 2: 加载 extra players 列表
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        all_extra_players = json.load(f)
    
    # Step 3: 获取剩余玩家，按新分片分配
    remaining = [p for p in all_extra_players if p['profileId'] not in all_completed_players]
    print(f"\n  Total extra players: {len(all_extra_players)}")
    print(f"  Already completed: {len(all_completed_players)}")
    print(f"  Remaining: {len(remaining)}")
    
    # Step 4: 备份旧进度文件
    backup_dir = os.path.join(EXTRA_MATCH_DIR, '_backup_8shard')
    os.makedirs(backup_dir, exist_ok=True)
    for sid in range(OLD_TOTAL_SHARDS):
        for pattern in [f'_shard_{sid}_progress.json']:
            src = os.path.join(EXTRA_MATCH_DIR, pattern)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, pattern)
                import shutil
                shutil.copy2(src, dst)
    print(f"\n  Backed up old progress to {backup_dir}")
    
    # Step 5: 为每个新分片创建进度文件
    # 已完成的玩家不需要重新分配到特定分片——因为 cmd_run 中的过滤逻辑是：
    #   remaining = [p for p in all_extra_players if p['profileId'] not in shard_completed]
    #   shard_players = [p for i, p in enumerate(remaining) if i % total_shards == shard_id]
    # 这里 shard_completed 只从本分片的progress加载。
    # 
    # 为了让新分片知道哪些玩家已完成，我们需要把 ALL completed_players 写入 EVERY 新分片的 progress。
    # 这样每个新分片启动时，remaining 列表就正确排除了所有已完成的玩家。
    
    for new_sid in range(NEW_TOTAL_SHARDS):
        new_progress = {
            'shard_id': new_sid,
            'completed_players': list(all_completed_players),
            'completed_matches': list(all_completed_matches),
            'last_updated': datetime.now().isoformat(),
            'stats': {
                'total_players_done': len(all_completed_players),
                'total_matches_done': len(all_completed_matches),
            },
            '_migration_note': f'Migrated from {OLD_TOTAL_SHARDS} to {NEW_TOTAL_SHARDS} shards'
        }
        
        pf = os.path.join(EXTRA_MATCH_DIR, f'_shard_{new_sid}_progress.json')
        with open(pf, 'w', encoding='utf-8') as f:
            json.dump(new_progress, f, ensure_ascii=False, indent=2)
        
        # 创建新分片目录（如果需要）
        shard_dir = os.path.join(EXTRA_MATCH_DIR, f'shard_{new_sid}')
        os.makedirs(shard_dir, exist_ok=True)
        
        # 计算该分片将处理多少玩家
        shard_count = len([p for i, p in enumerate(remaining) if i % NEW_TOTAL_SHARDS == new_sid])
        print(f"  New shard {new_sid}: {shard_count} players to process")
    
    # Step 6: 将已有的 match_details 保存到 shard_0（简单合并）
    # 旧分片的数据不需要按新分片重分配，因为数据是按 match_id 去重的
    # 新分片采集时会通过 load_all_known_match_ids 避免重复
    merged_file = os.path.join(EXTRA_MATCH_DIR, 'all_extra_match_details.json')
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(all_match_details, f, ensure_ascii=False)
    
    print(f"\n  Merged all match details to {merged_file}")
    print(f"\n{'=' * 70}")
    print(f"迁移完成! 新分片数: {NEW_TOTAL_SHARDS}")
    print(f"每个分片约处理 {len(remaining) // NEW_TOTAL_SHARDS} 个玩家")
    eta_hours = len(remaining) / (78 * NEW_TOTAL_SHARDS)  # 78 players/hour/shard
    print(f"预估总时间: ~{eta_hours:.1f} 小时 ({eta_hours/24:.1f} 天)")
    print(f"{'=' * 70}")
    return True


def launch_extra_shards(total_shards=NEW_TOTAL_SHARDS, delay=1.0):
    """启动所有Extra分片进程"""
    print(f"启动 {total_shards} 个 Extra 分片进程 (delay={delay}s)")
    
    script_path = os.path.join(BASE_DIR, 'extract_and_collect_extra_players.py')
    
    for sid in range(total_shards):
        stdout_log = os.path.join(EXTRA_MATCH_DIR, f'shard_{sid}_stdout.log')
        stderr_log = os.path.join(EXTRA_MATCH_DIR, f'shard_{sid}_stderr.log')
        
        cmd = [
            sys.executable,
            script_path,
            'run',
            '--shard-id', str(sid),
            '--total-shards', str(total_shards),
            '--delay', str(delay),
        ]
        
        proc = subprocess.Popen(
            cmd,
            stdout=open(stdout_log, 'w', encoding='utf-8'),
            stderr=open(stderr_log, 'w', encoding='utf-8'),
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        print(f"  Shard {sid}: PID {proc.pid}")
        time.sleep(0.5)  # 稍微错开启动
    
    print(f"\n全部 {total_shards} 个分片已启动!")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python pc_to_extra_relay.py check    - 检查PC是否完成")
        print("  python pc_to_extra_relay.py migrate   - 迁移Extra进度到新分片数")
        print("  python pc_to_extra_relay.py launch    - 启动新的Extra分片进程")
        print("  python pc_to_extra_relay.py auto      - 自动执行: 检查→迁移→启动")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'check':
        check_pc_complete()
    elif cmd == 'migrate':
        migrate_extra_progress()
    elif cmd == 'launch':
        total = int(sys.argv[2]) if len(sys.argv) > 2 else NEW_TOTAL_SHARDS
        delay = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        launch_extra_shards(total, delay)
    elif cmd == 'auto':
        # 自动模式
        pc_done = check_pc_complete()
        if not pc_done:
            print("\nPC未完成，暂不迁移。")
            print("你可以手动执行 migrate + launch 来提前扩展Extra分片数。")
            return
        
        print("\n" + "=" * 70)
        print("PC已完成！开始迁移和启动...")
        print("=" * 70 + "\n")
        
        migrate_extra_progress()
        print()
        launch_extra_shards()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == '__main__':
    main()

"""
数据备份脚本
============
将当前所有采集数据备份到带时间戳的目录中，
然后清除进度文件以便重新从头采集。

备份内容：
- output/match_data/        → backup_YYYYMMDD_HHMMSS/match_data/
- output/extra_match_data/  → backup_YYYYMMDD_HHMMSS/extra_match_data/
- output/leaderboard/       → backup_YYYYMMDD_HHMMSS/leaderboard/

用法:
  python backup_data.py                 # 备份数据
  python backup_data.py --clean-progress # 备份并清除进度（准备重新采集）
"""
import os
import sys
import io
import json
import shutil
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

DIRS_TO_BACKUP = [
    'match_data',
    'extra_match_data',
    'leaderboard',
]


def get_dir_size(path):
    """计算目录总大小"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def backup(clean_progress=False):
    """执行备份"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(OUTPUT_DIR, f'backup_{timestamp}')
    
    print("=" * 70)
    print(f"R6 数据备份")
    print("=" * 70)
    print(f"备份目录: {backup_dir}")
    print()
    
    # 检查要备份的内容
    total_size = 0
    dirs_exist = []
    for d in DIRS_TO_BACKUP:
        src = os.path.join(OUTPUT_DIR, d)
        if os.path.exists(src):
            size = get_dir_size(src)
            total_size += size
            dirs_exist.append((d, size))
            print(f"  {d}: {format_size(size)}")
        else:
            print(f"  {d}: 不存在，跳过")
    
    if not dirs_exist:
        print("\n没有需要备份的数据。")
        return
    
    print(f"\n总计: {format_size(total_size)}")
    print()
    
    # 执行备份（复制而非移动，保留原始数据）
    os.makedirs(backup_dir, exist_ok=True)
    
    for d, size in dirs_exist:
        src = os.path.join(OUTPUT_DIR, d)
        dst = os.path.join(backup_dir, d)
        print(f"  备份 {d}... ", end='', flush=True)
        shutil.copytree(src, dst)
        print(f"OK ({format_size(size)})")
    
    # 保存备份元数据
    meta = {
        'backup_time': datetime.now().isoformat(),
        'dirs': {d: {'size_bytes': s, 'size_human': format_size(s)} for d, s in dirs_exist},
        'total_size_bytes': total_size,
        'total_size_human': format_size(total_size),
        'clean_progress': clean_progress,
    }
    with open(os.path.join(backup_dir, '_backup_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    print(f"\n备份完成: {backup_dir}")
    
    # 清除进度文件（为重新采集做准备）
    if clean_progress:
        print(f"\n清除进度文件（准备重新采集）...")
        progress_patterns = [
            os.path.join(OUTPUT_DIR, 'match_data', '_shard_*_progress.json'),
            os.path.join(OUTPUT_DIR, 'match_data', '_progress.json'),
            os.path.join(OUTPUT_DIR, 'match_data', '_shared_match_ids.json'),
            os.path.join(OUTPUT_DIR, 'match_data', '_anomaly_players.json'),
            os.path.join(OUTPUT_DIR, 'extra_match_data', '_shard_*_progress.json'),
            os.path.join(OUTPUT_DIR, 'extra_match_data', '_anomaly_players.json'),
            os.path.join(OUTPUT_DIR, 'extra_match_data', '_extra_players.json'),
        ]
        
        import glob
        cleaned = 0
        for pattern in progress_patterns:
            for fp in glob.glob(pattern):
                os.remove(fp)
                print(f"  删除: {os.path.relpath(fp, BASE_DIR)}")
                cleaned += 1
        
        # 清除分片数据目录中的 match_details.json（但保留目录结构）
        shard_patterns = [
            os.path.join(OUTPUT_DIR, 'match_data', 'shard_*', 'match_details.json'),
            os.path.join(OUTPUT_DIR, 'extra_match_data', 'shard_*', 'match_details.json'),
        ]
        for pattern in shard_patterns:
            for fp in glob.glob(pattern):
                os.remove(fp)
                print(f"  删除: {os.path.relpath(fp, BASE_DIR)}")
                cleaned += 1
        
        print(f"\n已清除 {cleaned} 个文件。可以从头开始采集了。")
    
    return backup_dir


if __name__ == '__main__':
    clean = '--clean-progress' in sys.argv
    backup(clean_progress=clean)

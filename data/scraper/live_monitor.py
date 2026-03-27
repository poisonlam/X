"""
R6 数据采集实时监控面板
========================
每10秒扫描一次进度文件，有新数据立即显示。
直接在CMD窗口运行，实时可见。

用法: python live_monitor.py
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 强制 stdout 不缓冲
sys.stdout.reconfigure(line_buffering=True)

SCRAPER_DIR = Path(__file__).parent
PC_DIR = SCRAPER_DIR / "output" / "match_data"
EXTRA_DIR = SCRAPER_DIR / "output" / "extra_match_data"

# ANSI颜色（Windows 10+ CMD支持）
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[90m"


def enable_ansi():
    """启用Windows CMD的ANSI颜色支持"""
    if os.name == 'nt':
        os.system('')  # 简单trick激活ANSI


def read_progress(filepath):
    """读取进度文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def get_all_progress():
    """获取所有分片的进度快照"""
    snapshot = {
        'pc': {},
        'extra': {},
        'timestamp': datetime.now()
    }
    
    # PC 分片
    for i in range(10):  # 最多10个分片
        pf = PC_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            data = read_progress(pf)
            if data:
                snapshot['pc'][i] = {
                    'players': len(data.get('completed_players', [])),
                    'matches': len(data.get('completed_matches', [])),
                    'failed': len(data.get('failed_players', [])),
                    'last_updated': data.get('last_updated', ''),
                    'file_mtime': datetime.fromtimestamp(pf.stat().st_mtime)
                }
    
    # Extra 分片
    for i in range(20):  # 最多20个分片
        pf = EXTRA_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            data = read_progress(pf)
            if data:
                snapshot['extra'][i] = {
                    'players': len(data.get('completed_players', [])),
                    'matches': len(data.get('completed_matches', [])),
                    'failed': len(data.get('failed_players', [])),
                    'last_updated': data.get('last_updated', ''),
                    'file_mtime': datetime.fromtimestamp(pf.stat().st_mtime)
                }
    
    return snapshot


def print_header():
    """打印监控面板头部"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║       R6 Siege 数据采集实时监控面板                         ║{RESET}")
    print(f"{BOLD}{CYAN}║       按 Ctrl+C 退出                                       ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()


def format_time_ago(dt):
    """格式化为 '多久前' """
    if not dt:
        return "未知"
    diff = datetime.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}秒前"
    elif seconds < 3600:
        return f"{int(seconds/60)}分钟前"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}小时前"
    else:
        return f"{seconds/86400:.1f}天前"


def print_status(current, previous):
    """打印当前状态和增量变化"""
    now = datetime.now().strftime("%H:%M:%S")
    
    # PC 汇总
    pc_total_players = sum(s['players'] for s in current['pc'].values())
    pc_total_matches = sum(s['matches'] for s in current['pc'].values())
    pc_total_failed = sum(s['failed'] for s in current['pc'].values())
    
    pc_prev_players = sum(s['players'] for s in previous['pc'].values()) if previous else 0
    pc_prev_matches = sum(s['matches'] for s in previous['pc'].values()) if previous else 0
    
    pc_new_players = pc_total_players - pc_prev_players
    pc_new_matches = pc_total_matches - pc_prev_matches
    
    # Extra 汇总
    extra_total_players = sum(s['players'] for s in current['extra'].values())
    extra_total_matches = sum(s['matches'] for s in current['extra'].values())
    extra_total_failed = sum(s['failed'] for s in current['extra'].values())
    
    extra_prev_players = sum(s['players'] for s in previous['extra'].values()) if previous else 0
    extra_prev_matches = sum(s['matches'] for s in previous['extra'].values()) if previous else 0
    
    extra_new_players = extra_total_players - extra_prev_players
    extra_new_matches = extra_total_matches - extra_prev_matches
    
    total_new = pc_new_players + extra_new_players + pc_new_matches + extra_new_matches
    
    # 获取最近更新时间
    pc_latest_mtime = max((s['file_mtime'] for s in current['pc'].values()), default=None)
    extra_latest_mtime = max((s['file_mtime'] for s in current['extra'].values()), default=None)
    
    # 只在有变化时显示详细增量，否则显示简洁状态
    if total_new > 0:
        # 有新数据！高亮显示
        print(f"\n{BOLD}{GREEN}{'='*62}{RESET}")
        print(f"{BOLD}{GREEN}  🟢 [{now}] 新数据到达！{RESET}")
        print(f"{GREEN}{'='*62}{RESET}")
        
        if pc_new_players > 0 or pc_new_matches > 0:
            print(f"  {GREEN}📊 PC: +{pc_new_players} 玩家, +{pc_new_matches} 对局{RESET}")
            # 显示哪个分片有新增
            for sid, sdata in sorted(current['pc'].items()):
                if previous and sid in previous['pc']:
                    dp = sdata['players'] - previous['pc'][sid]['players']
                    dm = sdata['matches'] - previous['pc'][sid]['matches']
                    if dp > 0 or dm > 0:
                        print(f"    {DIM}└─ Shard {sid}: +{dp}玩家 +{dm}对局{RESET}")
        
        if extra_new_players > 0 or extra_new_matches > 0:
            print(f"  {GREEN}📊 Extra: +{extra_new_players} 玩家, +{extra_new_matches} 对局{RESET}")
            for sid, sdata in sorted(current['extra'].items()):
                if previous and sid in previous['extra']:
                    dp = sdata['players'] - previous['extra'][sid]['players']
                    dm = sdata['matches'] - previous['extra'][sid]['matches']
                    if dp > 0 or dm > 0:
                        print(f"    {DIM}└─ Shard {sid}: +{dp}玩家 +{dm}对局{RESET}")
        
        print()
    
    # 始终打印概览行
    pc_status_color = GREEN if pc_new_players > 0 else (YELLOW if pc_latest_mtime and (datetime.now() - pc_latest_mtime).total_seconds() < 300 else RED)
    extra_status_color = GREEN if extra_new_players > 0 else (YELLOW if extra_latest_mtime and (datetime.now() - extra_latest_mtime).total_seconds() < 300 else RED)
    
    pc_pct = pc_total_players / 9915 * 100 if 9915 > 0 else 0
    extra_pct = extra_total_players / 63199 * 100 if 63199 > 0 else 0
    
    # 进度条
    def bar(pct, width=20):
        filled = int(pct / 100 * width)
        return f"{'█' * filled}{'░' * (width - filled)}"
    
    print(f"  {DIM}[{now}]{RESET} "
          f"{pc_status_color}PC:{RESET} {pc_total_players}/9915 ({pc_pct:.1f}%) {bar(pc_pct)} "
          f"更新:{format_time_ago(pc_latest_mtime)}")
    print(f"  {DIM}       {RESET} "
          f"{extra_status_color}EX:{RESET} {extra_total_players}/63199 ({extra_pct:.1f}%) {bar(extra_pct)} "
          f"更新:{format_time_ago(extra_latest_mtime)}")
    
    # 如果超过5分钟没更新，发出警告
    warning_shown = False
    if pc_latest_mtime and (datetime.now() - pc_latest_mtime).total_seconds() > 300:
        if not warning_shown:
            print()
        print(f"  {RED}⚠️  PC 进度已 {format_time_ago(pc_latest_mtime)} 未更新！可能卡住了{RESET}")
        warning_shown = True
    
    if extra_latest_mtime and (datetime.now() - extra_latest_mtime).total_seconds() > 300:
        if not warning_shown:
            print()
        print(f"  {RED}⚠️  Extra 进度已 {format_time_ago(extra_latest_mtime)} 未更新！可能卡住了{RESET}")
        warning_shown = True
    
    sys.stdout.flush()


def main():
    enable_ansi()
    print_header()
    
    print(f"  {CYAN}正在初始化监控...{RESET}")
    print(f"  {DIM}每 10 秒检查一次进度文件变化{RESET}")
    print(f"  {DIM}有新数据时会立即显示增量{RESET}")
    print()
    
    previous = None
    cycle = 0
    hourly_baseline = None
    hourly_reset_time = datetime.now()
    
    try:
        while True:
            current = get_all_progress()
            
            if cycle == 0:
                # 首次打印完整状态
                print(f"{BOLD}  ── 当前状态 ──{RESET}")
                
                pc_total = sum(s['players'] for s in current['pc'].values())
                pc_matches = sum(s['matches'] for s in current['pc'].values())
                extra_total = sum(s['players'] for s in current['extra'].values())
                extra_matches = sum(s['matches'] for s in current['extra'].values())
                
                print(f"  PC:    {GREEN}{pc_total}{RESET}/9915 玩家, {pc_matches} 对局 ({len(current['pc'])}个分片)")
                print(f"  Extra: {GREEN}{extra_total}{RESET}/63199 玩家, {extra_matches} 对局 ({len(current['extra'])}个分片)")
                print(f"  总计:  {BOLD}{pc_total + extra_total}{RESET} 玩家, {pc_matches + extra_matches} 对局")
                print()
                print(f"{DIM}  ── 开始监控 (10秒/次) ──{RESET}")
                
                hourly_baseline = current
                hourly_reset_time = datetime.now()
            else:
                print_status(current, previous)
            
            # 每小时汇总
            if (datetime.now() - hourly_reset_time).total_seconds() >= 3600:
                if hourly_baseline:
                    pc_hr = sum(s['players'] for s in current['pc'].values()) - sum(s['players'] for s in hourly_baseline['pc'].values())
                    extra_hr = sum(s['players'] for s in current['extra'].values()) - sum(s['players'] for s in hourly_baseline['extra'].values())
                    print(f"\n{BOLD}{CYAN}  ── 过去1小时汇总 ──{RESET}")
                    print(f"  {CYAN}PC: +{pc_hr} 玩家 | Extra: +{extra_hr} 玩家 | 合计: +{pc_hr + extra_hr}{RESET}")
                    if pc_hr + extra_hr == 0:
                        print(f"  {RED}⚠️  1小时零增长！采集可能全部卡住！{RESET}")
                    print()
                hourly_baseline = current
                hourly_reset_time = datetime.now()
            
            previous = current
            cycle += 1
            time.sleep(10)
            
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}  监控已停止。{RESET}")
        sys.exit(0)


if __name__ == '__main__':
    main()

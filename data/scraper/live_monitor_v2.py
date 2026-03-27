"""
R6 数据采集实时监控面板 v2 (事件驱动)
======================================
改进:
- 不再每10秒轮询，改为监控事件日志文件变化
- 只在有事件时更新显示
- 显示关键信息: 是否找到对局、是否进入Session审查
- 色彩编码的状态指示

用法: python live_monitor_v2.py
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
else:
    sys.stdout.reconfigure(line_buffering=True)

SCRAPER_DIR = Path(__file__).parent
PC_DIR = SCRAPER_DIR / "output" / "match_data"
EXTRA_DIR = SCRAPER_DIR / "output" / "extra_match_data"
PC_EVENTS_DIR = PC_DIR / "_events"
EXTRA_EVENTS_DIR = EXTRA_DIR / "_events"

# ANSI 颜色
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[90m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"


def enable_ansi():
    if os.name == 'nt':
        os.system('')


def read_json_safe(filepath):
    """读取JSON文件，带重试和容错"""
    for attempt in range(3):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, ValueError):
            # 可能正好在写入中，短暂等待后重试
            time.sleep(0.05)
        except Exception:
            return None
    return None


# 缓存上一次成功读取的进度，避免读写竞争导致跳变
_progress_cache = {'pc': {}, 'extra': {}}


def read_last_events(event_file, max_lines=20):
    """读取事件文件的最新N条"""
    events = []
    try:
        with open(event_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines[-max_lines:]:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except:
                    pass
    except:
        pass
    return events


def format_time_ago(iso_str):
    if not iso_str:
        return "未知"
    try:
        dt = datetime.fromisoformat(iso_str)
        diff = datetime.now() - dt
        secs = diff.total_seconds()
        if secs < 60:
            return f"{int(secs)}秒前"
        elif secs < 3600:
            return f"{int(secs/60)}分钟前"
        elif secs < 86400:
            return f"{secs/3600:.1f}小时前"
        else:
            return f"{secs/86400:.1f}天前"
    except:
        return "未知"


def get_event_icon(event_type):
    icons = {
        'match_found': f'{GREEN}✓ 找到对局{RESET}',
        'match_not_found': f'{DIM}· 无对局{RESET}',
        'session_review_start': f'{BG_YELLOW}{WHITE} SESSION REVIEW 开始 {RESET}',
        'session_review_end': f'{YELLOW}◆ Session审查完成{RESET}',
        'session_rebuild': f'{RED}⟳ Session 重建{RESET}',
        'gap_detected': f'{YELLOW}△ 数据缺口{RESET}',
        'gap_filled': f'{GREEN}▲ 缺口修复{RESET}',
        'format_change': f'{BG_RED}{WHITE} ⚠ 数据格式变化! {RESET}',
        'player_done': f'{DIM}→ 玩家完成{RESET}',
        'shard_start': f'{CYAN}▶ 分片启动{RESET}',
        'shard_done': f'{GREEN}■ 分片完成{RESET}',
        'error': f'{RED}✗ 错误{RESET}',
    }
    return icons.get(event_type, f'{DIM}? {event_type}{RESET}')


def format_event(event):
    """格式化单条事件为显示字符串"""
    ts = event.get('timestamp', '')
    etype = event.get('type', 'unknown')
    data = event.get('data', {})
    shard = event.get('shard_id', '?')
    source = event.get('source', 'pc')
    
    # 时间部分
    try:
        dt = datetime.fromisoformat(ts)
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = ts[:8] if len(ts) >= 8 else ts
    
    prefix = f"Ex{shard}" if source == 'extra' else f"S{shard}"
    icon = get_event_icon(etype)
    
    # 详细信息
    detail = ''
    if etype == 'match_found':
        map_name = data.get('map', '?')
        players = data.get('players', '?')
        rounds = data.get('rounds', '?')
        source_player = data.get('source_player', '?')
        detail = f" [{map_name}] {players}p/{rounds}r <- {source_player}"
    elif etype == 'match_not_found':
        player = data.get('player', '?')
        ce = data.get('consecutive_empty', 0)
        detail = f" {player}"
        if ce >= 3:
            detail += f" {YELLOW}(连续空{ce}){RESET}"
    elif etype == 'session_review_start':
        ce = data.get('consecutive_empty', 0)
        cerr = data.get('consecutive_errors', 0)
        rc = data.get('review_count', 0)
        detail = f" 第{rc}次审查 (空:{ce}, 错:{cerr})"
    elif etype == 'session_review_end':
        result = data.get('result', '?')
        result_color = GREEN if 'ok' in result else YELLOW if 'backtrack' in result else RED
        detail = f" 结果: {result_color}{result}{RESET}"
    elif etype == 'session_rebuild':
        count = data.get('rebuild_count', 0)
        detail = f" 第{count}次重建"
    elif etype == 'player_done':
        player = data.get('player', '?')
        nm = data.get('new_matches', 0)
        detail = f" {player} (+{nm}场)"
    elif etype == 'shard_start':
        total = data.get('total_players', 0)
        remaining = data.get('remaining', 0)
        detail = f" 待处理: {remaining}/{total}"
    elif etype == 'shard_done':
        pd = data.get('players_done', 0)
        md = data.get('matches_done', 0)
        sr = data.get('session_reviews', 0)
        detail = f" 玩家:{pd} 对局:{md} 审查:{sr}次"
    elif etype == 'format_change':
        detail = f" {RED}{data}{RESET}"
    
    return f"  {DIM}{time_str}{RESET} [{prefix}] {icon}{detail}"


def get_progress_summary():
    """获取进度摘要（带缓存容错，避免读写竞争导致跳变）"""
    global _progress_cache
    summary = {'pc': {}, 'extra': {}}
    
    for i in range(10):
        pf = PC_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            data = read_json_safe(pf)
            if data and 'completed_players' in data:
                entry = {
                    'players': len(data.get('completed_players', [])),
                    'matches': len(data.get('completed_matches', [])),
                    'last_updated': data.get('last_updated', ''),
                    'version': data.get('version', 'v1'),
                }
                summary['pc'][i] = entry
                _progress_cache['pc'][i] = entry  # 更新缓存
            elif i in _progress_cache['pc']:
                # 读取失败，使用缓存值
                summary['pc'][i] = _progress_cache['pc'][i]
    
    for i in range(20):
        pf = EXTRA_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            data = read_json_safe(pf)
            if data and 'completed_players' in data:
                entry = {
                    'players': len(data.get('completed_players', [])),
                    'matches': len(data.get('completed_matches', [])),
                    'last_updated': data.get('last_updated', ''),
                    'version': data.get('version', 'v1'),
                }
                summary['extra'][i] = entry
                _progress_cache['extra'][i] = entry  # 更新缓存
            elif i in _progress_cache['extra']:
                # 读取失败，使用缓存值
                summary['extra'][i] = _progress_cache['extra'][i]
    
    return summary


def get_session_review_status():
    """检查是否有分片正在进行 Session 审查"""
    in_review = []
    
    for events_dir in [PC_EVENTS_DIR, EXTRA_EVENTS_DIR]:
        if not events_dir.exists():
            continue
        for sf in events_dir.glob('*_status.json'):
            data = read_json_safe(sf)
            if data and data.get('last_event') == 'session_review_start':
                in_review.append(data)
    
    return in_review


def collect_recent_events(max_per_shard=5):
    """收集所有分片的最新事件"""
    all_events = []
    
    for events_dir in [PC_EVENTS_DIR, EXTRA_EVENTS_DIR]:
        if not events_dir.exists():
            continue
        for ef in sorted(events_dir.glob('*_events.jsonl')):
            events = read_last_events(ef, max_lines=max_per_shard)
            all_events.extend(events)
    
    # 按时间排序
    all_events.sort(key=lambda e: e.get('timestamp', ''))
    return all_events


def print_dashboard(previous_event_count):
    """打印监控面板"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 清屏
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║     R6 Siege 数据采集监控 v2 (事件驱动)                         ║{RESET}")
    print(f"{BOLD}{CYAN}║     更新时间: {now}                                ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    
    # === 进度概览 ===
    summary = get_progress_summary()
    
    pc_players = sum(s['players'] for s in summary['pc'].values())
    pc_matches = sum(s['matches'] for s in summary['pc'].values())
    ex_players = sum(s['players'] for s in summary['extra'].values())
    ex_matches = sum(s['matches'] for s in summary['extra'].values())
    
    # 尝试读取总数
    lb_file = SCRAPER_DIR / "output" / "leaderboard" / "leaderboard_full.json"
    lb_total = 10015
    if lb_file.exists():
        try:
            with open(lb_file, 'r', encoding='utf-8') as f:
                lb_total = len(json.load(f))
        except:
            pass
    
    ex_file = EXTRA_DIR / "_extra_players.json"
    ex_total = 63199
    if ex_file.exists():
        try:
            with open(ex_file, 'r', encoding='utf-8') as f:
                ex_total = len(json.load(f))
        except:
            pass
    
    pc_pct = pc_players / max(lb_total, 1) * 100
    ex_pct = ex_players / max(ex_total, 1) * 100
    
    def bar(pct, w=25):
        filled = int(pct / 100 * w)
        return f"{'█' * filled}{'░' * (w - filled)}"
    
    print(f"\n  {BOLD}── 进度 ──{RESET}")
    print(f"  PC:    {GREEN}{pc_players:>6}{RESET}/{lb_total} 玩家 ({pc_pct:>5.1f}%) {bar(pc_pct)}  {pc_matches} 对局")
    print(f"  Extra: {GREEN}{ex_players:>6}{RESET}/{ex_total} 玩家 ({ex_pct:>5.1f}%) {bar(ex_pct)}  {ex_matches} 对局")
    print(f"  合计:  {BOLD}{pc_players + ex_players}{RESET} 玩家, {pc_matches + ex_matches} 对局")
    
    # 活跃分片
    active_pc = []
    for sid, s in summary['pc'].items():
        if s['last_updated']:
            try:
                dt = datetime.fromisoformat(s['last_updated'])
                if (datetime.now() - dt).total_seconds() < 300:
                    active_pc.append(sid)
            except:
                pass
    
    active_ex = []
    for sid, s in summary['extra'].items():
        if s['last_updated']:
            try:
                dt = datetime.fromisoformat(s['last_updated'])
                if (datetime.now() - dt).total_seconds() < 300:
                    active_ex.append(sid)
            except:
                pass
    
    if active_pc or active_ex:
        print(f"\n  {GREEN}活跃分片:{RESET} ", end='')
        if active_pc:
            print(f"PC[{','.join(str(s) for s in active_pc)}] ", end='')
        if active_ex:
            print(f"Extra[{','.join(str(s) for s in active_ex)}]", end='')
        print()
    
    # === Session 审查状态 ===
    reviews = get_session_review_status()
    if reviews:
        print(f"\n  {BG_YELLOW}{WHITE} ⚠ SESSION REVIEW 进行中 {RESET}")
        for r in reviews:
            sid = r.get('shard_id', '?')
            t = format_time_ago(r.get('last_event_time'))
            print(f"    Shard {sid}: 开始于 {t}")
    
    # === 最新事件流 ===
    events = collect_recent_events(max_per_shard=10)
    
    # 只显示最近50条"有意义"的事件
    important_types = {
        'match_found', 'session_review_start', 'session_review_end',
        'session_rebuild', 'format_change', 'shard_start', 'shard_done',
        'gap_detected', 'gap_filled', 'error',
    }
    
    # 也显示 match_not_found 但只在连续空 >= 3 时
    filtered_events = []
    for e in events:
        etype = e.get('type', '')
        if etype in important_types:
            filtered_events.append(e)
        elif etype == 'match_not_found':
            ce = e.get('data', {}).get('consecutive_empty', 0)
            if ce >= 3:
                filtered_events.append(e)
        elif etype == 'player_done':
            nm = e.get('data', {}).get('new_matches', 0)
            if nm > 0:
                filtered_events.append(e)
    
    # 显示最新20条
    recent = filtered_events[-20:]
    
    print(f"\n  {BOLD}── 事件流 (最新 {len(recent)} 条) ──{RESET}")
    if not recent:
        print(f"  {DIM}暂无事件... 等待采集脚本启动{RESET}")
    else:
        for event in recent:
            print(format_event(event))
    
    # === 统计摘要 ===
    # 最近5分钟的事件统计
    now_dt = datetime.now()
    recent_5min = [e for e in events if _is_within_minutes(e, now_dt, 5)]
    
    matches_5min = len([e for e in recent_5min if e.get('type') == 'match_found'])
    players_5min = len([e for e in recent_5min if e.get('type') == 'player_done'])
    reviews_5min = len([e for e in recent_5min if e.get('type') == 'session_review_start'])
    
    print(f"\n  {BOLD}── 最近5分钟 ──{RESET}")
    print(f"  对局: {GREEN}+{matches_5min}{RESET} | 玩家: +{players_5min} | Session审查: {reviews_5min}")
    
    print(f"\n  {DIM}按 Ctrl+C 退出 | 事件发生时自动刷新 | 无事件时每30秒刷新{RESET}")
    
    return len(events)


def _is_within_minutes(event, now_dt, minutes):
    try:
        dt = datetime.fromisoformat(event.get('timestamp', ''))
        return (now_dt - dt).total_seconds() < minutes * 60
    except:
        return False


def get_total_event_file_size():
    """获取所有事件文件的总大小，用于检测变化"""
    total = 0
    for events_dir in [PC_EVENTS_DIR, EXTRA_EVENTS_DIR]:
        if events_dir.exists():
            for f in events_dir.iterdir():
                if f.is_file():
                    total += f.stat().st_size
    return total


def main():
    enable_ansi()
    
    print(f"  {CYAN}R6 监控面板 v2 启动中...{RESET}")
    print(f"  {DIM}监控事件目录: {PC_EVENTS_DIR}{RESET}")
    print(f"  {DIM}                {EXTRA_EVENTS_DIR}{RESET}")
    
    last_event_count = 0
    last_file_size = 0
    idle_count = 0
    
    try:
        while True:
            current_size = get_total_event_file_size()
            
            # 检测到新事件或定期刷新
            if current_size != last_file_size or idle_count >= 6:  # 每30秒强制刷新(6*5s)
                last_event_count = print_dashboard(last_event_count)
                last_file_size = current_size
                idle_count = 0
            else:
                idle_count += 1
            
            time.sleep(5)  # 每5秒检查一次文件变化（但只在变化时刷新UI）
            
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}  监控已停止。{RESET}")
        sys.exit(0)


if __name__ == '__main__':
    main()

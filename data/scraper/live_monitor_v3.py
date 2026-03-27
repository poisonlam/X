"""
R6 数据采集监控面板 v3 — 真实去重进度
====================================
核心改进:
- 显示全局去重后的真实进度(不再>100%)
- 显示每分钟采集速率
- 显示预估剩余时间
- 分别显示旧分片和v2分片状态

用法: python live_monitor_v3.py
"""
import json, os, sys, time, io
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
else:
    sys.stdout.reconfigure(line_buffering=True)

SCRAPER_DIR = Path(__file__).parent
PC_DIR = SCRAPER_DIR / "output" / "match_data"
EXTRA_DIR = SCRAPER_DIR / "output" / "extra_match_data"

# ANSI
G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; C = "\033[96m"
B = "\033[1m"; X = "\033[0m"; D = "\033[90m"; M = "\033[95m"; W = "\033[97m"

def enable_ansi():
    if os.name == 'nt': os.system('')

def rj(fp):
    for _ in range(3):
        try:
            with open(fp, 'r', encoding='utf-8') as f: return json.load(f)
        except: time.sleep(0.05)
    return None

def bar(pct, w=30):
    pct = min(pct, 100)
    filled = int(pct / 100 * w)
    return f"{'█' * filled}{'░' * (w - filled)}"

def time_ago(iso_str):
    if not iso_str: return "未知"
    try:
        dt = datetime.fromisoformat(iso_str)
        s = (datetime.now() - dt).total_seconds()
        if s < 60: return f"{int(s)}秒前"
        elif s < 3600: return f"{int(s/60)}分前"
        elif s < 86400: return f"{s/3600:.1f}h前"
        else: return f"{s/86400:.1f}d前"
    except: return "未知"

# 历史记录用于计算速率
_history = []

def print_dashboard():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"{B}{C}╔══════════════════════════════════════════════════════════════════════╗{X}")
    print(f"{B}{C}║     R6 Siege 数据采集监控 v3 (真实去重进度)                         ║{X}")
    print(f"{B}{C}║     {now}                                               ║{X}")
    print(f"{B}{C}╚══════════════════════════════════════════════════════════════════════╝{X}")
    
    # ===== 加载去重数据 =====
    # Extra总数 (对profileId去重，确保准确)
    ep_file = EXTRA_DIR / "_extra_players.json"
    ex_total = 112816
    if ep_file.exists():
        d = rj(ep_file)
        if d:
            ex_pids = set()
            for p in d:
                pid = p.get('profileId') if isinstance(p, dict) else p
                if pid:
                    ex_pids.add(pid)
            ex_total = len(ex_pids)
    
    # PC总数 (对排行榜profileId去重，排行榜分页可能有重复条目)
    lb_file = SCRAPER_DIR / "output" / "leaderboard" / "leaderboard_full.json"
    pc_total = 10015
    if lb_file.exists():
        d = rj(lb_file)
        if d:
            pc_pids = set()
            for p in d:
                pid = p.get('profileId') if isinstance(p, dict) else p
                if pid:
                    pc_pids.add(pid)
            pc_total = len(pc_pids)
    
    # 全局已完成Extra玩家 (去重)
    ex_done = set()
    # 全局文件
    gf = EXTRA_DIR / "_global_completed_players.json"
    if gf.exists():
        d = rj(gf)
        if d: ex_done.update(d)
    # 旧分片
    for i in range(20):
        pf = EXTRA_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            d = rj(pf)
            if d: ex_done.update(d.get('completed_players', []))
    # V2分片
    v2_active = []
    for i in range(20):
        pf = EXTRA_DIR / f"_v2_shard_{i}_progress.json"
        if pf.exists():
            d = rj(pf)
            if d:
                ex_done.update(d.get('completed_players', []))
                upd = d.get('last_updated', '')
                try:
                    dt = datetime.fromisoformat(upd)
                    if (datetime.now() - dt).total_seconds() < 300:
                        v2_active.append((i, d))
                except: pass
    
    # PC去重
    pc_done = set()
    pc_matches = set()
    for i in range(10):
        pf = PC_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            d = rj(pf)
            if d:
                pc_done.update(d.get('completed_players', []))
                pc_matches.update(d.get('completed_matches', []))
    
    # Extra matches去重
    ex_matches = set()
    for i in range(20):
        for pat in [f"_shard_{i}_progress.json", f"_v2_shard_{i}_progress.json"]:
            pf = EXTRA_DIR / pat
            if pf.exists():
                d = rj(pf)
                if d: ex_matches.update(d.get('completed_matches', []))
    
    all_matches = pc_matches | ex_matches
    
    ex_pct = len(ex_done) / max(ex_total, 1) * 100
    pc_pct = len(pc_done) / max(pc_total, 1) * 100
    ex_remain = ex_total - len(ex_done)
    
    # ===== 进度概览 =====
    print(f"\n  {B}── 真实进度 (全局去重) ──{X}")
    print(f"  PC:    {G}{len(pc_done):>6}{X}/{pc_total} 玩家 ({pc_pct:>5.1f}%) {bar(pc_pct)}  {len(pc_matches):>6} 对局")
    print(f"  Extra: {G}{len(ex_done):>6}{X}/{ex_total} 玩家 ({ex_pct:>5.1f}%) {bar(ex_pct)}  {len(ex_matches):>6} 对局")
    print(f"  合计:  {B}{len(pc_done)+len(ex_done)}{X} 玩家, {len(all_matches)} 唯一对局")
    print(f"  Extra剩余: {Y}{ex_remain}{X} 玩家")
    
    # ===== 速率计算 =====
    current_total = len(ex_done)
    _history.append((time.time(), current_total))
    # 保留最近10分钟的历史
    cutoff = time.time() - 600
    while _history and _history[0][0] < cutoff:
        _history.pop(0)
    
    rate_str = "计算中..."
    eta_str = "计算中..."
    if len(_history) >= 2:
        dt = _history[-1][0] - _history[0][0]
        dp = _history[-1][1] - _history[0][1]
        if dt > 30 and dp > 0:
            rate_per_min = dp / dt * 60
            rate_str = f"{rate_per_min:.1f} 玩家/分钟"
            if rate_per_min > 0:
                eta_hours = ex_remain / rate_per_min / 60
                if eta_hours < 1:
                    eta_str = f"{eta_hours*60:.0f} 分钟"
                else:
                    eta_str = f"{eta_hours:.1f} 小时"
        elif dp == 0:
            rate_str = "0 (暂停中)"
            eta_str = "N/A"
    
    print(f"\n  {B}── 采集速率 ──{X}")
    print(f"  速率: {G}{rate_str}{X}")
    print(f"  预估剩余: {Y}{eta_str}{X}")
    
    # ===== V2活跃分片 =====
    if v2_active:
        print(f"\n  {B}── V2活跃分片 ──{X}")
        for sid, d in v2_active:
            stats = d.get('stats', {})
            upd = time_ago(d.get('last_updated'))
            print(f"    V2-S{sid}: {G}{stats.get('total_players_done',0)}{X} players, "
                  f"{stats.get('total_matches_done',0)} matches, {upd}")
    else:
        print(f"\n  {D}  无V2活跃分片 (所有采集已停止){X}")
    
    # ===== 旧分片汇总 =====
    old_total_p = 0; old_total_m = 0
    for i in range(16):
        pf = EXTRA_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            d = rj(pf)
            if d:
                old_total_p += d.get('stats', {}).get('total_players_done', 0)
                old_total_m += d.get('stats', {}).get('total_matches_done', 0)
    
    print(f"\n  {B}── 旧16分片汇总 (含重复) ──{X}")
    print(f"  旧分片合计: {D}{old_total_p} players (含重复), {old_total_m} matches (每个分片相同){X}")
    print(f"  去重后贡献: {G}{len(ex_done) - sum(d.get('stats',{}).get('total_players_done',0) for _,d in v2_active)}{X} unique players")
    
    # ===== 数据文件大小 =====
    print(f"\n  {B}── 数据文件 ──{X}")
    total_size = 0
    # 旧分片 match_details.json
    for i in range(16):
        df = EXTRA_DIR / f"shard_{i}" / "match_details.json"
        if df.exists():
            sz = df.stat().st_size / 1024 / 1024
            total_size += sz
    print(f"  旧分片(0-7 有数据): {total_size:.1f} MB")
    
    # V2 JSONL
    v2_size = 0
    for i in range(20):
        jf = EXTRA_DIR / f"v2_shard_{i}" / "match_details.jsonl"
        if jf.exists():
            sz = jf.stat().st_size / 1024 / 1024
            v2_size += sz
            if sz > 0:
                print(f"  V2-S{i} JSONL: {sz:.1f} MB")
    if v2_size == 0:
        print(f"  {D}V2暂无数据文件{X}")
    
    # 合并文件
    mf = EXTRA_DIR / "all_extra_match_details.json"
    if mf.exists():
        print(f"  合并文件: {mf.stat().st_size / 1024 / 1024:.1f} MB")
    
    # PC数据
    pc_size = 0
    for i in range(10):
        df = PC_DIR / f"shard_{i}" / "match_details.json"
        if df.exists(): pc_size += df.stat().st_size / 1024 / 1024
    print(f"  PC数据: {pc_size:.1f} MB")
    
    print(f"\n  {D}按 Ctrl+C 退出 | 每10秒自动刷新{X}")

def main():
    enable_ansi()
    print(f"  {C}R6 监控面板 v3 启动中...{X}")
    try:
        while True:
            print_dashboard()
            time.sleep(10)
    except KeyboardInterrupt:
        print(f"\n\n{Y}  监控已停止。{X}")
        sys.exit(0)

if __name__ == '__main__':
    main()

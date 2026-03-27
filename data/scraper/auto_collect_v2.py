"""
自动监控 + 采集脚本 v2
=======================
功能：
1. 持续检测 stats.cc 是否可用
2. 可用后自动启动所有分片的采集（PC 5分片 + Extra 8分片）
3. 采集完成后自动执行查漏补缺
4. 写入事件日志供监控面板读取

用法:
  python auto_collect_v2.py                     # 完整流程
  python auto_collect_v2.py --skip-backup       # 跳过备份直接启动
  python auto_collect_v2.py --pc-shards 5 --ex-shards 8
"""
import subprocess
import sys
import os
import time
import datetime
import requests
import json
import signal
import threading

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRAPER_DIR, "auto_collect_v2.log")

# 采集参数
PC_SHARDS = 5
EXTRA_SHARDS = 8
DELAY = 1.0
CHECK_INTERVAL_DOWN = 120
CHECK_INTERVAL_UP = 30

TEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Encoding": "gzip, deflate"  # 不要br! requests不支持brotli解压
}

running = True
processes = []


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        # 移除emoji避免GBK问题
        import re
        safe_line = re.sub(r'[\U00010000-\U0010ffff]', '', line)
        print(safe_line, flush=True)
    except:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def check_server():
    """检测 stats.cc 是否可用"""
    try:
        s = requests.Session()
        s.headers.update(TEST_HEADERS)
        # 用已知的比赛页面测试
        r = s.get("https://stats.cc/siege/matches/3f4a671e-7fe1-4f35-a7e4-d99522109330", timeout=15)
        if r.status_code == 200:
            return True, f"OK (HTTP 200)"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


def start_shard(script, shard_id, total_shards, delay, label_prefix, extra_args=None):
    """启动一个分片采集进程"""
    cmd = [
        sys.executable, script,
        "run",
        "--shard-id", str(shard_id),
        "--total-shards", str(total_shards),
        "--delay", str(delay),
        "--health-threshold", "5",
    ]
    if extra_args:
        cmd.extend(extra_args)
    
    log_path = os.path.join(SCRAPER_DIR, f"{label_prefix}_{shard_id}.log")
    log(f"  Starting: {label_prefix} shard {shard_id}")
    
    proc = subprocess.Popen(
        cmd,
        cwd=SCRAPER_DIR,
        stdout=open(log_path, 'a', encoding='utf-8'),
        stderr=subprocess.STDOUT,
    )
    return proc


def start_all():
    """启动所有采集进程"""
    global processes
    processes = []
    
    log("=" * 60)
    log("启动所有 v2 采集进程...")
    log("=" * 60)
    
    # PC 排行榜
    for sid in range(PC_SHARDS):
        proc = start_shard("parallel_collect_v2.py", sid, PC_SHARDS, DELAY, "pc_shard",
                          ["--max-matches", "10"])
        processes.append({"proc": proc, "label": f"pc-{sid}"})
        time.sleep(1)
    
    # 额外玩家
    for sid in range(EXTRA_SHARDS):
        proc = start_shard("extra_collect_v2.py", sid, EXTRA_SHARDS, DELAY, "extra_shard",
                          ["--max-matches", "5"])
        processes.append({"proc": proc, "label": f"extra-{sid}"})
        time.sleep(1)
    
    log(f"已启动 {len(processes)} 个采集进程 (PC:{PC_SHARDS} + Extra:{EXTRA_SHARDS})")


def stop_all():
    global processes
    log("停止所有进程...")
    for p in processes:
        try:
            p["proc"].terminate()
            p["proc"].wait(timeout=10)
        except:
            try:
                p["proc"].kill()
            except:
                pass
    processes = []


def check_alive():
    alive = sum(1 for p in processes if p["proc"].poll() is None)
    finished = sum(1 for p in processes if p["proc"].poll() is not None)
    return alive, finished


def signal_handler(sig, frame):
    global running
    log("收到退出信号...")
    running = False
    stop_all()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    global running, PC_SHARDS, EXTRA_SHARDS
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-backup', action='store_true', help='跳过备份')
    parser.add_argument('--pc-shards', type=int, default=5)
    parser.add_argument('--ex-shards', type=int, default=8)
    args = parser.parse_args()
    
    PC_SHARDS = args.pc_shards
    EXTRA_SHARDS = args.ex_shards
    
    log("=" * 60)
    log("R6 数据采集 v2 - 自动监控与采集系统")
    log("=" * 60)
    log(f"PC 分片: {PC_SHARDS}, Extra 分片: {EXTRA_SHARDS}")
    
    # Step 1: 备份（可选）
    if not args.skip_backup:
        log("Step 1: 备份现有数据...")
        try:
            subprocess.run([sys.executable, "backup_data.py", "--clean-progress"],
                         cwd=SCRAPER_DIR, timeout=300)
        except:
            log("  备份跳过或失败")
    
    # Step 2: 构建映射表
    log("Step 2: 构建名称映射表...")
    try:
        subprocess.run([sys.executable, "id_mapping.py"],
                     cwd=SCRAPER_DIR, timeout=120)
    except:
        log("  映射表构建失败，继续...")
    
    # Step 3: 检测服务器
    log("\nStep 3: 检测 stats.cc 服务器...")
    while running:
        ok, info = check_server()
        if ok:
            log(f"服务器可用! ({info})")
            break
        else:
            log(f"服务器不可用: {info}  ({CHECK_INTERVAL_DOWN}s后重试)")
            waited = 0
            while waited < CHECK_INTERVAL_DOWN and running:
                time.sleep(min(10, CHECK_INTERVAL_DOWN - waited))
                waited += 10
    
    if not running:
        return
    
    # 二次确认
    log("二次确认...")
    time.sleep(CHECK_INTERVAL_UP)
    ok, info = check_server()
    if not ok:
        log(f"二次确认失败: {info}，重新等待...")
        main()
        return
    
    log(f"确认通过! ({info})")
    
    # Step 4: 启动采集
    start_all()
    
    # Step 5: 监控循环
    log("\nStep 5: 进入监控循环...")
    last_report = time.time()
    
    while running:
        time.sleep(30)
        alive, finished = check_alive()
        
        if time.time() - last_report >= 300:
            log(f"进程状态: {alive} 运行, {finished} 完成")
            last_report = time.time()
        
        if alive == 0 and len(processes) > 0:
            log("=" * 60)
            log("所有采集进程已完成!")
            log("=" * 60)
            
            # 自动执行查漏补缺
            log("开始查漏补缺...")
            try:
                subprocess.run([
                    sys.executable, "parallel_collect_v2.py",
                    "gap-fill", "--total-shards", str(PC_SHARDS)
                ], cwd=SCRAPER_DIR, timeout=7200)
            except:
                log("查漏补缺完成或超时")
            
            break
    
    log("采集流程结束")


if __name__ == "__main__":
    main()

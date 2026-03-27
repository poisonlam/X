"""
自动监控 + 采集脚本
===================
功能：
1. 持续检测 stats.cc 是否恢复正常
2. 恢复后自动启动所有分片的采集（主排行榜 + 额外玩家）
3. 定期输出进度报告
4. 如果采集过程中服务器再次宕机，自动暂停等待恢复

使用方法：
  python auto_monitor_and_collect.py

输出日志到 auto_monitor.log
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
LOG_FILE = os.path.join(SCRAPER_DIR, "auto_monitor.log")
PROGRESS_FILE = os.path.join(SCRAPER_DIR, "auto_monitor_progress.json")

# 采集参数
TOTAL_SHARDS = 5
DELAY = 1.0  # 优化后的延迟
CHECK_INTERVAL_DOWN = 120     # 服务器宕机时，每2分钟检测一次
CHECK_INTERVAL_UP = 30        # 服务器恢复后，每30秒确认一次
PROGRESS_REPORT_INTERVAL = 300  # 每5分钟输出进度报告

# 测试用的请求头
TEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Encoding": "gzip, deflate"  # 不要br! requests不支持brotli解压
}

# 排行榜文件路径
LEADERBOARD_FILE = os.path.join(SCRAPER_DIR, "output", "leaderboard", "leaderboard_full.json")

# 全局控制
running = True
processes = []


def _strip_emoji(text):
    """移除emoji和其他非BMP字符，避免GBK编码崩溃"""
    import re
    # 移除 U+10000 以上的字符（emoji等）
    return re.sub(r'[\U00010000-\U0010ffff]', '', text)


def log(msg):
    """写入日志文件和标准输出"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        # 移除emoji后重试
        safe_line = _strip_emoji(line)
        try:
            print(safe_line, flush=True)
        except Exception:
            print(safe_line.encode("ascii", errors="replace").decode("ascii"), flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def check_server():
    """检测 stats.cc 玩家页面是否恢复正常 - 用排行榜中的真实玩家"""
    try:
        # 从排行榜加载几个玩家来测试
        test_players = []
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                all_players = json.load(f)
            # 取前、中、后各一个
            indices = [0, len(all_players)//2, len(all_players)-1]
            test_players = [all_players[i] for i in indices if i < len(all_players)]
        
        if not test_players:
            # fallback: 用排行榜首页
            s = requests.Session()
            s.headers.update(TEST_HEADERS)
            r = s.get("https://stats.cc/siege/leaderboards/pc/ranked/rankPoints?page=1", timeout=15)
            return r.status_code == 200, f"Leaderboard status: {r.status_code}"
        
        s = requests.Session()
        s.headers.update(TEST_HEADERS)
        
        ok_count = 0
        fail_count = 0
        for p in test_players:
            name = p.get("displayName", "")
            pid = p.get("profileId", "")
            url = f"https://stats.cc/siege/{name}/{pid}"
            try:
                r = s.get(url, timeout=15)
                if r.status_code == 200:
                    ok_count += 1
                else:
                    fail_count += 1
            except:
                fail_count += 1
            time.sleep(1)
        
        if ok_count > 0:
            return True, f"Tested {ok_count+fail_count} players: {ok_count} OK, {fail_count} fail"
        else:
            return False, f"All {fail_count} test players failed"
    except Exception as e:
        return False, f"Error: {e}"


def get_progress():
    """获取当前采集进度"""
    progress = {"main": {}, "extra": {}, "timestamp": ""}
    
    # 主排行榜进度
    total_players = 0
    total_matches = 0
    for sid in range(TOTAL_SHARDS):
        data_file = os.path.join(SCRAPER_DIR, f"shard_{sid}_matches.json")
        progress_file = os.path.join(SCRAPER_DIR, f"shard_{sid}_progress.json")
        players = 0
        matches = 0
        if os.path.exists(progress_file):
            try:
                with open(progress_file, "r") as f:
                    p = json.load(f)
                    players = len(p.get("completed_players", []))
            except:
                pass
        if os.path.exists(data_file):
            try:
                with open(data_file, "r") as f:
                    data = json.load(f)
                    matches = len(data)
            except:
                pass
        progress["main"][f"shard_{sid}"] = {"players": players, "matches": matches}
        total_players += players
        total_matches += matches
    progress["main"]["total"] = {"players": total_players, "matches": total_matches}
    
    # 额外玩家进度
    ex_total_players = 0
    ex_total_matches = 0
    for sid in range(TOTAL_SHARDS):
        data_file = os.path.join(SCRAPER_DIR, f"extra_shard_{sid}_matches.json")
        progress_file = os.path.join(SCRAPER_DIR, f"extra_shard_{sid}_progress.json")
        players = 0
        matches = 0
        if os.path.exists(progress_file):
            try:
                with open(progress_file, "r") as f:
                    p = json.load(f)
                    players = len(p.get("completed_players", []))
            except:
                pass
        if os.path.exists(data_file):
            try:
                with open(data_file, "r") as f:
                    data = json.load(f)
                    matches = len(data)
            except:
                pass
        progress["extra"][f"shard_{sid}"] = {"players": players, "matches": matches}
        ex_total_players += players
        ex_total_matches += matches
    progress["extra"]["total"] = {"players": ex_total_players, "matches": ex_total_matches}
    progress["timestamp"] = datetime.datetime.now().isoformat()
    
    return progress


def save_progress(progress):
    """保存进度到文件，供外部监控读取"""
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except:
        pass


def start_shard_process(script, shard_id, total_shards, delay):
    """启动一个分片采集进程"""
    cmd = [
        sys.executable, script,
        "run",
        "--shard-id", str(shard_id),
        "--total-shards", str(total_shards),
        "--delay", str(delay)
    ]
    log(f"  Starting: {script} shard {shard_id}")
    proc = subprocess.Popen(
        cmd,
        cwd=SCRAPER_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )
    return proc


def monitor_process(proc, label, log_file_path):
    """在后台线程中监控进程输出并写入日志"""
    try:
        with open(log_file_path, "a", encoding="utf-8") as lf:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    lf.write(f"[{ts}] {line}\n")
                    lf.flush()
    except:
        pass


def start_all_collectors():
    """启动所有采集进程"""
    global processes
    processes = []
    
    log("=" * 60)
    log("🚀 启动所有采集进程...")
    log("=" * 60)
    
    # 启动主排行榜的5个分片
    for sid in range(TOTAL_SHARDS):
        proc = start_shard_process("parallel_collect.py", sid, TOTAL_SHARDS, DELAY)
        log_path = os.path.join(SCRAPER_DIR, f"shard_{sid}.log")
        t = threading.Thread(target=monitor_process, args=(proc, f"main-{sid}", log_path), daemon=True)
        t.start()
        processes.append({"proc": proc, "label": f"main-shard-{sid}", "type": "main"})
        time.sleep(0.5)  # 错开启动时间
    
    # 启动额外玩家的5个分片
    for sid in range(TOTAL_SHARDS):
        proc = start_shard_process("extract_and_collect_extra_players.py", sid, TOTAL_SHARDS, DELAY)
        log_path = os.path.join(SCRAPER_DIR, f"extra_shard_{sid}.log")
        t = threading.Thread(target=monitor_process, args=(proc, f"extra-{sid}", log_path), daemon=True)
        t.start()
        processes.append({"proc": proc, "label": f"extra-shard-{sid}", "type": "extra"})
        time.sleep(0.5)
    
    log(f"✅ 已启动 {len(processes)} 个采集进程")


def stop_all_collectors():
    """停止所有采集进程"""
    global processes
    log("🛑 停止所有采集进程...")
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
    log("  所有进程已停止")


def check_processes_alive():
    """检查有多少进程还在运行"""
    alive = 0
    finished = 0
    for p in processes:
        if p["proc"].poll() is None:
            alive += 1
        else:
            finished += 1
    return alive, finished


def signal_handler(sig, frame):
    global running
    log("收到退出信号，正在停止...")
    running = False
    stop_all_collectors()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    global running
    
    log("=" * 60)
    log("🔍 R6 数据采集 - 自动监控与采集系统")
    log("=" * 60)
    
    # 显示当前进度
    progress = get_progress()
    save_progress(progress)
    log(f"当前进度:")
    log(f"  主排行榜: {progress['main']['total']['players']} 玩家, {progress['main']['total']['matches']} 场比赛")
    log(f"  额外玩家: {progress['extra']['total']['players']} 玩家, {progress['extra']['total']['matches']} 场比赛")
    
    # Phase 1: 检测服务器是否可用
    log("")
    log("Phase 1: 检测 stats.cc 服务器状态...")
    
    while running:
        ok, info = check_server()
        if ok:
            log(f"✅ 服务器已恢复! ({info})")
            break
        else:
            log(f"❌ 服务器仍不可用: {info}")
            log(f"   {CHECK_INTERVAL_DOWN}秒后重试...")
            
            # 分段等待，方便快速响应退出信号
            waited = 0
            while waited < CHECK_INTERVAL_DOWN and running:
                time.sleep(min(10, CHECK_INTERVAL_DOWN - waited))
                waited += 10
    
    if not running:
        return
    
    # Phase 2: 二次确认
    log("二次确认服务器稳定性...")
    time.sleep(CHECK_INTERVAL_UP)
    ok, info = check_server()
    if not ok:
        log(f"⚠️ 二次确认失败: {info}，继续等待...")
        # 回到循环
        main()
        return
    
    log(f"✅ 二次确认通过! 服务器稳定 ({info})")
    
    # Phase 3: 启动采集
    start_all_collectors()
    
    # Phase 4: 监控循环
    last_progress_report = time.time()
    last_progress = progress
    
    while running:
        time.sleep(30)
        
        # 检查进程状态
        alive, finished = check_processes_alive()
        
        # 定期输出进度报告
        if time.time() - last_progress_report >= PROGRESS_REPORT_INTERVAL:
            current_progress = get_progress()
            save_progress(current_progress)
            
            main_new_p = current_progress["main"]["total"]["players"] - last_progress["main"]["total"]["players"]
            main_new_m = current_progress["main"]["total"]["matches"] - last_progress["main"]["total"]["matches"]
            ex_new_p = current_progress["extra"]["total"]["players"] - last_progress["extra"]["total"]["players"]
            ex_new_m = current_progress["extra"]["total"]["matches"] - last_progress["extra"]["total"]["matches"]
            
            log("-" * 50)
            log(f"📊 进度报告 (进程: {alive} 运行, {finished} 完成)")
            log(f"  主排行榜: {current_progress['main']['total']['players']} 玩家 (+{main_new_p}), "
                f"{current_progress['main']['total']['matches']} 比赛 (+{main_new_m})")
            log(f"  额外玩家: {current_progress['extra']['total']['players']} 玩家 (+{ex_new_p}), "
                f"{current_progress['extra']['total']['matches']} 比赛 (+{ex_new_m})")
            log("-" * 50)
            
            last_progress = current_progress
            last_progress_report = time.time()
        
        # 如果所有进程都结束了
        if alive == 0 and len(processes) > 0:
            log("=" * 60)
            log("🎉 所有采集进程已完成!")
            final = get_progress()
            save_progress(final)
            log(f"最终结果:")
            log(f"  主排行榜: {final['main']['total']['players']} 玩家, {final['main']['total']['matches']} 场比赛")
            log(f"  额外玩家: {final['extra']['total']['players']} 玩家, {final['extra']['total']['matches']} 场比赛")
            log("=" * 60)
            break
    
    log("监控结束")


if __name__ == "__main__":
    main()

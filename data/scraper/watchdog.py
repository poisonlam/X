"""
R6 采集守护进程 (Watchdog)
==========================
功能:
  1. 定期检查 V2 分片进程是否存活
  2. 检测采集进度是否停滞
  3. 进程 crash/停滞 时弹 Windows 通知
  4. 自动重启 crash 的分片进程
  5. 采集全部完成时弹通知

用法: python watchdog.py
      python watchdog.py --check-interval 120   # 每120秒检查一次(默认60)
      python watchdog.py --stall-minutes 15      # 停滞超过15分钟报警(默认10)
      python watchdog.py --no-restart             # 只通知不重启
"""
import json
import os
import sys
import io
import time
import subprocess
import argparse
import ctypes
from datetime import datetime, timedelta
from pathlib import Path

# 确保 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
else:
    sys.stdout.reconfigure(line_buffering=True)

BASE_DIR = Path(__file__).parent
EXTRA_DIR = BASE_DIR / "output" / "extra_match_data"
EXTRA_PLAYERS_FILE = EXTRA_DIR / "_extra_players.json"

TOTAL_SHARDS = 16
DELAY = 1.2
MAX_MATCHES = 5
PYTHON_EXE = sys.executable
EXTRA_V2_SCRIPT = str(BASE_DIR / "extra_v2.py")

# ===== Windows 通知 =====
def win_notify(title, message):
    """使用 Windows 原生弹窗通知"""
    try:
        # 方法1: Windows Toast通知 (win10toast)
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=10, threaded=True)
            return
        except ImportError:
            pass

        # 方法2: Windows MessageBox (始终可用)
        # MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL | MB_TOPMOST
        MB_OK = 0x0
        MB_ICONWARNING = 0x30
        MB_ICONINFORMATION = 0x40
        MB_SYSTEMMODAL = 0x1000
        MB_SETFOREGROUND = 0x10000

        icon = MB_ICONINFORMATION if "完成" in title else MB_ICONWARNING
        flags = MB_OK | icon | MB_SYSTEMMODAL | MB_SETFOREGROUND

        # 在新线程中弹窗，避免阻塞主循环
        import threading
        def _show():
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
        t = threading.Thread(target=_show, daemon=True)
        t.start()

    except Exception as e:
        print(f"  [!] 通知发送失败: {e}")


def play_alert_sound():
    """播放系统警告声"""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except:
        pass


# ===== 进度文件读取 =====
def rj(fp):
    """安全读取 JSON"""
    for _ in range(3):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            time.sleep(0.1)
    return None


def get_total_players():
    """获取总玩家数"""
    if EXTRA_PLAYERS_FILE.exists():
        d = rj(str(EXTRA_PLAYERS_FILE))
        if d:
            pids = set()
            for p in d:
                pid = p.get('profileId') if isinstance(p, dict) else p
                if pid:
                    pids.add(pid)
            return len(pids)
    return 112816


def get_shard_progress(shard_id):
    """获取单个V2分片的进度"""
    pf = EXTRA_DIR / f"_v2_shard_{shard_id}_progress.json"
    if pf.exists():
        d = rj(str(pf))
        if d:
            return {
                'completed_players': len(d.get('completed_players', [])),
                'completed_matches': len(d.get('completed_matches', [])),
                'last_updated': d.get('last_updated', ''),
            }
    return {'completed_players': 0, 'completed_matches': 0, 'last_updated': ''}


def get_global_done():
    """获取全局去重后的已完成玩家数"""
    done = set()
    # 全局文件
    gf = EXTRA_DIR / "_global_completed_players.json"
    if gf.exists():
        d = rj(str(gf))
        if d:
            done.update(d)
    # 旧分片
    for i in range(20):
        pf = EXTRA_DIR / f"_shard_{i}_progress.json"
        if pf.exists():
            d = rj(str(pf))
            if d:
                done.update(d.get('completed_players', []))
    # V2分片
    for i in range(20):
        pf = EXTRA_DIR / f"_v2_shard_{i}_progress.json"
        if pf.exists():
            d = rj(str(pf))
            if d:
                done.update(d.get('completed_players', []))
    return len(done)


def find_running_shards():
    """查找当前运行中的 extra_v2 分片进程"""
    running = {}
    try:
        ps_script = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like '*extra_v2*run*' } | "
            "Select-Object ProcessId, CommandLine | "
            "ConvertTo-Json"
        )
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for proc in data:
                pid = proc.get('ProcessId')
                cmdline = proc.get('CommandLine', '')
                # 解析 shard-id
                if '--shard-id' in cmdline:
                    parts = cmdline.split()
                    for j, part in enumerate(parts):
                        if part == '--shard-id' and j + 1 < len(parts):
                            try:
                                sid = int(parts[j + 1])
                                running[sid] = pid
                            except ValueError:
                                pass
    except Exception as e:
        print(f"  [!] 查进程失败: {e}")
    return running


def restart_shard(shard_id):
    """重启指定分片"""
    log_out = str(EXTRA_DIR / f'v2_shard_{shard_id}_log.txt')
    log_err = str(EXTRA_DIR / f'v2_shard_{shard_id}_err.txt')

    cmd = [
        PYTHON_EXE, EXTRA_V2_SCRIPT,
        'run',
        '--shard-id', str(shard_id),
        '--total-shards', str(TOTAL_SHARDS),
        '--max-matches', str(MAX_MATCHES),
        '--delay', str(DELAY),
    ]

    # 追加模式写日志，不覆盖之前的
    out_f = open(log_out, 'a', encoding='utf-8')
    err_f = open(log_err, 'a', encoding='utf-8')

    # 写入重启标记
    restart_marker = f"\n{'='*60}\n[WATCHDOG RESTART] {datetime.now().isoformat()}\n{'='*60}\n"
    out_f.write(restart_marker)
    out_f.flush()

    p = subprocess.Popen(cmd, stdout=out_f, stderr=err_f, cwd=str(BASE_DIR))
    return p.pid


# ===== 主监控循环 =====
def main():
    parser = argparse.ArgumentParser(description='R6 采集守护进程')
    parser.add_argument('--check-interval', type=int, default=60, help='检查间隔(秒), 默认60')
    parser.add_argument('--stall-minutes', type=int, default=10, help='停滞阈值(分钟), 默认10')
    parser.add_argument('--no-restart', action='store_true', help='只通知不自动重启')
    args = parser.parse_args()

    CHECK_INTERVAL = args.check_interval
    STALL_THRESHOLD = timedelta(minutes=args.stall_minutes)
    AUTO_RESTART = not args.no_restart

    print(f"{'='*60}")
    print(f"  R6 采集守护进程 (Watchdog)")
    print(f"  检查间隔: {CHECK_INTERVAL}s")
    print(f"  停滞阈值: {args.stall_minutes}分钟")
    print(f"  自动重启: {'是' if AUTO_RESTART else '否'}")
    print(f"{'='*60}")

    total_players = get_total_players()
    print(f"  Extra 总玩家: {total_players}")
    print(f"  启动等待 45 秒 (等待采集进程完全启动)...")
    time.sleep(45)
    print(f"  开始监控!")

    # 上一次的进度快照 (用于检测停滞)
    last_progress = {}
    last_progress_time = {}
    # 通知冷却 (避免重复弹窗)
    notify_cooldown = {}
    COOLDOWN_SECONDS = 300  # 同一事件5分钟内不重复通知
    # 已通知完成
    completion_notified = False
    # 重启计数 (防止死循环重启)
    restart_counts = {}
    MAX_RESTARTS_PER_SHARD = 5

    try:
        while True:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            # 1. 查找运行中的分片
            running = find_running_shards()
            expected_shards = set(range(TOTAL_SHARDS))
            running_shards = set(running.keys())
            crashed_shards = expected_shards - running_shards

            # 2. 获取进度
            global_done = get_global_done()
            remaining = total_players - global_done
            pct = global_done / max(total_players, 1) * 100

            print(f"\n[{now_str}] 进度: {global_done}/{total_players} ({pct:.1f}%) | "
                  f"运行中: {sorted(running_shards)} | "
                  f"已退出: {sorted(crashed_shards) if crashed_shards else '无'}")

            # 3. 检查是否全部完成
            if remaining <= 0 and not completion_notified:
                msg = (f"🎉 Extra 采集已全部完成!\n"
                       f"总计: {global_done} 玩家\n"
                       f"时间: {now_str}")
                print(f"  ★ {msg}")
                win_notify("✅ R6 采集完成!", msg)
                play_alert_sound()
                completion_notified = True
                # 完成后继续监控几轮确认
                time.sleep(CHECK_INTERVAL)
                continue

            # 4. 处理 crash 的分片
            for sid in crashed_shards:
                cooldown_key = f"crash_{sid}"
                last_notify = notify_cooldown.get(cooldown_key, datetime.min)

                if (now - last_notify).total_seconds() < COOLDOWN_SECONDS:
                    continue  # 冷却中，不重复处理

                restart_count = restart_counts.get(sid, 0)

                if AUTO_RESTART and restart_count < MAX_RESTARTS_PER_SHARD:
                    # 自动重启
                    new_pid = restart_shard(sid)
                    restart_counts[sid] = restart_count + 1
                    msg = (f"⚠️ 分片 {sid} 已 crash，已自动重启\n"
                           f"新 PID: {new_pid}\n"
                           f"重启次数: {restart_counts[sid]}/{MAX_RESTARTS_PER_SHARD}\n"
                           f"时间: {now_str}")
                    print(f"  [RESTART] Shard {sid} -> PID {new_pid} (第{restart_counts[sid]}次)")
                    win_notify(f"⚠️ R6 分片{sid} 已重启", msg)
                    play_alert_sound()
                elif restart_count >= MAX_RESTARTS_PER_SHARD:
                    msg = (f"🔴 分片 {sid} 已 crash 超过 {MAX_RESTARTS_PER_SHARD} 次!\n"
                           f"不再自动重启，请手动检查!\n"
                           f"时间: {now_str}")
                    print(f"  [!] Shard {sid} 超过重启上限!")
                    win_notify(f"🔴 R6 分片{sid} 反复崩溃", msg)
                    play_alert_sound()
                else:
                    # 不自动重启模式
                    msg = (f"⚠️ 分片 {sid} 进程已退出!\n"
                           f"PID 不存在\n"
                           f"时间: {now_str}")
                    print(f"  [CRASH] Shard {sid} 进程不存在")
                    win_notify(f"⚠️ R6 分片{sid} 已停止", msg)
                    play_alert_sound()

                notify_cooldown[cooldown_key] = now

            # 5. 检测停滞 (进度长时间不变)
            for sid in running_shards:
                prog = get_shard_progress(sid)
                current_count = prog['completed_players']
                last_count = last_progress.get(sid, current_count)

                if current_count > last_count:
                    # 有进展，更新快照
                    last_progress[sid] = current_count
                    last_progress_time[sid] = now
                    restart_counts[sid] = 0  # 重置重启计数
                elif sid not in last_progress_time:
                    # 首次记录
                    last_progress[sid] = current_count
                    last_progress_time[sid] = now
                else:
                    # 无进展，检查是否超过阈值
                    stall_duration = now - last_progress_time[sid]
                    if stall_duration > STALL_THRESHOLD:
                        cooldown_key = f"stall_{sid}"
                        last_notify = notify_cooldown.get(cooldown_key, datetime.min)

                        if (now - last_notify).total_seconds() >= COOLDOWN_SECONDS:
                            stall_mins = stall_duration.total_seconds() / 60
                            msg = (f"⏸️ 分片 {sid} 采集停滞!\n"
                                   f"已 {stall_mins:.0f} 分钟无进展\n"
                                   f"当前: {current_count} 玩家\n"
                                   f"最后更新: {prog['last_updated']}\n"
                                   f"时间: {now_str}")
                            print(f"  [STALL] Shard {sid}: {stall_mins:.0f}分钟无进展 ({current_count} players)")
                            win_notify(f"⏸️ R6 分片{sid} 停滞", msg)
                            play_alert_sound()
                            notify_cooldown[cooldown_key] = now

            # 6. 检测所有分片都退出 (电脑关机后重开的情况)
            if not running_shards and remaining > 0:
                cooldown_key = "all_stopped"
                last_notify = notify_cooldown.get(cooldown_key, datetime.min)

                if (now - last_notify).total_seconds() >= COOLDOWN_SECONDS:
                    if AUTO_RESTART:
                        restarted = []
                        for sid in range(TOTAL_SHARDS):
                            rc = restart_counts.get(sid, 0)
                            if rc < MAX_RESTARTS_PER_SHARD:
                                new_pid = restart_shard(sid)
                                restart_counts[sid] = rc + 1
                                restarted.append(f"S{sid}->PID{new_pid}")
                                time.sleep(3)  # 错开启动
                        msg = (f"🔴 所有采集进程已停止!\n"
                               f"剩余 {remaining} 玩家未完成\n"
                               f"已自动重启: {', '.join(restarted)}\n"
                               f"时间: {now_str}")
                        print(f"  [ALL STOPPED] 已全部重启: {restarted}")
                    else:
                        msg = (f"🔴 所有采集进程已停止!\n"
                               f"剩余 {remaining} 玩家未完成\n"
                               f"请手动重启采集\n"
                               f"时间: {now_str}")
                        print(f"  [ALL STOPPED] 无运行中的分片!")

                    win_notify("🔴 R6 采集全部停止!", msg)
                    play_alert_sound()
                    notify_cooldown[cooldown_key] = now

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n  守护进程已停止。采集进程仍在运行中。")
        sys.exit(0)


if __name__ == '__main__':
    main()

"""
批量启动Extra V2采集 — 16个分片并行
用法: python start_extra_v2.py
"""
import subprocess
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRA_DIR = os.path.join(BASE_DIR, 'output', 'extra_match_data')

TOTAL_SHARDS = 16
DELAY = 1.2  # 16分片×1.2s ≈ 0.83 req/s/shard, 总计~13.3 req/s (有自适应回退兜底)
MAX_MATCHES = 5

def main():
    print("=" * 60)
    print(f"启动 Extra V2 采集 ({TOTAL_SHARDS}个分片)")
    print("=" * 60)
    
    processes = []
    
    for sid in range(TOTAL_SHARDS):
        log_out = os.path.join(EXTRA_DIR, f'v2_shard_{sid}_log.txt')
        log_err = os.path.join(EXTRA_DIR, f'v2_shard_{sid}_err.txt')
        
        cmd = [
            sys.executable, os.path.join(BASE_DIR, 'extra_v2.py'),
            'run',
            '--shard-id', str(sid),
            '--total-shards', str(TOTAL_SHARDS),
            '--max-matches', str(MAX_MATCHES),
            '--delay', str(DELAY),
        ]
        
        out_f = open(log_out, 'w', encoding='utf-8')
        err_f = open(log_err, 'w', encoding='utf-8')
        
        p = subprocess.Popen(cmd, stdout=out_f, stderr=err_f, cwd=BASE_DIR)
        processes.append((sid, p, out_f, err_f))
        print(f"  [START] Shard {sid} -> PID {p.pid}")
        
        # 错开启动，避免同时加载大文件
        time.sleep(3)
    
    print(f"\n所有 {TOTAL_SHARDS} 个分片已启动!")
    print(f"日志文件: {EXTRA_DIR}/v2_shard_*_log.txt")
    print(f"监控面板: python live_monitor_v3.py")
    print(f"\n按 Ctrl+C 停止所有进程...")
    
    try:
        while True:
            alive = [(sid, p) for sid, p, _, _ in processes if p.poll() is None]
            if not alive:
                print("\n所有分片已完成!")
                break
            time.sleep(30)
            print(f"  [STATUS] {len(alive)} 个分片仍在运行: {[s for s, _ in alive]}")
    except KeyboardInterrupt:
        print("\n\n正在停止所有进程...")
        for sid, p, out_f, err_f in processes:
            if p.poll() is None:
                p.terminate()
                print(f"  [STOP] Shard {sid} (PID {p.pid})")
            out_f.close()
            err_f.close()
        print("所有进程已停止。")

if __name__ == '__main__':
    main()

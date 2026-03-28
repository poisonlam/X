"""批量启动段位采集 — 16分片并行"""
import subprocess
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOTAL_SHARDS = 32
DELAY = 0.6

def main():
    print("=" * 60)
    print(f"启动段位采集 ({TOTAL_SHARDS}个分片, delay={DELAY}s)")
    print("=" * 60)
    
    processes = []
    for sid in range(TOTAL_SHARDS):
        log_out = os.path.join(BASE_DIR, 'output', 'rank_data', f'shard_{sid}_log.txt')
        log_err = os.path.join(BASE_DIR, 'output', 'rank_data', f'shard_{sid}_err.txt')
        
        cmd = [
            sys.executable, os.path.join(BASE_DIR, 'fetch_ranks.py'),
            'run',
            '--shard-id', str(sid),
            '--total-shards', str(TOTAL_SHARDS),
            '--delay', str(DELAY),
        ]
        
        out_f = open(log_out, 'w', encoding='utf-8')
        err_f = open(log_err, 'w', encoding='utf-8')
        p = subprocess.Popen(cmd, stdout=out_f, stderr=err_f, cwd=BASE_DIR)
        processes.append((sid, p, out_f, err_f))
        print(f"  [START] Shard {sid} -> PID {p.pid}")
        time.sleep(1)
    
    print(f"\n所有 {TOTAL_SHARDS} 个分片已启动!")
    print(f"查看进度: python fetch_ranks.py status")
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
        print("\n停止所有进程...")
        for sid, p, out_f, err_f in processes:
            if p.poll() is None:
                p.terminate()
            out_f.close()
            err_f.close()

if __name__ == '__main__':
    main()

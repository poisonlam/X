"""检查最近采集的数据，分析"没找到对局"的情况"""
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

def check_pc():
    print("=" * 60)
    print("=== PC Match Data 分析 ===")
    print("=" * 60)
    
    # 统计各shard的对局数
    total_matches = 0
    for i in range(5):
        path = os.path.join(BASE, f"output/match_data/shard_{i}/match_details.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else 0
            print(f"  Shard {i}: {count} 条对局")
            total_matches += count
    
    print(f"  PC总对局数: {total_matches}")
    
    # 检查anomaly players
    anomaly_path = os.path.join(BASE, "output/match_data/_anomaly_players.json")
    if os.path.exists(anomaly_path):
        with open(anomaly_path, 'r', encoding='utf-8') as f:
            anomaly = json.load(f)
        print(f"\n  PC异常玩家数: {len(anomaly)}")
        # 统计异常原因
        reasons = {}
        for p in anomaly:
            if isinstance(p, dict):
                r = p.get('reason', 'unknown')
            else:
                r = str(p)
            reasons[r] = reasons.get(r, 0) + 1
        print("  异常原因分布:")
        for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {r}: {c} 个")
        
        # 最后10个异常玩家
        print("\n  最近10个异常玩家:")
        for p in anomaly[-10:]:
            if isinstance(p, dict):
                print(f"    {p.get('name', '?')} | reason: {p.get('reason', 'N/A')}")
            else:
                print(f"    {p}")
    
    # 检查shared_match_ids的增长
    shared_path = os.path.join(BASE, "output/match_data/_shared_match_ids.json")
    if os.path.exists(shared_path):
        with open(shared_path, 'r', encoding='utf-8') as f:
            shared = json.load(f)
        if isinstance(shared, list):
            print(f"\n  共享match_id池: {len(shared)} 个唯一对局")
        elif isinstance(shared, dict):
            print(f"\n  共享match_id池: {len(shared)} 个唯一对局")
    
    # 查看最近几个对局的时间
    path0 = os.path.join(BASE, "output/match_data/shard_0/match_details.json")
    if os.path.exists(path0):
        with open(path0, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            print("\n  最近5场对局的时间:")
            for m in data[-5:]:
                if isinstance(m, dict):
                    started = m.get('started_at', 'N/A')
                    ended = m.get('ended_at', 'N/A')
                    map_name = m.get('map', 'N/A')
                    playlist = m.get('playlist', 'N/A')
                    mid = m.get('match_id', 'N/A')
                    print(f"    {mid[:20]}... | {playlist} | {map_name} | {started} ~ {ended}")

def check_extra():
    print("\n" + "=" * 60)
    print("=== Extra Match Data 分析 ===")
    print("=" * 60)
    
    total_matches = 0
    for i in range(8):
        path = os.path.join(BASE, f"output/extra_match_data/shard_{i}/match_details.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else 0
            print(f"  Shard {i}: {count} 条对局")
            total_matches += count
    
    print(f"  Extra总对局数: {total_matches}")
    
    # 检查anomaly players
    anomaly_path = os.path.join(BASE, "output/extra_match_data/_anomaly_players.json")
    if os.path.exists(anomaly_path):
        with open(anomaly_path, 'r', encoding='utf-8') as f:
            anomaly = json.load(f)
        print(f"\n  Extra异常玩家数: {len(anomaly)}")
        reasons = {}
        for p in anomaly:
            if isinstance(p, dict):
                r = p.get('reason', 'unknown')
            else:
                r = str(p)
            reasons[r] = reasons.get(r, 0) + 1
        print("  异常原因分布:")
        for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {r}: {c} 个")
        
        print("\n  最近10个异常玩家:")
        for p in anomaly[-10:]:
            if isinstance(p, dict):
                print(f"    {p.get('name', '?')} | reason: {p.get('reason', 'N/A')}")
            else:
                print(f"    {p}")

def check_progress():
    print("\n" + "=" * 60)
    print("=== 进度统计 ===")
    print("=" * 60)
    
    # PC进度
    pc_total_completed = 0
    for i in range(5):
        path = os.path.join(BASE, f"output/match_data/_shard_{i}_progress.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                prog = json.load(f)
            completed = len(prog.get('completed', []))
            pc_total_completed += completed
    
    # Extra进度
    extra_total_completed = 0
    for i in range(8):
        path = os.path.join(BASE, f"output/extra_match_data/_shard_{i}_progress.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                prog = json.load(f)
            completed = len(prog.get('completed', []))
            extra_total_completed += completed
    
    print(f"  PC已处理玩家: {pc_total_completed} / 10015")
    print(f"  Extra已处理玩家: {extra_total_completed} / 63199")
    
    # 计算"有对局"vs"无对局"的比例
    # 用 completed - anomaly 数来估算
    pc_anomaly_path = os.path.join(BASE, "output/match_data/_anomaly_players.json")
    pc_anomaly_count = 0
    if os.path.exists(pc_anomaly_path):
        with open(pc_anomaly_path, 'r', encoding='utf-8') as f:
            pc_anomaly_count = len(json.load(f))
    
    extra_anomaly_path = os.path.join(BASE, "output/extra_match_data/_anomaly_players.json")
    extra_anomaly_count = 0
    if os.path.exists(extra_anomaly_path):
        with open(extra_anomaly_path, 'r', encoding='utf-8') as f:
            extra_anomaly_count = len(json.load(f))
    
    pc_with_matches = pc_total_completed - pc_anomaly_count
    extra_with_matches = extra_total_completed - extra_anomaly_count
    
    print(f"\n  PC: {pc_with_matches} 有对局, {pc_anomaly_count} 无对局/异常 ({pc_anomaly_count}/{pc_total_completed}={pc_anomaly_count/max(pc_total_completed,1)*100:.1f}%)")
    print(f"  Extra: {extra_with_matches} 有对局, {extra_anomaly_count} 无对局/异常 ({extra_anomaly_count}/{extra_total_completed}={extra_anomaly_count/max(extra_total_completed,1)*100:.1f}%)")

if __name__ == '__main__':
    check_pc()
    check_extra()
    check_progress()

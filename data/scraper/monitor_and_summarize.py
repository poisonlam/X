"""
数据采集监控 & 汇总脚本
- 检查所有采集任务的进度
- 当所有任务完成后，生成汇总报告
适配实际文件结构：
  output/match_data/_shard_{0-4}_progress.json  (PC排行榜)
  output/extra_match_data/_shard_{0-7}_progress.json (额外玩家)
  output/leaderboard/leaderboard_{console,global}.json
"""

import json
import os
import glob
import time
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

def check_pc_leaderboard_progress():
    """检查 PC 排行榜采集进度（5个 collector agent）"""
    match_dir = OUTPUT_DIR / "match_data"

    # 总玩家数从排行榜获取
    try:
        lb = json.load(open(OUTPUT_DIR / "leaderboard" / "leaderboard_full.json", 'r', encoding='utf-8'))
        total_players = len(lb)
    except:
        total_players = 10015

    completed_players = 0
    completed_matches = 0
    shard_details = []

    for i in range(5):
        pf = match_dir / f"_shard_{i}_progress.json"
        try:
            with open(pf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cp = len(data.get("completed_players", []))
            cm = len(data.get("completed_matches", []))
            completed_players += cp
            completed_matches += cm
            shard_details.append({
                "shard": i,
                "completed_players": cp,
                "completed_matches": cm
            })
        except:
            shard_details.append({"shard": i, "completed_players": 0, "completed_matches": 0})

    pct = round(completed_players / total_players * 100, 1) if total_players > 0 else 0
    is_done = completed_players >= total_players

    return {
        "status": "completed" if is_done else "running",
        "total": total_players,
        "completed": completed_players,
        "matches": completed_matches,
        "pct": pct,
        "shards": shard_details
    }

def check_extra_leaderboards():
    """检查 Console/Global 排行榜爬取进度"""
    results = {}
    lb_dir = OUTPUT_DIR / "leaderboard"
    for platform in ["console", "global"]:
        lb_file = lb_dir / f"leaderboard_{platform}.json"
        if lb_file.exists():
            try:
                with open(lb_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results[platform] = {"status": "completed", "players": len(data)}
            except:
                results[platform] = {"status": "error", "players": 0}
        else:
            # 检查是否有中间页面文件
            page_files = list(lb_dir.glob(f"leaderboard_{platform}_page_*.json"))
            if page_files:
                total_players = 0
                for pf in page_files:
                    try:
                        with open(pf, 'r', encoding='utf-8') as f:
                            total_players += len(json.load(f))
                    except:
                        pass
                results[platform] = {"status": "running", "players": total_players, "pages": len(page_files)}
            else:
                results[platform] = {"status": "not_started", "players": 0}
    return results

def check_extra_players_progress():
    """检查额外玩家采集进度（8个 extra agent）"""
    extra_dir = OUTPUT_DIR / "extra_match_data"

    # 总额外玩家数
    try:
        ep = json.load(open(extra_dir / "_extra_players.json", 'r', encoding='utf-8'))
        total_players = len(ep)
    except:
        total_players = 63199

    completed_players = 0
    completed_matches = 0
    shard_details = []

    for i in range(8):
        pf = extra_dir / f"_shard_{i}_progress.json"
        try:
            with open(pf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cp = len(data.get("completed_players", []))
            cm = len(data.get("completed_matches", []))
            completed_players += cp
            completed_matches += cm
            shard_details.append({
                "shard": i,
                "completed_players": cp,
                "completed_matches": cm
            })
        except:
            shard_details.append({"shard": i, "completed_players": 0, "completed_matches": 0})

    pct = round(completed_players / total_players * 100, 1) if total_players > 0 else 0
    is_done = completed_players >= total_players

    return {
        "status": "completed" if is_done else ("running" if completed_players > 0 else "not_started"),
        "total": total_players,
        "completed": completed_players,
        "matches": completed_matches,
        "pct": pct,
        "shards": shard_details
    }

def count_data_files():
    """统计已采集的数据文件数量和大小"""
    results = {}
    for label, d in [
        ("PC排行榜比赛", OUTPUT_DIR / "match_data"),
        ("额外玩家比赛", OUTPUT_DIR / "extra_match_data"),
        ("排行榜数据", OUTPUT_DIR / "leaderboard")
    ]:
        if d.exists():
            total_size = 0
            count = 0
            for root, dirs, files in os.walk(str(d)):
                for f in files:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    count += 1
            results[label] = {
                "files": count,
                "size_mb": round(total_size / 1024 / 1024, 1)
            }
        else:
            results[label] = {"files": 0, "size_mb": 0}
    return results

def count_unique_players_from_matches():
    """从比赛数据中统计唯一玩家和段位分布（完整模式用）"""
    all_player_ids = set()
    rank_counts = {}

    for matches_dir in [OUTPUT_DIR / "match_data", OUTPUT_DIR / "extra_match_data"]:
        if not matches_dir.exists():
            continue
        for shard_dir in matches_dir.iterdir():
            if not shard_dir.is_dir():
                continue
            mf = shard_dir / "match_details.json"
            if not mf.exists():
                continue
            try:
                with open(mf, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        continue
                    data = json.loads(content)

                # data 可能是 dict {player_id: [matches]} 或 list
                if isinstance(data, dict):
                    for player_id, matches in data.items():
                        if not isinstance(matches, list):
                            continue
                        for match in matches:
                            if not isinstance(match, dict):
                                continue
                            # 从 rounds 中提取所有玩家
                            rounds = match.get("rounds", [])
                            for rnd in rounds:
                                if not isinstance(rnd, dict):
                                    continue
                                for team in rnd.get("teams", []):
                                    if not isinstance(team, dict):
                                        continue
                                    for p in team.get("players", []):
                                        if not isinstance(p, dict):
                                            continue
                                        pid = p.get("profileId", "")
                                        if pid:
                                            all_player_ids.add(pid)
                                        rank = p.get("rank", "")
                                        if rank:
                                            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            except Exception as e:
                pass

    return {
        "total_unique_players": len(all_player_ids),
        "rank_distribution": dict(sorted(rank_counts.items(), key=lambda x: -x[1])[:30])
    }

def generate_summary(mode="quick"):
    """生成汇总报告"""
    print(f"\n{'='*65}")
    print(f"  R6 Siege 数据采集监控报告")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  模式: {'完整汇总' if mode == 'full' else '快速检查'}")
    print(f"{'='*65}\n")

    # 1. PC排行榜采集
    pc = check_pc_leaderboard_progress()
    done_icon = "✅" if pc['status'] == 'completed' else "🔄"
    print(f"{done_icon} PC排行榜玩家采集 — {pc['completed']}/{pc['total']} ({pc['pct']}%), {pc['matches']} 场比赛")
    for s in pc['shards']:
        si = "✅" if s['completed_players'] >= (pc['total'] // 5) else "🔄"
        print(f"   {si} Shard {s['shard']}: {s['completed_players']} players, {s['completed_matches']} matches")
    print()

    # 2. Console/Global 排行榜
    extra_lb = check_extra_leaderboards()
    print(f"📋 额外排行榜")
    for platform, info in extra_lb.items():
        si = "✅" if info['status'] == 'completed' else ("🔄" if info['status'] == 'running' else "⏳")
        extra = f" ({info.get('pages', '?')} pages)" if 'pages' in info else ""
        print(f"   {si} {platform}: {info['players']} 玩家 [{info['status']}{extra}]")
    print()

    # 3. 额外玩家比赛采集
    extra = check_extra_players_progress()
    done_icon = "✅" if extra['status'] == 'completed' else "🔄"
    print(f"{done_icon} 额外玩家比赛采集 — {extra['completed']}/{extra['total']} ({extra['pct']}%), {extra['matches']} 场比赛")
    for s in extra['shards']:
        si = "✅" if s['completed_players'] >= (extra['total'] // 8) else "🔄"
        print(f"   {si} Shard {s['shard']}: {s['completed_players']} players, {s['completed_matches']} matches")
    print()

    # 4. 数据文件统计
    files_info = count_data_files()
    total_files = sum(v['files'] for v in files_info.values())
    total_size = sum(v['size_mb'] for v in files_info.values())
    print(f"📁 数据文件: {total_files} 个, 共 {total_size:.1f} MB")
    for label, info in files_info.items():
        print(f"   {label}: {info['files']} 文件, {info['size_mb']} MB")
    print()

    # 5. 完整汇总 - 统计唯一玩家
    if mode == "full":
        print(f"🔍 正在扫描比赛数据统计唯一玩家...")
        ps = count_unique_players_from_matches()
        print(f"👥 比赛中唯一玩家总数: {ps['total_unique_players']}")
        if ps['rank_distribution']:
            print(f"🏅 段位分布 (top 30):")
            for rank, count in ps['rank_distribution'].items():
                print(f"   {rank}: {count}")
        print()

    # 6. 总体状态判断
    all_done = (
        pc.get('status') == 'completed' and
        extra.get('status') == 'completed' and
        all(info.get('status') == 'completed' for info in extra_lb.values())
    )

    print(f"{'='*65}")
    if all_done:
        print(f"  ✅ 所有采集任务已完成！可以开始数据分析。")
    else:
        pending = []
        if pc.get('status') != 'completed':
            pending.append(f"PC排行榜({pc['pct']}%)")
        for p, info in extra_lb.items():
            if info.get('status') != 'completed':
                pending.append(f"{p}排行榜")
        if extra.get('status') != 'completed':
            pending.append(f"额外玩家({extra['pct']}%)")
        print(f"  🔄 进行中: {', '.join(pending)}")
    print(f"{'='*65}")

    return all_done

def monitor_loop(interval=300, max_hours=48):
    """持续监控，每隔 interval 秒检查一次"""
    print(f"🚀 监控已启动，每 {interval} 秒检查一次（最长 {max_hours} 小时）")

    start_time = time.time()
    max_seconds = max_hours * 3600
    check_count = 0

    while True:
        check_count += 1
        elapsed = time.time() - start_time

        if elapsed > max_seconds:
            print(f"\n⏰ 达到最大监控时长，输出最终汇总...")
            generate_summary(mode="full")
            break

        print(f"\n--- 检查 #{check_count} (运行 {elapsed/3600:.1f}h) ---")
        all_done = generate_summary(mode="quick")

        if all_done:
            print(f"\n🎉 所有任务完成！生成完整汇总...")
            generate_summary(mode="full")

            # 保存汇总JSON
            report = {
                "timestamp": datetime.now().isoformat(),
                "pc_leaderboard": check_pc_leaderboard_progress(),
                "extra_leaderboards": check_extra_leaderboards(),
                "extra_players": check_extra_players_progress(),
                "data_files": count_data_files(),
                "unique_players": count_unique_players_from_matches()
            }
            report_file = OUTPUT_DIR / "collection_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n📄 报告已保存: {report_file}")
            break

        print(f"\n⏳ {interval}秒后再查...")
        time.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            monitor_loop(interval=interval)
        elif cmd == "full":
            generate_summary(mode="full")
        elif cmd == "quick":
            generate_summary(mode="quick")
        else:
            print(f"Usage: python {sys.argv[0]} [quick|full|monitor [interval_secs]]")
    else:
        generate_summary(mode="quick")

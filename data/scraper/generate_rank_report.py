"""
综合段位分布分析报告生成器

合并所有已知段位数据源:
1. 排行榜数据 (leaderboard_full.json) - ~10,000 玩家
2. 已采集对局中的 source_player 段位
3. 生成可视化 HTML 报告
"""

import json
import os
import glob
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_leaderboard():
    """排行榜: ~10,000 玩家 Diamond III+"""
    path = os.path.join(SCRIPT_DIR, "output", "leaderboard", "leaderboard_full.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = {}
    for p in data:
        pid = p.get("profileId")
        if pid:
            result[pid] = {
                "rank": p.get("rank", "unknown"),
                "rankPoints": p.get("rankPoints", 0),
                "displayName": p.get("displayName", ""),
                "source": "leaderboard",
            }
    return result


def load_match_ranks():
    """从所有已采集对局中提取 source_player 段位"""
    result = {}
    patterns = [
        os.path.join(SCRIPT_DIR, "output", "match_data", "shard_*", "match_details.json"),
        os.path.join(SCRIPT_DIR, "output", "extra_match_data", "shard_*", "match_details.json"),
    ]
    for pattern in patterns:
        for fpath in glob.glob(pattern):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                matches = data if isinstance(data, list) else [data]
                for m in matches:
                    sp = m.get("source_player", {})
                    rank = sp.get("rank", "")
                    pid = sp.get("profileId", "")
                    rp = sp.get("rankPoints", 0)
                    if rank and pid:
                        if pid not in result or rp > result[pid].get("rankPoints", 0):
                            result[pid] = {
                                "rank": rank,
                                "rankPoints": rp,
                                "displayName": sp.get("displayName", ""),
                                "source": "match_data",
                            }
            except Exception:
                pass
    return result


def load_extra_players():
    """加载额外玩家列表"""
    path = os.path.join(SCRIPT_DIR, "output", "extra_match_data", "_extra_players.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_shard_progress():
    """加载各分片采集进度"""
    progress = {}
    
    # 加载排行榜总数以计算PC total
    lb_path = os.path.join(SCRIPT_DIR, "output", "leaderboard", "leaderboard_full.json")
    pc_total = 0
    if os.path.exists(lb_path):
        with open(lb_path, "r", encoding="utf-8") as f:
            pc_total = len(json.load(f))
    
    # 加载额外玩家总数
    ep_path = os.path.join(SCRIPT_DIR, "output", "extra_match_data", "_extra_players.json")
    extra_total = 0
    if os.path.exists(ep_path):
        with open(ep_path, "r", encoding="utf-8") as f:
            extra_total = len(json.load(f))
    
    # PC match shards
    pc_done = 0
    for i in range(5):
        pf = os.path.join(SCRIPT_DIR, "output", "match_data", f"_shard_{i}_progress.json")
        if os.path.exists(pf):
            with open(pf, "r", encoding="utf-8") as f:
                data = json.load(f)
            pc_done += len(data.get("completed_players", []))
    
    # Extra match shards
    extra_done = 0
    for i in range(8):
        pf = os.path.join(SCRIPT_DIR, "output", "extra_match_data", f"_shard_{i}_progress.json")
        if os.path.exists(pf):
            with open(pf, "r", encoding="utf-8") as f:
                data = json.load(f)
            extra_done += len(data.get("completed_players", []))
    
    return {
        "pc": {"done": pc_done, "total": pc_total},
        "extra": {"done": extra_done, "total": extra_total},
    }


def generate_report():
    """生成综合报告"""
    
    # 1. 加载所有数据
    leaderboard = load_leaderboard()
    match_ranks = load_match_ranks()
    extra_players = load_extra_players()
    shard_progress = load_shard_progress()
    
    # 2. 合并段位数据 (排行榜优先)
    all_ranks = {}
    
    # 先加入对局数据
    for pid, data in match_ranks.items():
        all_ranks[pid] = data
    
    # 排行榜覆盖
    for pid, data in leaderboard.items():
        all_ranks[pid] = data
    
    # 3. 统计
    rank_counts = Counter()
    rp_values = []
    sources = Counter()
    
    for pid, data in all_ranks.items():
        rank = data.get("rank", "unknown")
        rank_counts[rank] += 1
        rp = data.get("rankPoints", 0)
        if rp > 0:
            rp_values.append(rp)
        sources[data.get("source", "unknown")] += 1
    
    rp_values.sort()
    
    # 4. 采集进度统计
    done_pc = shard_progress["pc"]["done"]
    total_pc = shard_progress["pc"]["total"]
    done_extra = shard_progress["extra"]["done"]
    total_extra_shards = shard_progress["extra"]["total"]
    
    # 5. 段位顺序和颜色
    rank_order = [
        ("champion", "#FFD700", "冠军"),
        ("diamond-i", "#b9f2ff", "钻石 I"),
        ("diamond-ii", "#7dd8f0", "钻石 II"),
        ("diamond-iii", "#4cb8d9", "钻石 III"),
        ("diamond-iv", "#2a9cc0", "钻石 IV"),
        ("diamond-v", "#1a80a5", "钻石 V"),
        ("emerald-i", "#50C878", "翡翠 I"),
        ("emerald-ii", "#3CB371", "翡翠 II"),
        ("emerald-iii", "#2E8B57", "翡翠 III"),
        ("emerald-iv", "#228B22", "翡翠 IV"),
        ("emerald-v", "#1B6B1B", "翡翠 V"),
        ("platinum-i", "#E5E4E2", "铂金 I"),
        ("platinum-ii", "#C0C0C0", "铂金 II"),
        ("platinum-iii", "#A9A9A9", "铂金 III"),
        ("platinum-iv", "#909090", "铂金 IV"),
        ("platinum-v", "#787878", "铂金 V"),
        ("gold-i", "#FFD700", "金 I"),
        ("gold-ii", "#DAA520", "金 II"),
        ("gold-iii", "#B8860B", "金 III"),
        ("gold-iv", "#996515", "金 IV"),
        ("gold-v", "#806000", "金 V"),
        ("silver-i", "#C0C0C0", "银 I"),
        ("silver-ii", "#A8A8A8", "银 II"),
        ("silver-iii", "#909090", "银 III"),
        ("silver-iv", "#787878", "银 IV"),
        ("silver-v", "#606060", "银 V"),
        ("bronze-i", "#CD7F32", "铜 I"),
        ("bronze-ii", "#B87333", "铜 II"),
        ("bronze-iii", "#A0682D", "铜 III"),
        ("bronze-iv", "#8B5A2B", "铜 IV"),
        ("bronze-v", "#754C24", "铜 V"),
        ("copper-i", "#B87333", "紫铜 I"),
        ("copper-ii", "#A0682D", "紫铜 II"),
        ("copper-iii", "#8B5A2B", "紫铜 III"),
        ("copper-iv", "#754C24", "紫铜 IV"),
        ("copper-v", "#5E3D1C", "紫铜 V"),
        ("unranked", "#666666", "未定级"),
    ]
    
    total = len(all_ranks)
    total_extra_players = len(extra_players)
    uncovered = total_extra_players - len(set(all_ranks.keys()) & set(p["profileId"] for p in extra_players))
    
    # 构建表格行
    rows_html = ""
    for rank_key, color, rank_label in rank_order:
        count = rank_counts.get(rank_key, 0)
        if count > 0:
            pct = count / total * 100
            rows_html += f"""
            <tr>
                <td><span class="rank-badge" style="background:{color};color:{'#000' if color in ['#FFD700','#E5E4E2','#C0C0C0','#b9f2ff','#7dd8f0'] else '#fff'}">{rank_label}</span></td>
                <td class="rank-key">{rank_key}</td>
                <td class="count">{count:,}</td>
                <td class="pct">{pct:.2f}%</td>
                <td><div class="bar" style="width:{pct*3}px;background:{color}"></div></td>
            </tr>"""
    
    # RP 统计
    rp_min = min(rp_values) if rp_values else 0
    rp_max = max(rp_values) if rp_values else 0
    rp_avg = sum(rp_values) / len(rp_values) if rp_values else 0
    rp_median = rp_values[len(rp_values)//2] if rp_values else 0
    
    # 生成 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>R6S 段位分布分析报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}}
h1 {{ 
    text-align: center;
    font-size: 2em;
    margin: 30px 0;
    background: linear-gradient(135deg, #FFD700, #b9f2ff, #50C878);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.subtitle {{ text-align: center; color: #888; margin-bottom: 30px; }}
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 20px 0 30px 0;
}}
.stat-card {{
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}}
.stat-card .number {{
    font-size: 2em;
    font-weight: bold;
    color: #FFD700;
}}
.stat-card .label {{
    color: #888;
    font-size: 0.9em;
    margin-top: 5px;
}}
.section {{ 
    background: #12121e;
    border: 1px solid #2a2a3e;
    border-radius: 12px;
    padding: 25px;
    margin: 20px 0;
}}
.section h2 {{
    font-size: 1.3em;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #333;
}}
table {{ 
    width: 100%;
    border-collapse: collapse;
}}
th, td {{ 
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #1e1e2e;
}}
th {{ 
    color: #888;
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
}}
.rank-badge {{
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}}
.rank-key {{ color: #666; font-family: monospace; font-size: 0.85em; }}
.count {{ font-weight: 600; text-align: right; }}
.pct {{ color: #aaa; text-align: right; }}
.bar {{ 
    height: 20px;
    border-radius: 4px;
    min-width: 3px;
    opacity: 0.8;
}}
.progress-section {{
    background: #12121e;
    border: 1px solid #2a2a3e;
    border-radius: 12px;
    padding: 25px;
    margin: 20px 0;
}}
.progress-bar-container {{
    background: #1a1a2e;
    border-radius: 8px;
    overflow: hidden;
    height: 30px;
    margin: 10px 0;
}}
.progress-bar-fill {{
    height: 100%;
    background: linear-gradient(90deg, #50C878, #FFD700);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8em;
    font-weight: bold;
    color: #000;
    transition: width 0.5s;
}}
.note {{
    background: #1a1a2e;
    border-left: 3px solid #FFD700;
    padding: 15px 20px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
    color: #ccc;
    font-size: 0.9em;
}}
.note strong {{ color: #FFD700; }}
.rp-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
.rp-item {{ text-align: center; padding: 10px; background: #1a1a2e; border-radius: 8px; }}
.rp-item .value {{ font-size: 1.5em; font-weight: bold; color: #b9f2ff; }}
.rp-item .label {{ color: #888; font-size: 0.8em; }}
</style>
</head>
<body>

<h1>🏆 Rainbow Six Siege 段位分布分析</h1>
<p class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据来源: stats.cc 排行榜 + 对局数据</p>

<div class="stats-grid">
    <div class="stat-card">
        <div class="number">{total:,}</div>
        <div class="label">已知段位玩家</div>
    </div>
    <div class="stat-card">
        <div class="number">{total_extra_players:,}</div>
        <div class="label">待查段位玩家</div>
    </div>
    <div class="stat-card">
        <div class="number">{total + total_extra_players:,}</div>
        <div class="label">总玩家数</div>
    </div>
    <div class="stat-card">
        <div class="number">{total/(total+total_extra_players)*100:.1f}%</div>
        <div class="label">段位覆盖率</div>
    </div>
</div>

<div class="note">
    <strong>⚠️ 数据说明:</strong> 当前已知段位数据主要来自 stats.cc 排行榜 (PC Top 10,000)，
    因此分布高度集中在 Diamond III+ 段位。63,199 个从对局中发现的额外玩家尚未获取段位信息。
    这些额外玩家大多是排行榜玩家的对手和队友，预计包含更多低段位玩家（Platinum、Gold 甚至更低），
    完整分布需等待采集完成或 Ubisoft API 限速解除后批量查询。
</div>

<div class="section">
    <h2>📊 已知玩家段位分布</h2>
    <table>
        <thead>
            <tr><th>段位</th><th>ID</th><th style="text-align:right">人数</th><th style="text-align:right">占比</th><th>分布</th></tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</div>

<div class="section">
    <h2>📈 RP (排名分数) 分布</h2>
    <div class="rp-stats">
        <div class="rp-item"><div class="value">{rp_min:,}</div><div class="label">最低 RP</div></div>
        <div class="rp-item"><div class="value">{rp_max:,}</div><div class="label">最高 RP</div></div>
        <div class="rp-item"><div class="value">{rp_avg:,.0f}</div><div class="label">平均 RP</div></div>
        <div class="rp-item"><div class="value">{rp_median:,}</div><div class="label">中位 RP</div></div>
    </div>
</div>

<div class="progress-section">
    <h2>📋 数据采集进度</h2>
    
    <h3 style="margin:15px 0 5px 0;">PC 排行榜玩家 (对局数据)</h3>
    <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width:{done_pc/max(total_pc,1)*100:.1f}%">
            {done_pc:,}/{total_pc:,} ({done_pc/max(total_pc,1)*100:.1f}%)
        </div>
    </div>
    
    <h3 style="margin:15px 0 5px 0;">额外玩家 (对局数据 + 段位)</h3>
    <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width:{done_extra/max(total_extra_shards,1)*100:.1f}%">
            {done_extra:,}/{total_extra_shards:,} ({done_extra/max(total_extra_shards,1)*100:.1f}%)
        </div>
    </div>
    
    <p style="margin-top:15px;color:#888;font-size:0.85em;">
        采集进程会同时获取每个玩家的段位信息，完成后即可看到完整段位分布。
    </p>
</div>

<div class="section">
    <h2>💡 数据来源说明</h2>
    <table>
        <thead><tr><th>来源</th><th style="text-align:right">玩家数</th><th>说明</th></tr></thead>
        <tbody>
            <tr><td>排行榜 (leaderboard)</td><td class="count">{sources.get('leaderboard', 0):,}</td><td>stats.cc PC 排行榜 Top 10,000 (Diamond III+)</td></tr>
            <tr><td>对局数据 (match_data)</td><td class="count">{sources.get('match_data', 0):,}</td><td>已采集对局中的 source_player 段位</td></tr>
            <tr><td>待获取</td><td class="count">{uncovered:,}</td><td>额外发现的对手/队友，段位尚未获取</td></tr>
        </tbody>
    </table>
</div>

<div class="note">
    <strong>🔄 快速段位查询:</strong> 已创建 <code>fast_rank_fetch.py</code> 脚本使用 Ubisoft 官方 API 批量查询段位。
    目前 IP 因多次认证尝试被限速 (429)，等限速解除后（约 10-30 分钟）重新运行即可在 ~20 分钟内获取所有 63,199 个额外玩家的段位。
    <br><br>
    运行方式: <code>python data/scraper/fast_rank_fetch.py</code>
</div>

</body>
</html>"""
    
    # 保存 HTML
    output_path = os.path.join(SCRIPT_DIR, "..", "..", "rank_distribution_overview.html")
    output_path = os.path.normpath(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已保存: {output_path}")
    
    # 同时保存 JSON
    json_path = os.path.join(SCRIPT_DIR, "output", "rank_data")
    os.makedirs(json_path, exist_ok=True)
    
    distribution = {
        "generated_at": datetime.now().isoformat(),
        "total_players_with_rank": total,
        "total_extra_unranked": uncovered,
        "sources": dict(sources),
        "rank_distribution": {},
        "rp_stats": {
            "min": rp_min, "max": rp_max,
            "avg": round(rp_avg, 1), "median": rp_median,
        },
        "collection_progress": {
            "pc_shards": {"done": done_pc, "total": total_pc},
            "extra_shards": {"done": done_extra, "total": total_extra_shards},
        },
    }
    
    for rank_key, _, _ in rank_order:
        count = rank_counts.get(rank_key, 0)
        if count > 0:
            distribution["rank_distribution"][rank_key] = {
                "count": count,
                "percentage": round(count / total * 100, 2),
            }
    
    with open(os.path.join(json_path, "rank_distribution.json"), "w", encoding="utf-8") as f:
        json.dump(distribution, f, ensure_ascii=False, indent=2)
    
    print(f"JSON 已保存: {os.path.join(json_path, 'rank_distribution.json')}")
    
    # 控制台摘要
    print(f"\n{'='*60}")
    print(f"  段位分布摘要")
    print(f"{'='*60}")
    print(f"  已知段位: {total:,} 玩家")
    print(f"  待查段位: {uncovered:,} 玩家")
    print(f"  采集进度: PC {done_pc}/{total_pc}, Extra {done_extra}/{total_extra_shards}")
    print()
    for rank_key, _, rank_label in rank_order:
        count = rank_counts.get(rank_key, 0)
        if count > 0:
            pct = count / total * 100
            print(f"  {rank_label:<12} {count:>6,} ({pct:>6.2f}%)")


if __name__ == "__main__":
    generate_report()

"""
测试：额外玩家的对局是否会带来新的玩家和新的比赛数据？

思路：
1. 从已收集的额外玩家中随机挑几个
2. 访问他们的 stats.cc 主页，获取他们的比赛列表
3. 检查这些比赛中：
   a. 有多少比赛ID已经存在于我们PC排行榜玩家的数据中（重叠）
   b. 有多少比赛ID是全新的（新增数据）
   c. 比赛中的参与者有多少是新的（不在我们已知的玩家列表中）
"""

import json
import glob
import os
import sys
import time
import random
import urllib.request
import re
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. 加载已有数据：已知玩家ID集合 + 已知比赛ID集合
# ============================================================
def load_known_data():
    """加载所有已知的玩家ID和比赛ID"""
    known_players = set()
    known_matches = set()
    
    # 加载PC排行榜玩家
    lb_file = os.path.join(BASE_DIR, "output/leaderboard/leaderboard_full.json")
    if os.path.exists(lb_file):
        with open(lb_file, "r", encoding="utf-8") as f:
            lb_data = json.load(f)
            for p in lb_data:
                pid = p.get("profileId") or p.get("profile_id") or p.get("id", "")
                if pid:
                    known_players.add(pid.lower())
    
    # 加载额外玩家列表
    extra_file = os.path.join(BASE_DIR, "output/extra_match_data/_extra_players.json")
    if os.path.exists(extra_file):
        with open(extra_file, "r", encoding="utf-8") as f:
            extra_data = json.load(f)
            for p in extra_data:
                pid = p.get("profileId") or p.get("profile_id") or p.get("id", "")
                if pid:
                    known_players.add(pid.lower())
    
    # 加载已收集的比赛ID（从PC分片）
    for shard_file in glob.glob(os.path.join(BASE_DIR, "output/match_data/shard_*/match_details.json")):
        try:
            with open(shard_file, "r", encoding="utf-8") as f:
                matches = json.load(f)
                for m in matches:
                    mid = m.get("match_id") or m.get("matchId") or m.get("id", "")
                    if mid:
                        known_matches.add(mid.lower())
        except Exception as e:
            print(f"  Warning: Failed to read {shard_file}: {e}")
    
    # 加载已收集的比赛ID（从Extra分片）
    for shard_file in glob.glob(os.path.join(BASE_DIR, "output/extra_match_data/shard_*/match_details.json")):
        try:
            with open(shard_file, "r", encoding="utf-8") as f:
                matches = json.load(f)
                for m in matches:
                    mid = m.get("match_id") or m.get("matchId") or m.get("id", "")
                    if mid:
                        known_matches.add(mid.lower())
        except Exception as e:
            print(f"  Warning: Failed to read {shard_file}: {e}")
    
    return known_players, known_matches


# ============================================================
# 2. 从额外玩家中挑选测试样本
# ============================================================
def pick_test_players(n=5):
    """从已完成的额外玩家中随机选几个来测试"""
    # 进度文件中 completed_players 是纯UUID字符串列表
    # 需要对照 _extra_players.json 获取 displayName
    
    # 加载extra_players映射: profileId -> displayName
    extra_file = os.path.join(BASE_DIR, "output/extra_match_data/_extra_players.json")
    id_to_name = {}
    if os.path.exists(extra_file):
        with open(extra_file, "r", encoding="utf-8") as f:
            extra_data = json.load(f)
            for p in extra_data:
                pid = p.get("profileId", "")
                name = p.get("displayName", "")
                if pid and name:
                    id_to_name[pid.lower()] = name
    
    # 从进度文件获取已完成的玩家UUID
    completed_ids = set()
    for prog_file in glob.glob(os.path.join(BASE_DIR, "output/extra_match_data/_shard_*_progress.json")):
        try:
            with open(prog_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for pid in data.get("completed_players", []):
                    if isinstance(pid, str):
                        completed_ids.add(pid.lower())
        except:
            pass
    
    # 匹配已完成的玩家到名字
    completed = []
    for pid in completed_ids:
        name = id_to_name.get(pid, "")
        if name:
            completed.append({"id": pid, "name": name})
    
    # 如果已完成的不够，从extra_players列表中随机选
    if len(completed) < n:
        for pid, name in id_to_name.items():
            if pid not in completed_ids:
                completed.append({"id": pid, "name": name})
            if len(completed) >= n * 3:
                break
    
    random.shuffle(completed)
    return completed[:n]


# ============================================================
# 3. Nuxt SSR 数据解析（与现有爬虫相同的方式）
# ============================================================
def fetch_page(url):
    """获取页面HTML"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=20)
    return resp.read().decode("utf-8")


def extract_nuxt_data(html):
    """从HTML中提取Nuxt SSR数据"""
    # 查找 <script type="application/json" id="__NUXT_DATA__"...>
    pattern = r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None
    
    try:
        raw = json.loads(match.group(1))
    except:
        return None
    
    # Nuxt的deref解引用
    def deref(idx, visited=None):
        if visited is None:
            visited = set()
        if idx in visited or idx < 0 or idx >= len(raw):
            return None
        visited.add(idx)
        
        val = raw[idx]
        if isinstance(val, (str, int, float, bool)) or val is None:
            return val
        if isinstance(val, list):
            return [deref(i, set(visited)) for i in val if isinstance(i, int)]
        if isinstance(val, dict):
            # Nuxt用特殊格式表示对象
            result = {}
            keys = list(val.keys())
            for k in keys:
                v = val[k]
                if isinstance(v, int):
                    result[k] = deref(v, set(visited))
                else:
                    result[k] = v
            return result
        return val
    
    return raw, deref


def extract_matches_from_player_page(html):
    """从玩家页面提取比赛列表和参与者"""
    nuxt = extract_nuxt_data(html)
    if not nuxt:
        return [], []
    
    raw, deref = nuxt
    matches = []
    all_players_in_matches = []
    
    # 搜索match相关数据
    for i, item in enumerate(raw):
        if isinstance(item, str) and len(item) == 36 and item.count('-') == 4:
            # 可能是UUID (match_id 或 player_id)
            pass
    
    # 更直接的方法：搜索包含matchId或match_id的对象
    for i, item in enumerate(raw):
        if isinstance(item, dict):
            keys = set(item.keys())
            # 查找比赛对象
            if 'matchId' in keys or 'match_id' in keys or ('id' in keys and 'rounds' in keys):
                try:
                    resolved = deref(i)
                    if resolved and isinstance(resolved, dict):
                        mid = resolved.get('matchId') or resolved.get('match_id') or resolved.get('id', '')
                        if mid and len(str(mid)) > 10:
                            matches.append(resolved)
                except:
                    pass
            
            # 查找包含玩家列表的对象
            if 'players' in keys or 'participants' in keys or 'teams' in keys:
                try:
                    resolved = deref(i)
                    if resolved and isinstance(resolved, dict):
                        players = resolved.get('players') or resolved.get('participants') or []
                        if isinstance(players, list):
                            for p in players:
                                if isinstance(p, dict):
                                    pid = p.get('profileId') or p.get('profile_id') or p.get('id', '')
                                    if pid:
                                        all_players_in_matches.append(pid)
                except:
                    pass
    
    return matches, all_players_in_matches


def extract_match_ids_from_page(html):
    """更简单直接的方法：从HTML中提取所有看起来像match链接的UUID"""
    # 方法1: 从href中提取match链接
    match_ids = set()
    player_ids = set()
    
    # 查找 /siege/match/ 链接
    for m in re.finditer(r'/siege/match/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', html, re.I):
        match_ids.add(m.group(1).lower())
    
    # 查找 /siege/player/ 链接中的玩家名
    player_names = set()
    for m in re.finditer(r'/siege/player/([^"\'<>\s/]+)', html):
        player_names.add(m.group(1))
    
    # 从Nuxt数据中提取UUID格式的ID
    nuxt_result = extract_nuxt_data(html)
    if nuxt_result:
        raw, deref = nuxt_result
        for i, item in enumerate(raw):
            if isinstance(item, str) and len(item) == 36:
                parts = item.split('-')
                if len(parts) == 5 and all(len(p) in (8,4,4,4,12) for p in parts):
                    # 这是一个UUID，可能是match_id或player_id
                    # 通常player_id和match_id都是UUID格式
                    pass  # 我们通过上下文判断
        
        # 尝试从Nuxt数据中找到结构化的比赛和玩家数据
        for i, item in enumerate(raw):
            if isinstance(item, dict):
                # 找到包含profileId的对象
                if 'profileId' in item:
                    try:
                        resolved = deref(i)
                        if resolved:
                            pid = resolved.get('profileId', '')
                            if pid:
                                player_ids.add(pid.lower())
                    except:
                        pass
    
    return match_ids, player_ids, player_names


# ============================================================
# 4. 主测试流程
# ============================================================
def main():
    print("=" * 70)
    print("额外玩家数据深度分析测试")
    print("=" * 70)
    
    # 加载已知数据
    print("\n[1/4] 加载已知数据集...")
    known_players, known_matches = load_known_data()
    print(f"  已知玩家数: {len(known_players):,}")
    print(f"  已知比赛数: {len(known_matches):,}")
    
    # 挑选测试玩家
    print("\n[2/4] 选择测试用的额外玩家...")
    test_players = pick_test_players(8)
    if not test_players:
        print("  错误：未找到可测试的额外玩家！")
        return
    print(f"  选择了 {len(test_players)} 个额外玩家进行测试:")
    for p in test_players:
        print(f"    - {p['name']} ({p['id'][:8]}...)")
    
    # 逐个测试
    print("\n[3/4] 逐个访问额外玩家的 stats.cc 页面...")
    results = []
    
    for idx, player in enumerate(test_players):
        name = player["name"]
        pid = player["id"]
        print(f"\n  --- 测试玩家 {idx+1}/{len(test_players)}: {name} ---")
        
        url = f"https://stats.cc/siege/player/{name}"
        try:
            time.sleep(2.0 + random.uniform(0.5, 1.5))  # 礼貌延迟
            html = fetch_page(url)
            print(f"  页面大小: {len(html):,} bytes")
            
            match_ids, player_ids_in_page, player_names = extract_match_ids_from_page(html)
            
            # 统计
            new_matches = match_ids - known_matches
            overlapping_matches = match_ids & known_matches
            new_players = player_ids_in_page - known_players
            
            result = {
                "name": name,
                "id": pid,
                "total_matches_found": len(match_ids),
                "overlapping_matches": len(overlapping_matches),
                "new_matches": len(new_matches),
                "overlap_rate": len(overlapping_matches) / len(match_ids) * 100 if match_ids else 0,
                "total_players_in_page": len(player_ids_in_page),
                "new_players": len(new_players),
                "player_names_in_page": len(player_names),
                "new_match_ids": list(new_matches)[:5],  # 保留几个样本
            }
            results.append(result)
            
            print(f"  比赛数: {len(match_ids)} (重叠: {len(overlapping_matches)}, 新增: {len(new_matches)}, 重叠率: {result['overlap_rate']:.1f}%)")
            print(f"  页面中的玩家ID: {len(player_ids_in_page)} (新发现: {len(new_players)})")
            print(f"  页面中的玩家名: {len(player_names)}")
            
        except Exception as e:
            print(f"  请求失败: {e}")
            results.append({"name": name, "id": pid, "error": str(e)})
    
    # 汇总分析
    print("\n" + "=" * 70)
    print("[4/4] 汇总分析")
    print("=" * 70)
    
    valid = [r for r in results if "error" not in r]
    if not valid:
        print("所有测试都失败了！")
        return
    
    total_matches_found = sum(r["total_matches_found"] for r in valid)
    total_overlapping = sum(r["overlapping_matches"] for r in valid)
    total_new = sum(r["new_matches"] for r in valid)
    total_new_players = sum(r["new_players"] for r in valid)
    
    avg_overlap_rate = sum(r["overlap_rate"] for r in valid) / len(valid) if valid else 0
    
    print(f"\n测试玩家数: {len(valid)} (成功) / {len(results)} (总计)")
    print(f"\n--- 比赛重叠分析 ---")
    print(f"  发现的总比赛数: {total_matches_found}")
    print(f"  已存在的比赛: {total_overlapping} ({total_overlapping/total_matches_found*100:.1f}%)" if total_matches_found else "  无")
    print(f"  全新的比赛: {total_new} ({total_new/total_matches_found*100:.1f}%)" if total_matches_found else "  无")
    print(f"  平均重叠率: {avg_overlap_rate:.1f}%")
    
    print(f"\n--- 新玩家发现 ---")
    print(f"  在额外玩家对局中发现的新玩家ID: {total_new_players}")
    
    print(f"\n--- 对方案C的影响评估 ---")
    if avg_overlap_rate >= 80:
        print(f"  ✅ 重叠率 {avg_overlap_rate:.1f}% >= 80%，方案C损失较小")
        print(f"  每个额外玩家平均带来 {total_new/len(valid):.1f} 场全新比赛")
        new_per_player = total_new / len(valid) if valid else 0
        print(f"  如果采集全部63,199个额外玩家的比赛详情，预计可获得 ~{int(new_per_player * 63199):,} 场新比赛")
        print(f"  这些新比赛可能包含的新玩家: ~{total_new_players / len(valid) * 63199:,.0f}")
    elif avg_overlap_rate >= 50:
        print(f"  ⚠️ 重叠率 {avg_overlap_rate:.1f}%，方案C会丢失较多数据")
        print(f"  建议保留比赛详情爬取，但可以考虑方案A降低延迟")
    else:
        print(f"  ❌ 重叠率仅 {avg_overlap_rate:.1f}%，方案C会导致大量数据丢失！")
        print(f"  强烈建议保留完整的比赛详情爬取")
    
    # 计算如果每场新比赛都爬取详情的额外开销
    if total_new > 0 and valid:
        avg_new_per_player = total_new / len(valid)
        total_extra_requests = avg_new_per_player * 63199  # 额外的请求数
        time_per_req = 1.8  # 优化后每请求秒数(方案A)
        extra_hours = total_extra_requests * time_per_req / 3600 / 8  # 8个分片
        print(f"\n--- 折中方案: 只爬新比赛 ---")
        print(f"  平均每人 {avg_new_per_player:.1f} 场新比赛需要爬取详情")
        print(f"  总额外请求: ~{int(total_extra_requests):,}")
        print(f"  额外耗时(8分片, 方案A延迟): ~{extra_hours:.1f} 小时")

    # 保存详细结果
    output_file = os.path.join(BASE_DIR, "_test_extra_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"summary": {
            "test_count": len(valid),
            "total_matches": total_matches_found,
            "overlapping": total_overlapping,
            "new_matches": total_new,
            "avg_overlap_rate": avg_overlap_rate,
            "new_players": total_new_players,
        }, "details": results}, f, indent=2, ensure_ascii=False)
    print(f"\n详细结果已保存到: {output_file}")


if __name__ == "__main__":
    main()

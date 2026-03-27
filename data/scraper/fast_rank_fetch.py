"""
快速批量获取所有玩家段位信息
使用 Ubisoft 官方 API 批量查询 (profile_ids 逗号分隔)

预计时间: 
  - ~63,000 个额外玩家 + ~10,000 排行榜玩家
  - 每次批量查 50 个，共 ~1,460 批
  - 每批 ~0.5s + 间隔 ~0.3s ≈ 每批 0.8s
  - 总计 ~20 分钟

数据源:
  - output/extra_match_data/_extra_players.json (63,199 个)
  - output/leaderboard/leaderboard_full.json (10,015 个，已有段位)

输出:
  - output/rank_data/all_player_ranks.json
  - output/rank_data/rank_distribution.json
  - output/rank_data/fetch_progress.json
"""

import os
import sys
import io
import json
import time
import base64
import glob
import urllib.request
import urllib.error
import ssl
from datetime import datetime
from collections import Counter

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 设置同时输出到文件和控制台的日志
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "rank_fetch_log.txt")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

_log_file_handle = open(LOG_FILE, "w", encoding="utf-8")
_original_print = print

def print(*args, **kwargs):
    """同时输出到控制台和日志文件"""
    _original_print(*args, **kwargs)
    # 也写到日志文件
    try:
        kwargs_copy = dict(kwargs)
        kwargs_copy["file"] = _log_file_handle
        _original_print(*args, **kwargs_copy)
        _log_file_handle.flush()
    except Exception:
        pass

# ==================== 配置 ====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output", "rank_data")
EXTRA_PLAYERS_FILE = os.path.join(SCRIPT_DIR, "output", "extra_match_data", "_extra_players.json")
LEADERBOARD_FILE = os.path.join(SCRIPT_DIR, "output", "leaderboard", "leaderboard_full.json")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "fetch_progress.json")
RANKS_FILE = os.path.join(OUTPUT_DIR, "all_player_ranks.json")
DISTRIBUTION_FILE = os.path.join(OUTPUT_DIR, "rank_distribution.json")

# Ubisoft API 配置
CONNECT_APP_ID = "3587dcbb-7f81-457c-9781-0e3f29f6f56a"
R6S_APP_ID = "e3d5ea9e-50bd-43b7-88bf-39794f4e3d40"
AUTH_URL = "https://public-ubiservices.ubi.com/v3/profiles/sessions"
SPACE_ID_PC = "5172a557-50b5-4665-b7db-e3f2e8c5041d"
NEW_SPACE_ID = "0d2ae42d-4c27-4cb7-af6c-2099062302bb"
SANDBOX_ID_PC = "OSBOR_PC_LNCH_A"

BATCH_SIZE = 50  # 每次查询的玩家数
REQUEST_DELAY = 0.35  # 请求间隔(秒)
MAX_RETRIES = 3
RETRY_DELAY = 5  # 重试间隔(秒)

# 段位名称映射 (Ubisoft API rank_id -> 段位名)
RANK_MAP = {
    0: "unranked",
    1: "copper-v", 2: "copper-iv", 3: "copper-iii", 4: "copper-ii", 5: "copper-i",
    6: "bronze-v", 7: "bronze-iv", 8: "bronze-iii", 9: "bronze-ii", 10: "bronze-i",
    11: "silver-v", 12: "silver-iv", 13: "silver-iii", 14: "silver-ii", 15: "silver-i",
    16: "gold-v", 17: "gold-iv", 18: "gold-iii", 19: "gold-ii", 20: "gold-i",
    21: "platinum-v", 22: "platinum-iv", 23: "platinum-iii", 24: "platinum-ii", 25: "platinum-i",
    26: "emerald-v", 27: "emerald-iv", 28: "emerald-iii", 29: "emerald-ii", 30: "emerald-i",
    31: "diamond-v", 32: "diamond-iv", 33: "diamond-iii", 34: "diamond-ii", 35: "diamond-i",
    36: "champion",
}

# SSL context
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


# ==================== 凭据读取 ====================

def load_credentials():
    """从 creds 目录的文件名解码 Ubisoft 凭据"""
    creds_dir = os.path.join(SCRIPT_DIR, "..", "..", "creds")
    creds_dir = os.path.normpath(creds_dir)
    
    if not os.path.isdir(creds_dir):
        return None, None
    
    for fname in os.listdir(creds_dir):
        if fname.endswith(".json"):
            # 文件名是 base64(email:password)
            name_without_ext = fname.replace(".json", "")
            try:
                decoded = base64.b64decode(name_without_ext).decode("utf-8")
                if ":" in decoded and "@" in decoded:
                    email, password = decoded.split(":", 1)
                    return email, password
            except Exception:
                continue
    
    # 回退到环境变量
    email = os.environ.get("UBI_EMAIL", "")
    password = os.environ.get("UBI_PASSWORD", "")
    if email and password:
        return email, password
    
    return None, None


# ==================== HTTP 请求 ====================

def http_request(method, url, headers, body=None):
    """通用 HTTP 请求"""
    if body and isinstance(body, (dict, list)):
        body = json.dumps(body).encode("utf-8")
    elif body and isinstance(body, str):
        body = body.encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=20) as resp:
            data = resp.read().decode("utf-8")
            try:
                return json.loads(data), resp.status
            except json.JSONDecodeError:
                return {"_raw": data[:500]}, resp.status
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        try:
            return json.loads(body_text), e.code
        except Exception:
            return {"_raw": body_text[:500], "_http_code": e.code}, e.code
    except Exception as e:
        return {"_error": str(e)}, 0


# ==================== Ubisoft API ====================

def authenticate(email, password, app_id=None, label=""):
    """Ubisoft 认证，获取 ticket (含重试)"""
    use_app_id = app_id or CONNECT_APP_ID
    credentials = base64.b64encode(f"{email}:{password}".encode()).decode()
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Ubi-AppId": use_app_id,
        "Authorization": f"Basic {credentials}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Connection": "Keep-Alive",
    }
    
    for attempt in range(5):  # 最多重试5次
        result, status = http_request("POST", AUTH_URL, headers, {"rememberMe": True})
        
        if result.get("ticket"):
            return {
                "ticket": result["ticket"],
                "session_id": result.get("sessionId", ""),
                "profile_id": result.get("profileId", ""),
                "user_id": result.get("userId", ""),
                "expiration": result.get("expiration", ""),
                "app_id": use_app_id,
            }
        elif status == 429:
            wait = 15 * (attempt + 1)
            print(f"  ⚠️ [{label}] 429 限速，等待 {wait}s 后重试 ({attempt + 1}/5)...")
            time.sleep(wait)
        else:
            print(f"  ❌ [{label}] 认证失败 (HTTP {status}): {result.get('message', str(result)[:200])}")
            return None
    
    print(f"  ❌ [{label}] 认证重试耗尽")
    return None


def dual_authenticate(email, password):
    """双重认证: R6S AppId (优先) + Connect AppId"""
    # 先认证 R6S (段位API需要用这个)
    print("  🔑 认证 #1: R6S PC (段位API主要需要)...")
    auth_r6s = authenticate(email, password, R6S_APP_ID, "R6S")
    if auth_r6s:
        print(f"  ✅ R6S 认证成功!")
    
    time.sleep(5)  # 间隔 5 秒避免 429 限速
    
    print("  🔑 认证 #2: Ubisoft Connect (备用)...")
    auth_connect = authenticate(email, password, CONNECT_APP_ID, "Connect")
    if auth_connect:
        print(f"  ✅ Connect 认证成功!")
    
    return auth_connect, auth_r6s


def make_headers(auth_info, app_id=None):
    """构造请求头"""
    return {
        "Authorization": f"Ubi_v1 t={auth_info['ticket']}",
        "Ubi-AppId": app_id or auth_info.get("app_id", CONNECT_APP_ID),
        "Ubi-SessionId": auth_info["session_id"],
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Connection": "Keep-Alive",
    }


def fetch_ranks_v1(profile_ids, headers, space_id=None):
    """
    使用 v1 API 批量获取段位
    GET /v1/spaces/{spaceId}/sandboxes/{sandboxId}/r6karma/players?
        board_id=pvp_ranked&season_id=-1&region_id=global&profile_ids=id1,id2,...
    """
    sid = space_id or SPACE_ID_PC
    ids_str = ",".join(profile_ids)
    url = (
        f"https://public-ubiservices.ubi.com/v1/spaces/{sid}/sandboxes/{SANDBOX_ID_PC}"
        f"/r6karma/players?board_id=pvp_ranked&season_id=-1&region_id=global"
        f"&profile_ids={ids_str}"
    )
    
    result, status = http_request("GET", url, headers)
    return result, status


def fetch_ranks_v2(profile_ids, headers, space_id=None):
    """
    使用 v2 API 批量获取段位
    GET /v2/spaces/{spaceId}/title/r6s/skill/full_profiles?
        profile_ids=id1,id2,...&platform_families=pc
    """
    sid = space_id or NEW_SPACE_ID
    ids_str = ",".join(profile_ids)
    url = (
        f"https://public-ubiservices.ubi.com/v2/spaces/{sid}/title/r6s"
        f"/skill/full_profiles?profile_ids={ids_str}&platform_families=pc"
    )
    
    result, status = http_request("GET", url, headers)
    return result, status


def parse_v1_response(result, profile_ids):
    """解析 v1 API 响应"""
    ranks = {}
    players_data = result.get("players", {})
    
    for pid in profile_ids:
        player = players_data.get(pid, {})
        if player:
            rank_id = player.get("rank", 0)
            rank_name = RANK_MAP.get(rank_id, f"rank_{rank_id}")
            ranks[pid] = {
                "rank": rank_name,
                "rank_id": rank_id,
                "rankPoints": player.get("mmr", player.get("skill_mean", 0)),
                "max_rank": RANK_MAP.get(player.get("max_rank", 0), "unknown"),
                "max_rank_id": player.get("max_rank", 0),
                "max_mmr": player.get("max_mmr", 0),
                "season": player.get("season", -1),
                "wins": player.get("wins", 0),
                "losses": player.get("losses", 0),
                "abandons": player.get("abandons", 0),
                "source": "ubisoft_v1",
            }
        else:
            ranks[pid] = {
                "rank": "unranked",
                "rank_id": 0,
                "rankPoints": 0,
                "source": "ubisoft_v1_empty",
            }
    
    return ranks


def parse_v2_response(result, profile_ids):
    """解析 v2 API 响应"""
    ranks = {}
    
    # v2 格式: {"platform_families_full_profiles": [{"board_ids_full_profiles": [...]}]}
    families = result.get("platform_families_full_profiles", [])
    
    # 构建 profile_id -> rank 映射
    for family in families:
        boards = family.get("board_ids_full_profiles", [])
        for board in boards:
            if board.get("board_id") == "ranked":
                seasons = board.get("full_profiles", [])
                for season in seasons:
                    pid = season.get("profile", {}).get("id") or season.get("profile_id", "")
                    if pid:
                        rank_id = season.get("season_statistics", {}).get("rank", 0)
                        rank_name = RANK_MAP.get(rank_id, f"rank_{rank_id}")
                        rp = season.get("season_statistics", {}).get("rank_points", 0)
                        max_rank_id = season.get("season_statistics", {}).get("max_rank", 0)
                        ranks[pid] = {
                            "rank": rank_name,
                            "rank_id": rank_id,
                            "rankPoints": rp,
                            "max_rank": RANK_MAP.get(max_rank_id, "unknown"),
                            "max_rank_id": max_rank_id,
                            "max_rankPoints": season.get("season_statistics", {}).get("max_rank_points", 0),
                            "source": "ubisoft_v2",
                        }
    
    # 填充未找到的
    for pid in profile_ids:
        if pid not in ranks:
            ranks[pid] = {
                "rank": "unranked",
                "rank_id": 0,
                "rankPoints": 0,
                "source": "ubisoft_v2_empty",
            }
    
    return ranks


# ==================== 数据加载 ====================

def load_extra_players():
    """加载额外玩家列表"""
    if not os.path.exists(EXTRA_PLAYERS_FILE):
        print(f"  ❌ 找不到额外玩家文件: {EXTRA_PLAYERS_FILE}")
        return []
    
    with open(EXTRA_PLAYERS_FILE, "r", encoding="utf-8") as f:
        players = json.load(f)
    
    return players


def load_leaderboard():
    """加载排行榜数据 (已有段位)"""
    if not os.path.exists(LEADERBOARD_FILE):
        print(f"  ⚠️ 排行榜文件不存在，跳过")
        return {}
    
    with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
        players = json.load(f)
    
    ranks = {}
    for p in players:
        pid = p.get("profileId")
        if pid:
            ranks[pid] = {
                "rank": p.get("rank", "unknown"),
                "rank_id": -1,  # 排行榜不给 rank_id
                "rankPoints": p.get("rankPoints", 0),
                "displayName": p.get("displayName", ""),
                "source": "leaderboard",
            }
    
    return ranks


def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_ids": [], "batch_index": 0, "total_batches": 0}


def save_progress(progress):
    """保存进度"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)


def load_existing_ranks():
    """加载已有段位数据"""
    if os.path.exists(RANKS_FILE):
        with open(RANKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_ranks(ranks):
    """保存段位数据"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(RANKS_FILE, "w", encoding="utf-8") as f:
        json.dump(ranks, f, ensure_ascii=False, indent=1)


# ==================== 段位分布统计 ====================

def generate_distribution(all_ranks, player_name_map):
    """生成段位分布统计"""
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
    
    # 段位顺序
    rank_order = [
        "champion", "diamond-i", "diamond-ii", "diamond-iii", "diamond-iv", "diamond-v",
        "emerald-i", "emerald-ii", "emerald-iii", "emerald-iv", "emerald-v",
        "platinum-i", "platinum-ii", "platinum-iii", "platinum-iv", "platinum-v",
        "gold-i", "gold-ii", "gold-iii", "gold-iv", "gold-v",
        "silver-i", "silver-ii", "silver-iii", "silver-iv", "silver-v",
        "bronze-i", "bronze-ii", "bronze-iii", "bronze-iv", "bronze-v",
        "copper-i", "copper-ii", "copper-iii", "copper-iv", "copper-v",
        "unranked",
    ]
    
    total = len(all_ranks)
    
    distribution = {
        "generated_at": datetime.now().isoformat(),
        "total_players": total,
        "sources": dict(sources),
        "rank_distribution": {},
        "rp_stats": {},
    }
    
    # 按顺序排列段位
    for rank in rank_order:
        count = rank_counts.get(rank, 0)
        if count > 0:
            distribution["rank_distribution"][rank] = {
                "count": count,
                "percentage": round(count / total * 100, 2) if total > 0 else 0,
            }
    
    # 加上未在预定义列表中的段位
    for rank, count in rank_counts.items():
        if rank not in rank_order:
            distribution["rank_distribution"][rank] = {
                "count": count,
                "percentage": round(count / total * 100, 2) if total > 0 else 0,
            }
    
    # RP 统计
    if rp_values:
        rp_values.sort()
        distribution["rp_stats"] = {
            "min": min(rp_values),
            "max": max(rp_values),
            "avg": round(sum(rp_values) / len(rp_values), 1),
            "median": rp_values[len(rp_values) // 2],
            "p25": rp_values[len(rp_values) // 4],
            "p75": rp_values[3 * len(rp_values) // 4],
        }
    
    return distribution


# ==================== 主逻辑 ====================

def main():
    print("=" * 70)
    print("  🏆 Rainbow Six Siege 快速批量段位查询")
    print("=" * 70)
    print()
    
    # 1. 加载凭据
    print("📋 步骤 1: 加载凭据...")
    email, password = load_credentials()
    if not email or not password:
        print("  ❌ 找不到 Ubisoft 凭据！")
        print("  请设置环境变量 UBI_EMAIL / UBI_PASSWORD")
        print("  或在 creds/ 目录放置 base64(email:password).json 文件")
        sys.exit(1)
    print(f"  ✅ 凭据已加载: {email[:3]}***@{email.split('@')[1] if '@' in email else '***'}")
    print()
    
    # 2. 加载数据
    print("📋 步骤 2: 加载玩家列表...")
    
    # 加载排行榜 (已有段位数据)
    leaderboard_ranks = load_leaderboard()
    print(f"  ✅ 排行榜: {len(leaderboard_ranks)} 个玩家 (已有段位)")
    
    # 加载额外玩家
    extra_players = load_extra_players()
    print(f"  ✅ 额外玩家: {len(extra_players)} 个 (需要查询段位)")
    
    # 合并: 排行榜玩家的 profileId 集合
    leaderboard_ids = set(leaderboard_ranks.keys())
    
    # 需要查询的: 额外玩家中不在排行榜里的
    to_query = []
    already_have = 0
    for p in extra_players:
        pid = p.get("profileId")
        if pid and pid not in leaderboard_ids:
            to_query.append({
                "profileId": pid,
                "displayName": p.get("displayName", ""),
            })
        else:
            already_have += 1
    
    print(f"  📊 排行榜已覆盖 {already_have} 个额外玩家")
    print(f"  📊 需要查询: {len(to_query)} 个玩家")
    print()
    
    # 3. 加载已有进度
    existing_ranks = load_existing_ranks()
    progress = load_progress()
    
    # 过滤掉已查询的
    completed_set = set(progress.get("completed_ids", []))
    # 也加入已有结果
    for pid in existing_ranks:
        if existing_ranks[pid].get("source", "").startswith("ubisoft"):
            completed_set.add(pid)
    
    remaining = [p for p in to_query if p["profileId"] not in completed_set]
    
    if completed_set:
        print(f"  📋 已有 {len(completed_set)} 个API查询结果，继续从断点恢复...")
    print(f"  📋 剩余需查询: {len(remaining)} 个")
    
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    est_minutes = total_batches * (REQUEST_DELAY + 0.5) / 60
    print(f"  📋 预计分 {total_batches} 批，每批 {BATCH_SIZE} 个")
    print(f"  📋 预计耗时: {est_minutes:.1f} 分钟")
    print()
    
    if len(remaining) == 0:
        print("  ✅ 所有玩家已查询完毕！直接生成报告...")
        # 合并所有数据
        all_ranks = dict(leaderboard_ranks)
        all_ranks.update(existing_ranks)
        distribution = generate_distribution(all_ranks, {})
        save_distribution(distribution)
        print_distribution_summary(distribution)
        return
    
    # 4. 双重认证
    print("📋 步骤 3: Ubisoft API 双重认证...")
    auth_connect, auth_r6s = dual_authenticate(email, password)
    if not auth_connect and not auth_r6s:
        print("  ❌ 两种认证都失败了，请检查凭据")
        sys.exit(1)
    print()
    
    # 5. 测试所有可能的 API 端点组合
    print("📋 步骤 4: 测试 API 端点 (多种组合)...")
    test_ids = [remaining[0]["profileId"]]
    if len(remaining) > 1:
        test_ids.append(remaining[1]["profileId"])
    
    # 尝试所有组合: (api_version, space_id, auth_info, app_id_for_request, label)
    test_combos = []
    
    if auth_connect:
        test_combos.extend([
            ("v1_old", SPACE_ID_PC, auth_connect, CONNECT_APP_ID, "v1+OldSpace+Connect"),
            ("v2_old", SPACE_ID_PC, auth_connect, CONNECT_APP_ID, "v2+OldSpace+Connect"),
            ("v2_new", NEW_SPACE_ID, auth_connect, CONNECT_APP_ID, "v2+NewSpace+Connect"),
        ])
    
    if auth_r6s:
        test_combos.extend([
            ("v1_old", SPACE_ID_PC, auth_r6s, R6S_APP_ID, "v1+OldSpace+R6S"),
            ("v2_old", SPACE_ID_PC, auth_r6s, R6S_APP_ID, "v2+OldSpace+R6S"),
            ("v2_new", NEW_SPACE_ID, auth_r6s, R6S_APP_ID, "v2+NewSpace+R6S"),
        ])
    
    # 交叉测试: R6S token + Connect AppId
    if auth_r6s:
        test_combos.extend([
            ("v2_new", NEW_SPACE_ID, auth_r6s, CONNECT_APP_ID, "v2+NewSpace+R6Stoken+ConnectAppId"),
            ("v2_old", SPACE_ID_PC, auth_r6s, CONNECT_APP_ID, "v2+OldSpace+R6Stoken+ConnectAppId"),
        ])
    if auth_connect:
        test_combos.extend([
            ("v2_new", NEW_SPACE_ID, auth_connect, R6S_APP_ID, "v2+NewSpace+ConnectToken+R6SAppId"),
        ])
    
    ids_str = ",".join(test_ids)
    best_combo = None
    
    for api_ver, space_id, auth, app_id, label in test_combos:
        headers_test = make_headers(auth, app_id)
        
        if api_ver.startswith("v1"):
            url = (
                f"https://public-ubiservices.ubi.com/v1/spaces/{space_id}/sandboxes/{SANDBOX_ID_PC}"
                f"/r6karma/players?board_id=pvp_ranked&season_id=-1&region_id=global"
                f"&profile_ids={ids_str}"
            )
        else:
            url = (
                f"https://public-ubiservices.ubi.com/v2/spaces/{space_id}/title/r6s"
                f"/skill/full_profiles?profile_ids={ids_str}&platform_families=pc"
            )
        
        result, status = http_request("GET", url, headers_test)
        
        # 判断成功
        ok = False
        if api_ver.startswith("v1"):
            ok = status == 200 and result.get("players")
        else:
            ok = status == 200 and not result.get("errorCode") and not result.get("_raw", "").startswith("r6s-ubisoft")
        
        icon = "✅" if ok else "❌"
        print(f"  {icon} [{label}] HTTP {status}")
        
        if ok and not best_combo:
            best_combo = (api_ver, space_id, auth, app_id, label)
            print(f"     🎯 这个可用! 将使用此组合")
            # 打印返回数据预览
            preview = json.dumps(result, ensure_ascii=False)[:300]
            print(f"     预览: {preview}")
        
        time.sleep(0.5)
    
    if not best_combo:
        print()
        print("  ❌ 所有 API 组合都不可用!")
        print("  可能原因: API 限速 / 接口彻底变更 / 账号问题")
        print("  尝试保存已有数据并生成报告...")
        all_ranks = dict(leaderboard_ranks)
        all_ranks.update(existing_ranks)
        save_ranks(all_ranks)
        distribution = generate_distribution(all_ranks, {})
        save_distribution(distribution)
        print_distribution_summary(distribution)
        return
    
    api_ver, space_id, auth_info, app_id, combo_label = best_combo
    use_v2 = api_ver.startswith("v2")
    api_label = api_ver
    headers = make_headers(auth_info, app_id)
    print(f"\n  📌 将使用 [{combo_label}] 进行批量查询")
    print()
    
    # 6. 批量查询
    print(f"📋 步骤 5: 批量获取段位 ({len(remaining)} 个玩家)...")
    print("-" * 70)
    
    # 构建 displayName 映射
    name_map = {}
    for p in remaining:
        name_map[p["profileId"]] = p.get("displayName", "")
    
    all_ranks = dict(leaderboard_ranks)
    all_ranks.update(existing_ranks)
    
    success_count = 0
    error_count = 0
    rate_limit_count = 0
    
    start_time = time.time()
    auth_refresh_time = start_time
    
    for batch_idx in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[batch_idx:batch_idx + BATCH_SIZE]
        batch_ids = [p["profileId"] for p in batch]
        batch_num = batch_idx // BATCH_SIZE + 1
        
        # 每 30 分钟刷新认证
        if time.time() - auth_refresh_time > 1800:
            print("\n  🔄 刷新认证 ticket...")
            new_auth = authenticate(email, password, app_id, "refresh")
            if new_auth:
                auth_info = new_auth
                headers = make_headers(auth_info, app_id)
                auth_refresh_time = time.time()
                print("  ✅ 认证已刷新")
            else:
                print("  ❌ 认证刷新失败，尝试继续...")
        
        # 发送请求
        retries = 0
        batch_ranks = None
        
        while retries < MAX_RETRIES:
            try:
                if use_v2:
                    result, status = fetch_ranks_v2(batch_ids, headers, space_id)
                    if status == 200 and not result.get("errorCode") and not result.get("_raw", "").startswith("r6s-ubisoft"):
                        batch_ranks = parse_v2_response(result, batch_ids)
                        break
                else:
                    result, status = fetch_ranks_v1(batch_ids, headers, space_id)
                    if status == 200:
                        batch_ranks = parse_v1_response(result, batch_ids)
                        break
                
                if status == 429:
                    rate_limit_count += 1
                    wait_time = RETRY_DELAY * (retries + 1) * 2
                    print(f"  ⚠️ 429 限速! 等待 {wait_time}s... (第 {rate_limit_count} 次)")
                    time.sleep(wait_time)
                    retries += 1
                elif status == 401:
                    # ticket 过期，重新认证
                    print("  🔄 401 未授权，重新认证...")
                    new_auth = authenticate(email, password, app_id, "re-auth")
                    if new_auth:
                        auth_info = new_auth
                        headers = make_headers(auth_info, app_id)
                        auth_refresh_time = time.time()
                    retries += 1
                else:
                    print(f"  ⚠️ HTTP {status}, 重试 ({retries + 1}/{MAX_RETRIES})...")
                    time.sleep(RETRY_DELAY)
                    retries += 1
                    
            except Exception as e:
                print(f"  ❌ 异常: {e}, 重试...")
                time.sleep(RETRY_DELAY)
                retries += 1
        
        if batch_ranks:
            # 合并结果
            for pid, rank_data in batch_ranks.items():
                rank_data["displayName"] = name_map.get(pid, "")
                all_ranks[pid] = rank_data
                completed_set.add(pid)
            
            success_count += len(batch_ranks)
        else:
            error_count += len(batch_ids)
            # 标记为失败但已尝试
            for pid in batch_ids:
                all_ranks[pid] = {
                    "rank": "query_failed",
                    "rank_id": -1,
                    "rankPoints": 0,
                    "displayName": name_map.get(pid, ""),
                    "source": "failed",
                }
                completed_set.add(pid)
        
        # 进度输出
        elapsed = time.time() - start_time
        total_done = batch_idx + len(batch)
        pct = total_done / len(remaining) * 100
        speed = total_done / elapsed if elapsed > 0 else 0
        eta = (len(remaining) - total_done) / speed if speed > 0 else 0
        
        if batch_num % 10 == 0 or batch_num <= 3 or batch_num == total_batches:
            print(
                f"  批次 {batch_num}/{total_batches} | "
                f"{total_done}/{len(remaining)} ({pct:.1f}%) | "
                f"✅ {success_count} ❌ {error_count} | "
                f"速度 {speed:.1f}/s | "
                f"剩余 {eta/60:.1f}min"
            )
        
        # 定期保存 (每 100 批)
        if batch_num % 100 == 0:
            save_ranks(all_ranks)
            progress["completed_ids"] = list(completed_set)
            progress["batch_index"] = batch_idx
            progress["total_batches"] = total_batches
            save_progress(progress)
        
        # 请求间隔
        time.sleep(REQUEST_DELAY)
    
    # 7. 最终保存
    print()
    print("-" * 70)
    total_elapsed = time.time() - start_time
    print(f"📋 批量查询完成! 耗时 {total_elapsed/60:.1f} 分钟")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失败: {error_count}")
    print(f"  ⚠️ 限速: {rate_limit_count} 次")
    print()
    
    # 保存最终结果
    save_ranks(all_ranks)
    progress["completed_ids"] = list(completed_set)
    progress["status"] = "completed"
    progress["completed_at"] = datetime.now().isoformat()
    save_progress(progress)
    
    # 8. 生成分布报告
    print("📋 步骤 6: 生成段位分布报告...")
    distribution = generate_distribution(all_ranks, name_map)
    save_distribution(distribution)
    print_distribution_summary(distribution)
    
    print()
    print("=" * 70)
    print("  ✅ 完成! 数据已保存到:")
    print(f"     段位数据: {RANKS_FILE}")
    print(f"     分布统计: {DISTRIBUTION_FILE}")
    print(f"     进度文件: {PROGRESS_FILE}")
    print("=" * 70)


def save_distribution(distribution):
    """保存分布数据"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(DISTRIBUTION_FILE, "w", encoding="utf-8") as f:
        json.dump(distribution, f, ensure_ascii=False, indent=2)


def print_distribution_summary(distribution):
    """打印分布摘要"""
    print()
    print("  " + "=" * 60)
    print("  🏆 段位分布总览")
    print("  " + "=" * 60)
    print(f"  总玩家数: {distribution['total_players']}")
    print()
    
    # 数据来源
    print("  📊 数据来源:")
    for source, count in distribution.get("sources", {}).items():
        print(f"     {source}: {count}")
    print()
    
    # 段位分布
    print("  📊 段位分布:")
    print(f"  {'段位':<20} {'人数':>8} {'占比':>8}")
    print("  " + "-" * 40)
    
    for rank, info in distribution.get("rank_distribution", {}).items():
        count = info["count"]
        pct = info["percentage"]
        bar = "█" * max(1, int(pct / 2))
        print(f"  {rank:<20} {count:>8,} {pct:>7.2f}% {bar}")
    
    # RP 统计
    rp = distribution.get("rp_stats", {})
    if rp:
        print()
        print("  📊 RP 分布:")
        print(f"     最低: {rp.get('min', 'N/A')}")
        print(f"     最高: {rp.get('max', 'N/A')}")
        print(f"     平均: {rp.get('avg', 'N/A')}")
        print(f"     中位: {rp.get('median', 'N/A')}")
        print(f"     P25:  {rp.get('p25', 'N/A')}")
        print(f"     P75:  {rp.get('p75', 'N/A')}")


if __name__ == "__main__":
    main()

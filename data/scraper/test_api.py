"""
Ubisoft API 端点可用性测试脚本 (Python 版)

逐个测试各 Ubisoft 后端 API 端点，输出详细的可用性报告。

用法（PowerShell）：
  $env:UBI_EMAIL = "your_email"
  $env:UBI_PASSWORD = "your_password"
  python data/scraper/test_api.py
"""

import os
import sys
import io
import json
import time
import base64
import urllib.request
import urllib.error
import ssl

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==================== 常量 ====================

UBISOFT_APP_ID = "3587dcbb-7f81-457c-9781-0e3f29f6f56a"  # Ubisoft Connect App ID (verified working)
AUTH_URL = "https://public-ubiservices.ubi.com/v3/profiles/sessions"

SPACE_ID_PC = "5172a557-50b5-4665-b7db-e3f2e8c5041d"
SANDBOX_ID_PC = "OSBOR_PC_LNCH_A"

# 忽略 SSL 证书问题（某些企业网络环境）
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ==================== 工具函数 ====================

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"


def separator(title):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print("═" * 60)


def print_json(obj, max_length=800):
    s = json.dumps(obj, indent=2, ensure_ascii=False)
    if len(s) > max_length:
        print(s[:max_length] + "\n  ... (truncated)")
    else:
        print(s)


def http_request(method, url, headers=None, body=None):
    """通用 HTTP 请求"""
    if headers is None:
        headers = {}

    if body and isinstance(body, (dict, list)):
        body = json.dumps(body).encode("utf-8")
    elif body and isinstance(body, str):
        body = body.encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
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


# ==================== 认证 ====================


def authenticate(email, password):
    """登录 Ubisoft 获取 ticket"""
    # Basic Auth = base64(email:password)
    credentials = base64.b64encode(f"{email}:{password}".encode()).decode()

    headers = {
        "Content-Type": "application/json",
        "Ubi-AppId": UBISOFT_APP_ID,
        "Authorization": f"Basic {credentials}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    body = {"rememberMe": True}

    result, status = http_request("POST", AUTH_URL, headers, body)
    return result, status


def make_auth_headers(ticket, session_id):
    """构造认证后的请求头"""
    return {
        "Authorization": f"Ubi_v1 t={ticket}",
        "Ubi-AppId": UBISOFT_APP_ID,
        "Ubi-SessionId": session_id,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def auth_get(url, headers):
    """认证后的 GET 请求"""
    return http_request("GET", url, headers)


# ==================== 测试 ====================


def run_tests():
    email = os.environ.get("UBI_EMAIL", "")
    password = os.environ.get("UBI_PASSWORD", "")

    if not email or not password:
        print("""
请先设置环境变量（PowerShell）：

  $env:UBI_EMAIL = "your_email@example.com"
  $env:UBI_PASSWORD = "your_password"
  python data/scraper/test_api.py
        """)
        sys.exit(1)

    results = []

    # ---------- 1. 认证测试 ----------
    separator("1. 认证测试 (Authentication)")
    print(f"  Email: {email}")

    auth_result, auth_status = authenticate(email, password)

    ticket = auth_result.get("ticket")
    session_id = auth_result.get("sessionId")
    expiration = auth_result.get("expiration")

    if ticket:
        print(f"{PASS} 认证成功！HTTP {auth_status}")
        print(f"   Ticket: {ticket[:30]}...")
        print(f"   SessionId: {session_id}")
        print(f"   Expiration: {expiration}")
        print(f"   ProfileId: {auth_result.get('profileId', 'N/A')}")
        print(f"   UserId: {auth_result.get('userId', 'N/A')}")
        results.append({"test": "Authentication", "status": "PASS"})
    else:
        print(f"{FAIL} 认证失败 (HTTP {auth_status}):")
        print_json(auth_result)
        results.append({"test": "Authentication", "status": "FAIL", "error": str(auth_result)})
        print("\n无法继续后续测试。请检查邮箱/密码是否正确，以及 2FA 是否已关闭。")
        print_report(results)
        return

    headers = make_auth_headers(ticket, session_id)

    # ---------- 2. 玩家搜索测试 ----------
    separator("2. 玩家搜索测试 (Player Search)")
    test_usernames = ["Beaulo.TSM", "Pengu", "Canadian"]
    found_profile_id = None

    for username in test_usernames:
        print(f"\n  搜索: \"{username}\"")
        url = f"https://public-ubiservices.ubi.com/v3/profiles?nameOnPlatform={username}&platformType=uplay"
        result, status = auth_get(url, headers)

        profiles = result.get("profiles", [])
        if profiles:
            p = profiles[0]
            found_profile_id = p.get("profileId")
            print(f"  {PASS} 找到 {len(profiles)} 个结果 (HTTP {status})")
            print(f"     名称: {p.get('nameOnPlatform')}")
            print(f"     ProfileId: {found_profile_id}")
            print(f"     Platform: {p.get('platformType')}")
            results.append({"test": f"Player Search ({username})", "status": "PASS"})
            break
        elif result.get("errorCode"):
            print(f"  {FAIL} API 错误 (HTTP {status}): code={result.get('errorCode')}")
            results.append({"test": f"Player Search ({username})", "status": "FAIL"})
        else:
            print(f"  {WARN} 未找到或响应异常 (HTTP {status}):")
            print_json(result, 300)
            results.append({"test": f"Player Search ({username})", "status": "WARN"})

        time.sleep(1)

    if not found_profile_id:
        # 备用 profileId
        found_profile_id = "621be942-39b4-4f5e-8ef2-f1f5cfe28258"
        print(f"\n{INFO} 使用备用 profileId: {found_profile_id}")

    # ---------- 3. 玩家基础统计 ----------
    separator("3. 玩家基础统计 (Player Stats Summary)")
    stats_url = (
        f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
        f"/playerstats2/statistics?populations={found_profile_id}"
        f"&statistics=casualpvp_kills,casualpvp_death,casualpvp_matchlost,casualpvp_matchwon,"
        f"casualpvp_timeplayed,rankedpvp_kills,rankedpvp_death,rankedpvp_matchlost,"
        f"rankedpvp_matchwon,rankedpvp_timeplayed"
    )
    result, status = auth_get(stats_url, headers)
    if result.get("results") or (status == 200 and not result.get("errorCode")):
        print(f"{PASS} 基础统计获取成功 (HTTP {status})")
        print_json(result)
        results.append({"test": "Player Stats Summary", "status": "PASS"})
    elif result.get("errorCode"):
        print(f"{FAIL} API 错误 (HTTP {status}): code={result['errorCode']}")
        print_json(result)
        results.append({"test": "Player Stats Summary", "status": "FAIL"})
    else:
        print(f"{WARN} 返回数据 (HTTP {status}):")
        print_json(result)
        results.append({"test": "Player Stats Summary", "status": "WARN"})

    time.sleep(1)

    # ---------- 4. 干员统计 ----------
    separator("4. 干员统计 (Operator Stats)")
    op_url = (
        f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
        f"/playerstats2/statistics?populations={found_profile_id}"
        f"&statistics=operatorpvp_kills,operatorpvp_death,operatorpvp_roundwon,"
        f"operatorpvp_roundlost,operatorpvp_timeplayed"
    )
    result, status = auth_get(op_url, headers)
    if result.get("results") or (status == 200 and not result.get("errorCode")):
        print(f"{PASS} 干员统计获取成功 (HTTP {status})")
        print_json(result)
        results.append({"test": "Operator Stats", "status": "PASS"})
    elif result.get("errorCode"):
        print(f"{FAIL} API 错误 (HTTP {status}): code={result['errorCode']}")
        print_json(result)
        results.append({"test": "Operator Stats", "status": "FAIL"})
    else:
        print(f"{WARN} 返回数据 (HTTP {status}):")
        print_json(result)
        results.append({"test": "Operator Stats", "status": "WARN"})

    time.sleep(1)

    # ---------- 5. 段位数据 v1 ----------
    separator("5. 段位数据 v1 (Seasonal Rank)")
    rank_url = (
        f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
        f"/r6karma/players?board_id=pvp_ranked&season_id=-1&region_id=global"
        f"&profile_ids={found_profile_id}"
    )
    result, status = auth_get(rank_url, headers)
    if result.get("players") or (status == 200 and not result.get("errorCode")):
        print(f"{PASS} 段位数据获取成功 (HTTP {status})")
        print_json(result)
        results.append({"test": "Seasonal Rank v1", "status": "PASS"})
    elif result.get("errorCode"):
        print(f"{FAIL} API 错误 (HTTP {status}): code={result['errorCode']}")
        print_json(result)
        results.append({"test": "Seasonal Rank v1", "status": "FAIL"})
    else:
        print(f"{WARN} 返回数据 (HTTP {status}):")
        print_json(result)
        results.append({"test": "Seasonal Rank v1", "status": "WARN"})

    time.sleep(1)

    # ---------- 6. 段位数据 v2 ----------
    separator("6. 段位数据 v2 (Seasonal V2)")
    rank_v2_url = (
        f"https://public-ubiservices.ubi.com/v2/spaces/{SPACE_ID_PC}/title/r6s"
        f"/skill/full_profiles?profile_ids={found_profile_id}&platform_families=pc"
    )
    result, status = auth_get(rank_v2_url, headers)
    if status == 200 and not result.get("errorCode"):
        print(f"{PASS} V2 段位数据获取成功 (HTTP {status})")
        print_json(result)
        results.append({"test": "Seasonal Rank v2", "status": "PASS"})
    elif result.get("errorCode"):
        print(f"{FAIL} API 错误 (HTTP {status}): code={result['errorCode']}")
        print_json(result)
        results.append({"test": "Seasonal Rank v2", "status": "FAIL"})
    else:
        print(f"{WARN} 返回数据 (HTTP {status}):")
        print_json(result)
        results.append({"test": "Seasonal Rank v2", "status": "WARN"})

    time.sleep(1)

    # ---------- 7. 比赛历史 ⭐ ----------
    separator("7. 比赛历史 (Match History) ⭐ 关键端点")
    match_url = (
        f"https://public-ubiservices.ubi.com/v1/profiles/{found_profile_id}"
        f"/playedgames?spaceId={SPACE_ID_PC}&limit=5&offset=0"
    )
    result, status = auth_get(match_url, headers)
    if status == 200 and not result.get("errorCode"):
        print(f"{PASS} 比赛历史获取成功 (HTTP {status})")
        print_json(result)
        results.append({"test": "Match History", "status": "PASS"})
    elif result.get("errorCode"):
        print(f"{FAIL} API 错误 (HTTP {status}): code={result['errorCode']}")
        print_json(result)
        results.append({"test": "Match History", "status": "FAIL"})
    else:
        print(f"{WARN} 返回数据 (HTTP {status}):")
        print_json(result)
        results.append({"test": "Match History", "status": "WARN"})

    time.sleep(1)

    # ---------- 8. 排行榜 ----------
    separator("8. 排行榜 (Leaderboard)")
    lb_url = (
        f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
        f"/r6karma/player_skill_records?board_id=pvp_ranked&season_id=-1"
        f"&region_id=global&limit=5&offset=0"
    )
    result, status = auth_get(lb_url, headers)
    if status == 200 and not result.get("errorCode"):
        print(f"{PASS} 排行榜获取成功 (HTTP {status})")
        print_json(result)
        results.append({"test": "Leaderboard", "status": "PASS"})
    elif result.get("errorCode"):
        print(f"{FAIL} API 错误 (HTTP {status}): code={result['errorCode']}")
        print_json(result)
        results.append({"test": "Leaderboard", "status": "FAIL"})
    else:
        print(f"{WARN} 返回数据 (HTTP {status}):")
        print_json(result)
        results.append({"test": "Leaderboard", "status": "WARN"})

    time.sleep(1)

    # ---------- 9. 额外端点探测 ----------
    separator("9. 额外端点探测")

    extra_endpoints = [
        {
            "name": "Player Progress",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6playerprofile/playerprofile/progressions?profile_ids={found_profile_id}",
        },
        {
            "name": "Current Season Info",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6karma/seasons",
        },
        {
            "name": "Match Replay V2",
            "url": f"https://public-ubiservices.ubi.com/v2/spaces/{SPACE_ID_PC}"
                   f"/matches?profile_id={found_profile_id}&limit=5",
        },
        {
            "name": "Ubisoft Connect profile",
            "url": f"https://public-ubiservices.ubi.com/v3/profiles/{found_profile_id}",
        },
        {
            "name": "Game Metadata (R6 title stats)",
            "url": f"https://public-ubiservices.ubi.com/v1/profiles/{found_profile_id}"
                   f"/statscard?spaceId={SPACE_ID_PC}",
        },
    ]

    for ep in extra_endpoints:
        print(f"\n  测试: {ep['name']}")
        print(f"  URL: {ep['url'][:100]}...")
        result, status = auth_get(ep["url"], headers)

        if result.get("errorCode") or result.get("_http_code", 0) >= 400:
            print(f"  {FAIL} HTTP {status}, errorCode: {result.get('errorCode', 'N/A')}")
            print_json(result, 400)
            results.append({"test": ep["name"], "status": "FAIL"})
        elif result.get("_error"):
            print(f"  {FAIL} 请求失败: {result['_error']}")
            results.append({"test": ep["name"], "status": "FAIL"})
        else:
            print(f"  {PASS} HTTP {status} 有数据返回:")
            print_json(result, 500)
            results.append({"test": ep["name"], "status": "PASS"})

        time.sleep(0.8)

    # ---------- 最终报告 ----------
    print_report(results)


def print_report(results):
    separator("📋 端点可用性报告")
    print()

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    warned = [r for r in results if r["status"] == "WARN"]

    for r in results:
        icon = PASS if r["status"] == "PASS" else (FAIL if r["status"] == "FAIL" else WARN)
        extra = f" ({r['error']})" if "error" in r else ""
        print(f"  {icon} {r['test']}{extra}")

    print(f"\n  总计: {len(results)} 个测试")
    print(f"  {PASS} 通过: {len(passed)}")
    print(f"  {FAIL} 失败: {len(failed)}")
    print(f"  {WARN} 警告: {len(warned)}")

    print("\n" + "═" * 60)

    if passed:
        print("\n💡 建议下一步:")
        test_names = [r["test"] for r in passed]
        if "Match History" in test_names:
            print("  🎉 Match History 端点可用！可以直接获取对局数据。")
        if any("Leaderboard" in t for t in test_names):
            print("  📊 排行榜可用，可以从排行榜获取高段位玩家列表。")
        if any("Operator" in t for t in test_names):
            print("  🎮 干员统计可用，可以获取玩家的干员使用数据。")
        if any("Seasonal" in t or "Rank" in t for t in test_names):
            print("  🏆 段位数据可用，可以获取玩家排名信息。")

    # 保存报告到文件
    report_path = os.path.join(os.path.dirname(__file__), "output", "api_test_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📁 报告已保存到: {report_path}")


if __name__ == "__main__":
    run_tests()

"""
直接使用已获取的 ticket 测试所有端点（跳过认证步骤）
"""
import os, sys, io, json, time, urllib.request, urllib.error, ssl

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

APP_ID = "3587dcbb-7f81-457c-9781-0e3f29f6f56a"
SPACE_ID_PC = "5172a557-50b5-4665-b7db-e3f2e8c5041d"
SANDBOX_ID_PC = "OSBOR_PC_LNCH_A"


def separator(title):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print("═" * 60)


def print_json(obj, max_length=1200):
    s = json.dumps(obj, indent=2, ensure_ascii=False)
    if len(s) > max_length:
        print(s[:max_length] + "\n  ... (truncated)")
    else:
        print(s)


def http_get(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
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
        except:
            pass
        try:
            return json.loads(body_text), e.code
        except:
            return {"_raw": body_text[:500], "_http_code": e.code}, e.code
    except Exception as e:
        return {"_error": str(e)}, 0


def main():
    # --- 第一步：认证（获取新 ticket）---
    import base64
    email = os.environ.get("UBI_EMAIL", "")
    password = os.environ.get("UBI_PASSWORD", "")
    
    if not email or not password:
        print("请设置 UBI_EMAIL 和 UBI_PASSWORD 环境变量")
        sys.exit(1)

    separator("0. 认证")
    credentials = base64.b64encode(f"{email}:{password}".encode()).decode()
    auth_headers = {
        "Content-Type": "application/json",
        "Ubi-AppId": APP_ID,
        "Authorization": f"Basic {credentials}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    body = json.dumps({"rememberMe": True}).encode("utf-8")
    req = urllib.request.Request(
        "https://public-ubiservices.ubi.com/v3/profiles/sessions",
        data=body, headers=auth_headers, method="POST"
    )
    
    ticket = None
    session_id = None
    my_profile_id = None
    
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ticket = data.get("ticket")
            session_id = data.get("sessionId")
            my_profile_id = data.get("profileId")
            print(f"  {PASS} 认证成功!")
            print(f"  ProfileId: {my_profile_id}")
            print(f"  SessionId: {session_id}")
            print(f"  Ticket: {ticket[:50]}...")
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except:
            pass
        print(f"  {FAIL} 认证失败 HTTP {e.code}")
        print(f"  {body_text[:300]}")
        print(f"\n  {INFO} IP 还在被限速，请等几分钟后再试")
        return
    except Exception as e:
        print(f"  {FAIL} 异常: {e}")
        return

    headers = {
        "Authorization": f"Ubi_v1 t={ticket}",
        "Ubi-AppId": APP_ID,
        "Ubi-SessionId": session_id,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    results = [{"test": "Authentication", "status": "PASS"}]
    
    # --- 玩家搜索 ---
    separator("1. 玩家搜索 (Player Search)")
    test_names = ["Beaulo.TSM", "Pengu", "Canadian"]
    found_profile_id = None
    
    for name in test_names:
        print(f"\n  搜索: \"{name}\"")
        url = f"https://public-ubiservices.ubi.com/v3/profiles?nameOnPlatform={name}&platformType=uplay"
        result, status = http_get(url, headers)
        profiles = result.get("profiles", [])
        if profiles:
            p = profiles[0]
            found_profile_id = p.get("profileId")
            print(f"  {PASS} 找到 {len(profiles)} 个结果 (HTTP {status})")
            print(f"     名称: {p.get('nameOnPlatform')}")
            print(f"     ProfileId: {found_profile_id}")
            results.append({"test": f"Player Search ({name})", "status": "PASS"})
            break
        else:
            print(f"  {WARN} 未找到 (HTTP {status})")
            results.append({"test": f"Player Search ({name})", "status": "WARN"})
        time.sleep(0.5)
    
    if not found_profile_id:
        found_profile_id = "621be942-39b4-4f5e-8ef2-f1f5cfe28258"
        print(f"\n  {INFO} 使用备用 profileId: {found_profile_id}")

    pid = found_profile_id

    # --- 端点列表 ---
    tests = [
        {
            "name": "基础统计 (Player Stats)",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/playerstats2/statistics?populations={pid}"
                   f"&statistics=casualpvp_kills,casualpvp_death,casualpvp_matchlost,casualpvp_matchwon,"
                   f"rankedpvp_kills,rankedpvp_death,rankedpvp_matchlost,rankedpvp_matchwon",
        },
        {
            "name": "干员统计 (Operator Stats)",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/playerstats2/statistics?populations={pid}"
                   f"&statistics=operatorpvp_kills,operatorpvp_death,operatorpvp_roundwon,"
                   f"operatorpvp_roundlost,operatorpvp_timeplayed",
        },
        {
            "name": "段位 v1 (Ranked Karma)",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6karma/players?board_id=pvp_ranked&season_id=-1&region_id=global&profile_ids={pid}",
        },
        {
            "name": "段位 v2 (Skill Full Profiles)",
            "url": f"https://public-ubiservices.ubi.com/v2/spaces/{SPACE_ID_PC}/title/r6s"
                   f"/skill/full_profiles?profile_ids={pid}&platform_families=pc",
        },
        {
            "name": "⭐ 比赛历史 (Match History - playedgames)",
            "url": f"https://public-ubiservices.ubi.com/v1/profiles/{pid}"
                   f"/playedgames?spaceId={SPACE_ID_PC}&limit=5&offset=0",
        },
        {
            "name": "⭐ 比赛历史 v2 (Matches)",
            "url": f"https://public-ubiservices.ubi.com/v2/spaces/{SPACE_ID_PC}"
                   f"/matches?profile_id={pid}&limit=5",
        },
        {
            "name": "排行榜 (Leaderboard)",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6karma/player_skill_records?board_id=pvp_ranked&season_id=-1"
                   f"&region_id=global&limit=5&offset=0",
        },
        {
            "name": "玩家进度 (Player Progress)",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6playerprofile/playerprofile/progressions?profile_ids={pid}",
        },
        {
            "name": "赛季信息 (Season Info)",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6karma/seasons",
        },
        {
            "name": "玩家资料 (Profile)",
            "url": f"https://public-ubiservices.ubi.com/v3/profiles/{pid}",
        },
        {
            "name": "统计卡 (Stats Card)",
            "url": f"https://public-ubiservices.ubi.com/v1/profiles/{pid}"
                   f"/statscard?spaceId={SPACE_ID_PC}",
        },
    ]

    for i, test in enumerate(tests, 2):
        separator(f"{i}. {test['name']}")
        print(f"  URL: {test['url'][:120]}...")
        result, status = http_get(test["url"], headers)
        
        is_error = result.get("errorCode") or result.get("_http_code", 0) >= 400 or result.get("_error")
        
        if is_error:
            print(f"  {FAIL} HTTP {status}")
            if result.get("errorCode"):
                print(f"  ErrorCode: {result.get('errorCode')}, Msg: {result.get('message', 'N/A')}")
            print_json(result, 500)
            results.append({"test": test["name"], "status": "FAIL"})
        elif status == 200:
            print(f"  {PASS} HTTP {status} - 有数据返回!")
            print_json(result)
            results.append({"test": test["name"], "status": "PASS"})
        else:
            print(f"  {WARN} HTTP {status}")
            print_json(result, 500)
            results.append({"test": test["name"], "status": "WARN"})
        
        time.sleep(0.8)

    # --- 最终报告 ---
    separator("📋 端点可用性报告")
    print()
    
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    warned = [r for r in results if r["status"] == "WARN"]
    
    for r in results:
        icon = PASS if r["status"] == "PASS" else (FAIL if r["status"] == "FAIL" else WARN)
        print(f"  {icon} {r['test']}")
    
    print(f"\n  总计: {len(results)} 个测试")
    print(f"  {PASS} 通过: {len(passed)}")
    print(f"  {FAIL} 失败: {len(failed)}")
    print(f"  {WARN} 警告: {len(warned)}")
    print("═" * 60)
    
    if passed:
        print(f"\n💡 可用端点总结:")
        for r in passed:
            print(f"  🟢 {r['test']}")
    
    if failed:
        print(f"\n🔴 不可用端点:")
        for r in failed:
            print(f"  🔴 {r['test']}")
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), "output", "api_full_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📁 报告已保存到: {report_path}")


if __name__ == "__main__":
    main()

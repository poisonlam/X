"""
策略：用 Ubisoft Connect AppId 认证获取 ticket，
然后在后续请求中切换为 R6S PC AppId 来请求游戏数据
"""
import os, sys, io, json, time, base64, urllib.request, urllib.error, ssl

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

# 两个 AppId
CONNECT_APP_ID = "3587dcbb-7f81-457c-9781-0e3f29f6f56a"  # 用来认证
R6S_APP_ID = "e3d5ea9e-50bd-43b7-88bf-39794f4e3d40"      # 用来请求游戏数据

SPACE_ID_PC = "5172a557-50b5-4665-b7db-e3f2e8c5041d"
SANDBOX_ID_PC = "OSBOR_PC_LNCH_A"


def separator(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


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
    email = os.environ.get("UBI_EMAIL", "")
    password = os.environ.get("UBI_PASSWORD", "")
    
    if not email or not password:
        print("请设置 UBI_EMAIL 和 UBI_PASSWORD 环境变量")
        sys.exit(1)

    # === 认证 ===
    separator("0. 认证 (用 Ubisoft Connect AppId)")
    credentials = base64.b64encode(f"{email}:{password}".encode()).decode()
    auth_headers = {
        "Content-Type": "application/json",
        "Ubi-AppId": CONNECT_APP_ID,
        "Authorization": f"Basic {credentials}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    body = json.dumps({"rememberMe": True}).encode("utf-8")
    req = urllib.request.Request(
        "https://public-ubiservices.ubi.com/v3/profiles/sessions",
        data=body, headers=auth_headers, method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ticket = data.get("ticket")
            session_id = data.get("sessionId")
            profile_id = data.get("profileId")
            print(f"  {PASS} 认证成功! (Ubisoft Connect)")
            print(f"  ProfileId: {profile_id}")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8") if e else ""
        print(f"  {FAIL} 认证失败 HTTP {e.code}: {body_text[:200]}")
        return
    except Exception as e:
        print(f"  {FAIL} 异常: {e}")
        return

    time.sleep(1)

    # === 测试不同 AppId 组合 ===
    # 先搜个玩家
    separator("1. 玩家搜索")
    
    # 用 Connect AppId 搜索
    h_connect = {
        "Authorization": f"Ubi_v1 t={ticket}",
        "Ubi-AppId": CONNECT_APP_ID,
        "Ubi-SessionId": session_id,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    
    # 用 R6S AppId 搜索
    h_r6s = {
        "Authorization": f"Ubi_v1 t={ticket}",
        "Ubi-AppId": R6S_APP_ID,
        "Ubi-SessionId": session_id,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    pid = None
    url = "https://public-ubiservices.ubi.com/v3/profiles?nameOnPlatform=Pengu&platformType=uplay"
    
    for label, h in [("Connect AppId", h_connect), ("R6S AppId", h_r6s)]:
        print(f"\n  [{label}] 搜索 'Pengu'")
        result, status = http_get(url, h)
        profiles = result.get("profiles", [])
        if profiles:
            pid = profiles[0].get("profileId")
            print(f"  {PASS} 找到! ProfileId: {pid}")
        elif status == 429:
            print(f"  {WARN} 429 限速")
        else:
            print(f"  {FAIL} HTTP {status}: {json.dumps(result, ensure_ascii=False)[:200]}")
        time.sleep(0.5)

    if not pid:
        pid = "5e25fafc-35d1-4659-8d05-8acaa6e9ac1b"  # Pengu的已知ID
        print(f"\n  {INFO} 使用已知的 Pengu ProfileId: {pid}")

    time.sleep(1)

    # === 关键测试：用不同 AppId 请求游戏数据 ===
    test_urls = [
        {
            "name": "基础统计",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/playerstats2/statistics?populations={pid}"
                   f"&statistics=casualpvp_kills,casualpvp_death,rankedpvp_kills,rankedpvp_death",
        },
        {
            "name": "段位 v1",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6karma/players?board_id=pvp_ranked&season_id=-1&region_id=global&profile_ids={pid}",
        },
        {
            "name": "比赛历史",
            "url": f"https://public-ubiservices.ubi.com/v1/profiles/{pid}"
                   f"/playedgames?spaceId={SPACE_ID_PC}&limit=5&offset=0",
        },
        {
            "name": "玩家进度",
            "url": f"https://public-ubiservices.ubi.com/v1/spaces/{SPACE_ID_PC}/sandboxes/{SANDBOX_ID_PC}"
                   f"/r6playerprofile/playerprofile/progressions?profile_ids={pid}",
        },
    ]

    for i, test in enumerate(test_urls, 2):
        separator(f"{i}. {test['name']}")
        
        for label, h in [("Connect AppId", h_connect), ("R6S AppId", h_r6s)]:
            print(f"\n  [{label}]")
            result, status = http_get(test["url"], h)
            
            if result.get("errorCode"):
                print(f"  {FAIL} HTTP {status} - ErrorCode: {result.get('errorCode')}, Msg: {result.get('message', '')[:100]}")
            elif status == 200:
                print(f"  {PASS} HTTP {status} - 成功!")
                print_json(result, 600)
            elif status == 429:
                print(f"  {WARN} HTTP 429 限速")
            else:
                print(f"  {WARN} HTTP {status}")
                print_json(result, 300)
            
            time.sleep(0.8)

    # === 额外：尝试 r6api.js 使用的新版 URL ===
    separator("额外：尝试新版 API URL 格式")
    
    # r6api.js 可能使用 nimbus 端点
    new_urls = [
        {
            "name": "Stats via ubiservices v2",
            "url": f"https://public-ubiservices.ubi.com/v2/spaces/{SPACE_ID_PC}/title/r6s"
                   f"/skill/full_profiles?profile_ids={pid}&platform_families=pc",
        },
        {
            "name": "Profile applications",
            "url": f"https://public-ubiservices.ubi.com/v3/profiles/{pid}/applications",
        },
        {
            "name": "Nimbus stats",
            "url": f"https://nimbus.ubisoft.com/api/v1/spaces/{SPACE_ID_PC}"
                   f"/sandboxes/{SANDBOX_ID_PC}/playerstats2/statistics?populations={pid}"
                   f"&statistics=casualpvp_kills",
        },
    ]

    for test in new_urls:
        print(f"\n  {test['name']}")
        for label, h in [("Connect", h_connect), ("R6S", h_r6s)]:
            result, status = http_get(test["url"], h)
            is_ok = status == 200 and not result.get("errorCode")
            icon = PASS if is_ok else (WARN if status == 429 else FAIL)
            msg = ""
            if result.get("errorCode"):
                msg = f"err={result['errorCode']}"
            elif result.get("_error"):
                msg = result["_error"][:80]
            elif is_ok:
                msg = f"有数据! keys={list(result.keys())[:5]}"
            print(f"    [{label}] {icon} HTTP {status} {msg}")
            time.sleep(0.5)

    print("\n" + "=" * 60)
    print("  测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

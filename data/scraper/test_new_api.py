"""
基于 SwiftCODA/R6-API 源码逆向的最新 Ubisoft R6S API 端点测试

关键发现:
- V2 AppId (Ubisoft Connect): 3587dcbb-7f81-457c-9781-0e3f29f6f56a
- V3 AppId (R6S PC): e3d5ea9e-50bd-43b7-88bf-39794f4e3d40
- 新 Space ID: 0d2ae42d-4c27-4cb7-af6c-2099062302bb
- 统计端点: https://prod.datadev.ubisoft.com/v1/users/{userId}/playerstats
- 段位端点: https://public-ubiservices.ubi.com/v2/spaces/{spaceId}/title/r6s/skill/full_profiles
- 等级端点: https://public-ubiservices.ubi.com/v1/spaces/{spaceId}/title/r6s/rewards/public_profile
"""
import os, sys, io, json, time, base64, urllib.request, urllib.error, ssl, urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

# === 配置 ===
V2_APP_ID = "3587dcbb-7f81-457c-9781-0e3f29f6f56a"  # Ubisoft Connect
V3_APP_ID = "e3d5ea9e-50bd-43b7-88bf-39794f4e3d40"  # R6S PC

NEW_SPACE_ID = "0d2ae42d-4c27-4cb7-af6c-2099062302bb"  # 新的 R6S Space ID
PSN_SPACE_ID = "05bfb3f7-6c21-4c42-be1f-97a33fb5cf66"  # PSN Space ID (也用于 datadev 请求)

AUTH_URL = "https://public-ubiservices.ubi.com/v3/profiles/sessions"


def separator(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def print_json(obj, max_length=1500):
    s = json.dumps(obj, indent=2, ensure_ascii=False)
    if len(s) > max_length:
        print(s[:max_length] + "\n  ... (truncated)")
    else:
        print(s)


def http_request(method, url, headers, body=None):
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
        except:
            pass
        try:
            return json.loads(body_text), e.code
        except:
            return {"_raw": body_text[:500], "_http_code": e.code}, e.code
    except Exception as e:
        return {"_error": str(e)}, 0


def authenticate(email, password, app_id, label):
    """用指定 AppId 进行认证"""
    credentials = base64.b64encode(f"{email}:{password}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Ubi-AppId": app_id,
        "Authorization": f"Basic {credentials}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Connection": "Keep-Alive",
    }
    body = {"rememberMe": True}
    result, status = http_request("POST", AUTH_URL, headers, body)
    
    if result.get("ticket"):
        print(f"  {PASS} [{label}] 认证成功! (HTTP {status})")
        print(f"     Ticket: {result['ticket'][:50]}...")
        print(f"     SessionId: {result.get('sessionId')}")
        print(f"     ProfileId: {result.get('profileId')}")
        print(f"     UserId: {result.get('userId')}")
        return result
    else:
        print(f"  {FAIL} [{label}] 认证失败 (HTTP {status})")
        if result.get("message"):
            print(f"     Message: {result['message']}")
        return None


def main():
    email = os.environ.get("UBI_EMAIL", "")
    password = os.environ.get("UBI_PASSWORD", "")
    
    if not email or not password:
        print("请设置 UBI_EMAIL 和 UBI_PASSWORD 环境变量")
        sys.exit(1)

    results = []

    # ==================== 1. 双重认证 ====================
    separator("1. 双重认证 (V2 + V3)")
    
    token_v2 = authenticate(email, password, V2_APP_ID, "V2-Connect")
    time.sleep(2)  # 间隔避免限速
    token_v3 = authenticate(email, password, V3_APP_ID, "V3-R6S")
    
    if not token_v2:
        print(f"\n  {FAIL} V2 认证失败，无法继续")
        return
    
    results.append({"test": "Auth V2 (Connect)", "status": "PASS" if token_v2 else "FAIL"})
    results.append({"test": "Auth V3 (R6S)", "status": "PASS" if token_v3 else "FAIL"})

    # 构造请求头
    h_v2 = {
        "Authorization": f"ubi_v1 t={token_v2['ticket']}",
        "Ubi-AppId": V2_APP_ID,
        "Ubi-SessionId": token_v2.get("sessionId", ""),
        "Expiration": token_v2.get("expiration", ""),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Connection": "Keep-Alive",
    }
    
    h_v3 = None
    if token_v3:
        h_v3 = {
            "Authorization": f"ubi_v1 t={token_v3['ticket']}",
            "Ubi-AppId": V3_APP_ID,  # 注意 V3 某些端点实际上也用 V2 AppId
            "Ubi-SessionId": token_v3.get("sessionId", ""),
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Connection": "Keep-Alive",
        }
    
    time.sleep(1)

    # ==================== 2. 玩家搜索 ====================
    separator("2. 玩家搜索")
    
    # 试两个域名
    search_urls = [
        ("api-ubiservices.ubi.com", f"https://api-ubiservices.ubi.com/v3/profiles?nameOnPlatform=Pengu&platformType=uplay"),
        ("public-ubiservices.ubi.com", f"https://public-ubiservices.ubi.com/v3/profiles?nameOnPlatform=Pengu&platformType=uplay"),
    ]
    
    found_profile_id = None
    found_user_id = None
    
    for domain, url in search_urls:
        print(f"\n  [{domain}]")
        result, status = http_request("GET", url, h_v2)
        profiles = result.get("profiles", [])
        if profiles:
            p = profiles[0]
            found_profile_id = p.get("profileId")
            found_user_id = p.get("userId")
            print(f"  {PASS} 找到! (HTTP {status})")
            print(f"     名称: {p.get('nameOnPlatform')}")
            print(f"     ProfileId: {found_profile_id}")
            print(f"     UserId: {found_user_id}")
            print(f"     Platform: {p.get('platformType')}")
            results.append({"test": f"Player Search ({domain})", "status": "PASS"})
            break
        else:
            print(f"  {FAIL} HTTP {status}: {result.get('message', json.dumps(result)[:100])}")
            results.append({"test": f"Player Search ({domain})", "status": "FAIL"})
        time.sleep(0.5)
    
    if not found_user_id:
        found_profile_id = "5e25fafc-35d1-4659-8d05-8acaa6e9ac1b"
        found_user_id = "5e25fafc-35d1-4659-8d05-8acaa6e9ac1b"  # 可能相同
        print(f"\n  {INFO} 使用备用 ID")

    pid = found_profile_id
    uid = found_user_id

    time.sleep(1)

    # ==================== 3. 干员统计 (prod.datadev) ⭐ ====================
    separator("3. 干员统计 (prod.datadev.ubisoft.com) ⭐")
    
    params = {
        "spaceId": PSN_SPACE_ID,  # SwiftCODA 用的是 PSN SpaceId
        "gameMode": "all,ranked,casual,unranked",
        "view": "seasonal",
        "aggregation": "operators",
        "platform": "PC",
        "teamRole": "Attacker,Defender",
        "seasons": "Y9S1,Y9S2,Y8S4,Y8S3,Y8S2,Y8S1",
    }
    query = urllib.parse.urlencode(params)
    url = f"https://prod.datadev.ubisoft.com/v1/users/{uid}/playerstats?{query}"
    
    print(f"  URL: {url[:120]}...")
    result, status = http_request("GET", url, h_v2)
    
    if status == 200 and not result.get("errorCode"):
        print(f"  {PASS} HTTP {status} - 干员统计获取成功!")
        print_json(result)
        results.append({"test": "Operator Stats (datadev)", "status": "PASS"})
    else:
        print(f"  {FAIL} HTTP {status}")
        if result.get("errorCode"):
            print(f"     ErrorCode: {result.get('errorCode')}, Msg: {result.get('message', '')[:200]}")
        else:
            print_json(result, 500)
        results.append({"test": "Operator Stats (datadev)", "status": "FAIL"})

    time.sleep(1)

    # ==================== 4. 生涯统计 (prod.datadev) ====================
    separator("4. 生涯统计 (prod.datadev.ubisoft.com)")
    
    params_lifetime = {
        "spaceId": PSN_SPACE_ID,
        "gameMode": "all,ranked,casual,unranked",
        "view": "seasonal",
        "aggregation": "summary",
        "platform": "PC",
        "teamRole": "all",
        "seasons": "Y9S1,Y9S2,Y8S4,Y8S3",
    }
    query2 = urllib.parse.urlencode(params_lifetime)
    url2 = f"https://prod.datadev.ubisoft.com/v1/users/{uid}/playerstats?{query2}"
    
    print(f"  URL: {url2[:120]}...")
    result, status = http_request("GET", url2, h_v2)
    
    if status == 200 and not result.get("errorCode"):
        print(f"  {PASS} HTTP {status} - 生涯统计获取成功!")
        print_json(result)
        results.append({"test": "Lifetime Stats (datadev)", "status": "PASS"})
    else:
        print(f"  {FAIL} HTTP {status}")
        if result.get("errorCode"):
            print(f"     ErrorCode: {result.get('errorCode')}, Msg: {result.get('message', '')[:200]}")
        else:
            print_json(result, 500)
        results.append({"test": "Lifetime Stats (datadev)", "status": "FAIL"})

    time.sleep(1)

    # ==================== 5. 段位数据 v2 (新 SpaceId) ====================
    separator("5. 段位数据 v2 (新 Space ID)")
    
    rank_url = (
        f"https://public-ubiservices.ubi.com/v2/spaces/{NEW_SPACE_ID}/title/r6s"
        f"/skill/full_profiles?platform_families=pc,console&profile_ids={uid}"
    )
    
    # 用 V3 token + V3 AppId (如 SwiftCODA 源码)
    h_rank = h_v3 if h_v3 else h_v2
    # SwiftCODA 用 V3 token + V3 AppId
    
    print(f"  URL: {rank_url[:120]}...")
    result, status = http_request("GET", rank_url, h_rank)
    
    if status == 200 and not result.get("errorCode"):
        print(f"  {PASS} HTTP {status} - 段位数据获取成功!")
        print_json(result)
        results.append({"test": "Ranked v2 (new SpaceId)", "status": "PASS"})
    else:
        print(f"  {FAIL} HTTP {status}")
        if result.get("errorCode"):
            print(f"     ErrorCode: {result.get('errorCode')}, Msg: {result.get('message', '')[:200]}")
        else:
            print_json(result, 500)
        results.append({"test": "Ranked v2 (new SpaceId)", "status": "FAIL"})
    
    # 也用 V2 试试
    if h_v3:
        print(f"\n  [备用: V2 token + V2 AppId]")
        result2, status2 = http_request("GET", rank_url, h_v2)
        if status2 == 200 and not result2.get("errorCode"):
            print(f"  {PASS} V2 也能用! HTTP {status2}")
        else:
            print(f"  {WARN} V2 不行 HTTP {status2}: {result2.get('message', '')[:100]}")

    time.sleep(1)

    # ==================== 6. 等级数据 ====================
    separator("6. 等级数据 (Level/XP)")
    
    level_url = (
        f"https://public-ubiservices.ubi.com/v1/spaces/{NEW_SPACE_ID}/title/r6s"
        f"/rewards/public_profile?profile_id={uid}"
    )
    
    # SwiftCODA: 用 V3 token + V2 AppId
    h_level = dict(h_v2) if h_v3 else h_v2
    if h_v3:
        h_level["Authorization"] = f"ubi_v1 t={token_v3['ticket']}"
        h_level["Ubi-SessionId"] = token_v3.get("sessionId", "")
    
    print(f"  URL: {level_url[:120]}...")
    result, status = http_request("GET", level_url, h_level)
    
    if status == 200 and not result.get("errorCode"):
        print(f"  {PASS} HTTP {status} - 等级数据获取成功!")
        print_json(result)
        results.append({"test": "Player Level", "status": "PASS"})
    else:
        print(f"  {FAIL} HTTP {status}")
        print_json(result, 500)
        results.append({"test": "Player Level", "status": "FAIL"})

    time.sleep(1)

    # ==================== 7. 比赛历史（尝试新旧端点） ====================
    separator("7. 比赛历史 (Match History)")
    
    match_urls = [
        ("playedgames (old)", f"https://public-ubiservices.ubi.com/v1/profiles/{pid}/playedgames?spaceId={NEW_SPACE_ID}&limit=5&offset=0"),
        ("matches v2 (new space)", f"https://public-ubiservices.ubi.com/v2/spaces/{NEW_SPACE_ID}/matches?profile_id={pid}&limit=5"),
        ("datadev matches", f"https://prod.datadev.ubisoft.com/v1/users/{uid}/playerstats?spaceId={PSN_SPACE_ID}&gameMode=ranked&view=current&aggregation=movingpoint&platform=PC&teamRole=all"),
    ]
    
    for label, url in match_urls:
        print(f"\n  [{label}]")
        print(f"  URL: {url[:120]}...")
        result, status = http_request("GET", url, h_v2)
        
        if status == 200 and not result.get("errorCode"):
            print(f"  {PASS} HTTP {status} - 有数据!")
            print_json(result, 800)
            results.append({"test": f"Match History ({label})", "status": "PASS"})
        else:
            print(f"  {FAIL} HTTP {status}")
            if result.get("message"):
                print(f"     Msg: {result['message'][:150]}")
            results.append({"test": f"Match History ({label})", "status": "FAIL"})
        time.sleep(0.8)

    # ==================== 最终报告 ====================
    separator("📋 端点可用性报告")
    print()
    
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    
    for r in results:
        icon = PASS if r["status"] == "PASS" else (FAIL if r["status"] == "FAIL" else WARN)
        print(f"  {icon} {r['test']}")
    
    print(f"\n  总计: {len(results)} 个测试")
    print(f"  {PASS} 通过: {len(passed)}")
    print(f"  {FAIL} 失败: {len(failed)}")
    print("=" * 60)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), "output", "api_v2_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📁 报告已保存到: {report_path}")


if __name__ == "__main__":
    main()

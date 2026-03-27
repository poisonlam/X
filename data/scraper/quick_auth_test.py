"""快速认证测试 - 只发一次请求，不重试"""
import os, sys, io, json, base64, urllib.request, urllib.error, ssl

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

email = os.environ.get("UBI_EMAIL", "")
password = os.environ.get("UBI_PASSWORD", "")

if not email or not password:
    print("请设置 UBI_EMAIL 和 UBI_PASSWORD 环境变量")
    sys.exit(1)

# 尝试多个 AppId
APP_IDS = {
    "R6S PC (r6api.js)": "e3d5ea9e-50bd-43b7-88bf-39794f4e3d40",
    "Ubisoft Connect": "3587dcbb-7f81-457c-9781-0e3f29f6f56a",
    "R6S Tracker": "39baebad-39e5-4552-8c25-2c9b91e604f2",
    "Ubisoft Club": "314d4fef-e568-454a-ae06-43e3bece12a6",
}

credentials = base64.b64encode(f"{email}:{password}".encode()).decode()

for name, app_id in APP_IDS.items():
    print(f"\n--- 测试 AppId: {name} ({app_id[:12]}...) ---")
    headers = {
        "Content-Type": "application/json",
        "Ubi-AppId": app_id,
        "Authorization": f"Basic {credentials}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    body = json.dumps({"rememberMe": True}).encode("utf-8")
    req = urllib.request.Request(
        "https://public-ubiservices.ubi.com/v3/profiles/sessions",
        data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  ✅ 成功! HTTP {resp.status}")
            print(f"  Ticket: {data.get('ticket', 'N/A')[:40]}...")
            print(f"  ProfileId: {data.get('profileId', 'N/A')}")
            print(f"  SessionId: {data.get('sessionId', 'N/A')}")
            print(f"  Expiration: {data.get('expiration', 'N/A')}")
            # 成功就不测其他的了
            break
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except:
            pass
        print(f"  ❌ HTTP {e.code}")
        try:
            err = json.loads(body_text)
            print(f"  Message: {err.get('message', 'N/A')}")
            print(f"  ErrorCode: {err.get('errorCode', 'N/A')}")
        except:
            print(f"  Raw: {body_text[:300]}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

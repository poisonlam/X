"""
R6 Data Fetcher - 通过 r6data.eu API 获取彩虹六号围攻的玩家数据
=================================================================

使用方法:
  1. 在 https://r6data.eu/register.html 注册账号
  2. 登录后在 https://r6data.eu/dashboard 获取 API Key
  3. 运行: python fetch_r6data.py --api-key YOUR_KEY --player PLAYER_NAME

或设置环境变量:
  R6DATA_API_KEY=YOUR_KEY
  python fetch_r6data.py --player PLAYER_NAME
"""

import argparse
import json
import os
import sys
import time
import io
from pathlib import Path
from typing import Optional, Dict, Any, List

# Fix Windows GBK encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Run: pip install requests")
    sys.exit(1)

# ============================================================
#  Configuration
# ============================================================

BASE_URL = "https://api.r6data.eu/api"
OUTPUT_DIR = Path(__file__).parent.parent / "scraper" / "output"

# ============================================================
#  R6Data API Client
# ============================================================

class R6DataClient:
    """r6data.eu API client"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": "r6-data-fetcher/1.0"
        })
        self._request_count = 0

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send GET request to r6data.eu API"""
        url = f"{BASE_URL}{endpoint}"
        self._request_count += 1

        try:
            resp = self.session.get(url, params=params, timeout=30)

            if resp.status_code == 401:
                print(f"  [!] 认证失败 (401): API Key 无效或已过期")
                return {"error": "Unauthorized", "status": 401}

            if resp.status_code == 429:
                print(f"  [!] 请求频率限制 (429): 请稍后再试")
                return {"error": "Rate limited", "status": 429}

            if resp.status_code != 200:
                print(f"  [!] HTTP {resp.status_code}: {resp.text[:200]}")
                return {"error": f"HTTP {resp.status_code}", "status": resp.status_code}

            return resp.json()

        except requests.exceptions.ConnectionError as e:
            print(f"  [!] 连接失败: {e}")
            return {"error": "Connection failed"}
        except requests.exceptions.Timeout:
            print(f"  [!] 请求超时")
            return {"error": "Timeout"}
        except Exception as e:
            print(f"  [!] 未知错误: {e}")
            return {"error": str(e)}

    # ---- Game Data (static) ----

    def get_operators(self, **filters) -> Dict:
        """获取干员元数据"""
        return self._get("/operators", params=filters or None)

    def get_maps(self, **filters) -> Dict:
        """获取地图元数据"""
        return self._get("/maps", params=filters or None)

    def get_weapons(self, **filters) -> Dict:
        """获取武器元数据"""
        return self._get("/weapons", params=filters or None)

    def get_seasons(self, **filters) -> Dict:
        """获取赛季元数据"""
        return self._get("/seasons", params=filters or None)

    def get_ranks(self, version: str = "v6", **filters) -> Dict:
        """获取段位元数据"""
        params = {"version": version, **filters}
        return self._get("/ranks", params=params)

    # ---- Player Data (dynamic) ----

    def get_account_info(self, name: str, platform: str = "uplay") -> Dict:
        """获取玩家账户信息"""
        return self._get("/stats", params={
            "type": "accountInfo",
            "nameOnPlatform": name,
            "platformType": platform
        })

    def get_player_stats(self, name: str, platform: str = "uplay",
                         platform_families: str = "pc", board_id: Optional[str] = None) -> Dict:
        """获取玩家排位/统计数据"""
        params = {
            "type": "stats",
            "nameOnPlatform": name,
            "platformType": platform,
            "platform_families": platform_families
        }
        if board_id:
            params["board_id"] = board_id
        return self._get("/stats", params=params)

    def get_operator_stats(self, name: str, platform: str = "uplay",
                           season: Optional[str] = None, modes: str = "ranked") -> Dict:
        """获取玩家干员使用统计"""
        params = {
            "type": "operatorStats",
            "nameOnPlatform": name,
            "platformType": platform,
            "modes": modes
        }
        if season:
            params["seasonYear"] = season
        return self._get("/stats", params=params)

    def get_seasonal_stats(self, name: str, platform: str = "uplay") -> Dict:
        """获取玩家当前赛季统计"""
        return self._get("/stats", params={
            "type": "seasonalStats",
            "nameOnPlatform": name,
            "platformType": platform
        })

    def get_ban_status(self, name: str, platform: str = "uplay") -> Dict:
        """检查玩家封禁状态"""
        return self._get("/stats", params={
            "type": "isBanned",
            "nameOnPlatform": name,
            "platformType": platform
        })

    def get_game_stats(self) -> Dict:
        """获取游戏实时玩家统计"""
        return self._get("/stats", params={"type": "gameStats"})

    def get_service_status(self) -> Dict:
        """获取服务器状态"""
        return self._get("/servicestatus")

    def get_api_usage(self) -> Dict:
        """获取自己的 API 使用情况"""
        return self._get("/me/usage")


# ============================================================
#  Data Fetcher
# ============================================================

def fetch_all_player_data(client: R6DataClient, player_name: str, platform: str = "uplay") -> Dict:
    """获取一个玩家的所有数据"""
    print(f"\n{'='*60}")
    print(f"  获取玩家数据: {player_name} ({platform})")
    print(f"{'='*60}")

    results = {}

    # 1. 账户信息
    print(f"\n[1/5] 获取账户信息...")
    data = client.get_account_info(player_name, platform)
    results["account_info"] = data
    if "error" not in data:
        print(f"  OK - 获取成功")
    else:
        print(f"  FAIL - {data.get('error')}")

    time.sleep(0.5)  # 避免过快请求

    # 2. 排位统计
    print(f"\n[2/5] 获取排位统计...")
    data = client.get_player_stats(player_name, platform)
    results["player_stats"] = data
    if "error" not in data:
        print(f"  OK - 获取成功")
    else:
        print(f"  FAIL - {data.get('error')}")

    time.sleep(0.5)

    # 3. 干员统计
    print(f"\n[3/5] 获取干员使用统计...")
    data = client.get_operator_stats(player_name, platform, modes="ranked")
    results["operator_stats_ranked"] = data
    if "error" not in data:
        print(f"  OK - 获取成功 (ranked)")
    else:
        print(f"  FAIL - {data.get('error')}")

    time.sleep(0.5)

    # 3b. 干员统计 (casual)
    print(f"  获取干员统计 (casual)...")
    data = client.get_operator_stats(player_name, platform, modes="casual")
    results["operator_stats_casual"] = data
    if "error" not in data:
        print(f"  OK - 获取成功 (casual)")
    else:
        print(f"  FAIL - {data.get('error')}")

    time.sleep(0.5)

    # 4. 当前赛季统计
    print(f"\n[4/5] 获取当前赛季统计...")
    data = client.get_seasonal_stats(player_name, platform)
    results["seasonal_stats"] = data
    if "error" not in data:
        print(f"  OK - 获取成功")
    else:
        print(f"  FAIL - {data.get('error')}")

    time.sleep(0.5)

    # 5. 封禁状态
    print(f"\n[5/5] 检查封禁状态...")
    data = client.get_ban_status(player_name, platform)
    results["ban_status"] = data
    if "error" not in data:
        print(f"  OK - 获取成功")
    else:
        print(f"  FAIL - {data.get('error')}")

    return results


def fetch_game_metadata(client: R6DataClient) -> Dict:
    """获取游戏的元数据 (干员/地图/武器/赛季/段位)"""
    print(f"\n{'='*60}")
    print(f"  获取游戏元数据")
    print(f"{'='*60}")

    results = {}
    items = [
        ("operators", lambda: client.get_operators()),
        ("maps", lambda: client.get_maps()),
        ("weapons", lambda: client.get_weapons()),
        ("seasons", lambda: client.get_seasons()),
        ("ranks_v6", lambda: client.get_ranks("v6")),
    ]

    for i, (name, fetcher) in enumerate(items, 1):
        print(f"\n[{i}/{len(items)}] 获取 {name}...")
        data = fetcher()
        results[name] = data
        if "error" not in data:
            if isinstance(data, list):
                print(f"  OK - {len(data)} 条记录")
            else:
                print(f"  OK - 获取成功")
        else:
            print(f"  FAIL - {data.get('error')}")
        time.sleep(0.3)

    return results


def save_results(data: Dict, filename: str):
    """保存结果到 JSON 文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  [SAVED] {filepath}")


# ============================================================
#  Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="R6 Data Fetcher - 通过 r6data.eu API 获取数据")
    parser.add_argument("--api-key", type=str, help="r6data.eu API Key")
    parser.add_argument("--player", type=str, help="玩家名称 (可指定多个，逗号分隔)")
    parser.add_argument("--platform", type=str, default="uplay", help="平台 (uplay/psn/xbl)")
    parser.add_argument("--metadata", action="store_true", help="同时获取游戏元数据")
    parser.add_argument("--test", action="store_true", help="仅测试 API 连通性")

    args = parser.parse_args()

    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("R6DATA_API_KEY")
    if not api_key:
        print("=" * 60)
        print("  R6 Data Fetcher")
        print("=" * 60)
        print()
        print("  [!] 缺少 API Key!")
        print()
        print("  获取方法:")
        print("  1. 访问 https://r6data.eu/register.html 注册账号")
        print("  2. 登录后在 Dashboard 页面生成 API Key")
        print("  3. 运行: python fetch_r6data.py --api-key YOUR_KEY --player 玩家名")
        print()
        print("  或设置环境变量:")
        print("  $env:R6DATA_API_KEY = 'YOUR_KEY'")
        print("  python fetch_r6data.py --player 玩家名")
        print()
        return

    client = R6DataClient(api_key)

    # Test mode
    if args.test:
        print("=" * 60)
        print("  API 连通性测试")
        print("=" * 60)

        print("\n[1] 测试 API Key...")
        usage = client.get_api_usage()
        if "error" not in usage:
            print(f"  OK - API Key 有效!")
            print(f"  Plan: {usage.get('plan', 'N/A')}")
            print(f"  Limit: {usage.get('limit', 'N/A')}")
            if "usage" in usage:
                print(f"  Total calls: {usage['usage'].get('total_calls', 'N/A')}")
        else:
            print(f"  FAIL - {usage.get('error')}")

        print("\n[2] 测试获取干员数据...")
        ops = client.get_operators(name="ash")
        if "error" not in ops:
            if isinstance(ops, list) and len(ops) > 0:
                print(f"  OK - 找到: {ops[0].get('name', 'N/A')}")
            else:
                print(f"  OK - 响应: {str(ops)[:200]}")
        else:
            print(f"  FAIL - {ops.get('error')}")

        print("\n[3] 测试服务状态...")
        status = client.get_service_status()
        if "error" not in status:
            if isinstance(status, list):
                for s in status:
                    print(f"  {s.get('name', 'N/A')}: {s.get('status', 'N/A')}")
            else:
                print(f"  OK - {str(status)[:200]}")
        else:
            print(f"  FAIL - {status.get('error')}")

        print(f"\n  总请求数: {client._request_count}")
        return

    # Fetch metadata
    if args.metadata:
        metadata = fetch_game_metadata(client)
        save_results(metadata, "r6_metadata.json")

    # Fetch player data
    if args.player:
        players = [p.strip() for p in args.player.split(",")]
        for player_name in players:
            player_data = fetch_all_player_data(client, player_name, args.platform)
            safe_name = player_name.replace(".", "_").replace(" ", "_")
            save_results(player_data, f"player_{safe_name}.json")

    if not args.player and not args.metadata:
        print("请指定 --player 或 --metadata 参数")
        parser.print_help()

    print(f"\n{'='*60}")
    print(f"  完成! 总 API 请求数: {client._request_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

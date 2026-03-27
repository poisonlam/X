"""
使用 siegeapi 库测试彩虹六号围攻的各种数据端点
"""
import asyncio
import os
import sys
import json
import traceback
import io

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 先用 aiohttp 手动检查 DNS
async def check_dns():
    import aiohttp
    print("=" * 60)
    print("  DNS 连通性检查")
    print("=" * 60)
    
    hosts = [
        "https://public-ubiservices.ubi.com",
        "https://prod.datadev.ubisoft.com",
    ]
    
    async with aiohttp.ClientSession() as session:
        for host in hosts:
            try:
                async with session.get(host, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    print(f"  ✅ {host} -> HTTP {resp.status}")
            except aiohttp.ClientConnectorError as e:
                print(f"  ❌ {host} -> 连接失败: {e}")
            except asyncio.TimeoutError:
                print(f"  ⏳ {host} -> 超时 (10s)")
            except Exception as e:
                print(f"  ❓ {host} -> {type(e).__name__}: {e}")
    print()

async def test_siegeapi():
    from siegeapi import Auth
    
    email = os.environ.get("UBI_EMAIL")
    password = os.environ.get("UBI_PASSWORD")
    
    if not email or not password:
        print("❌ 请设置 UBI_EMAIL 和 UBI_PASSWORD 环境变量")
        return
    
    print("=" * 60)
    print("  siegeapi 库测试")
    print("=" * 60)
    
    auth = Auth(email=email, password=password)
    
    try:
        # 1. 搜索玩家
        print("\n[1/7] 搜索玩家 'CNDRD'...")
        try:
            player = await auth.get_player(name="CNDRD")
            print(f"  ✅ 找到: {player.name} (ID: {player.id})")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            # 用一个知名玩家试试
            print("  尝试搜索 'Beaulo.TSM'...")
            try:
                player = await auth.get_player(name="Beaulo.TSM")
                print(f"  ✅ 找到: {player.name} (ID: {player.id})")
            except Exception as e2:
                print(f"  ❌ 也失败了: {e2}")
                print("  无法搜索到任何玩家，跳过后续测试")
                await auth.close()
                return
        
        # 2. 加载等级/进度
        print("\n[2/7] 加载等级/进度 (load_progress)...")
        try:
            await player.load_progress()
            print(f"  ✅ 等级: {player.level}, Alpha Pack: {player.alpha_pack}%, XP: {player.xp}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        
        # 3. 加载游玩时间
        print("\n[3/7] 加载游玩时间 (load_playtime)...")
        try:
            await player.load_playtime()
            print(f"  ✅ 总时长: {player.total_time_played:,} 秒 ({player.total_time_played // 3600} 小时)")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        
        # 4. 加载段位数据
        print("\n[4/7] 加载段位 (load_full_profiles)...")
        try:
            await player.load_full_profiles()
            profiles = player.list_full_profiles()
            print(f"  ✅ 可用档案: {profiles}")
            for p_name in profiles[:3]:
                profile = player.get_full_profile(p_name)
                print(f"    - {p_name}: 段位={profile.rank}, MMR={profile.rank_points}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        
        # 5. 加载干员数据 (需要 prod.datadev.ubisoft.com)
        print("\n[5/7] 加载干员统计 (load_operators) [需要 prod.datadev.ubisoft.com]...")
        try:
            await player.load_operators()
            ops = player.operators
            if ops:
                print(f"  ✅ 干员数据加载成功!")
                # 显示前几个干员
                for mode in ["all"]:
                    attackers = getattr(getattr(ops, mode, None), "attacker", [])
                    if attackers:
                        print(f"  进攻方干员 ({mode}):")
                        for op in attackers[:3]:
                            print(f"    - {op.name}: K={op.kills} D={op.deaths} W={op.wins} L={op.losses}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            traceback.print_exc()
        
        # 6. 加载地图数据 (需要 prod.datadev.ubisoft.com)
        print("\n[6/7] 加载地图统计 (load_maps) [需要 prod.datadev.ubisoft.com]...")
        try:
            await player.load_maps()
            maps = player.maps
            if maps:
                print(f"  ✅ 地图数据加载成功!")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        
        # 7. 加载武器数据 (需要 prod.datadev.ubisoft.com)
        print("\n[7/7] 加载武器统计 (load_weapons) [需要 prod.datadev.ubisoft.com]...")
        try:
            await player.load_weapons()
            weapons = player.weapons
            if weapons:
                print(f"  ✅ 武器数据加载成功!")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        
    except Exception as e:
        print(f"\n❌ 全局错误: {e}")
        traceback.print_exc()
    finally:
        await auth.close()
    
    print("\n" + "=" * 60)
    print("  测试完成!")
    print("=" * 60)

async def main():
    await check_dns()
    await test_siegeapi()

if __name__ == "__main__":
    asyncio.run(main())

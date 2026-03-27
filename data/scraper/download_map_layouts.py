"""
R6 Siege 地图平面图下载器
========================
从多个开源资源下载所有地图的楼层平面图。

资源优先级:
1. irestone/r6s-maps (GitHub) - 高质量蓝图，每楼层单独文件 (1-floor.jpg, basement.jpg 等)
2. capajon/r6maps (GitHub) - r6maps.com 源码，每楼层编号文件 (bank-0.jpg, bank-1.jpg 等)
3. otariga/R6TAC_ALLMAPS (GitHub) - 日本战术地图，扁平命名 (bank1f.jpg, bankb1.jpg 等)

输出目录: data/map_layouts/{map_id}/
"""

import os
import sys
import time
import json
import requests
from urllib.parse import urljoin

# Windows GBK 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # 回到项目根目录
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR))  # data/
OUTPUT_DIR = os.path.join(DATA_DIR, "map_layouts")

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ========================
# 地图信息与楼层定义
# ========================

# 我们项目中的所有地图 (来自 maps.js)
ALL_MAPS = {
    "bank":             {"name": "Bank / 银行",           "floors": ["basement", "1f", "2f"], "roof": True},
    "bartlett_u":       {"name": "Bartlett U. / 巴特利特大学", "floors": ["1f", "2f"], "roof": True},
    "border":           {"name": "Border / 边境",          "floors": ["1f", "2f"], "roof": True},
    "chalet":           {"name": "Chalet / 别墅",          "floors": ["basement", "1f", "2f"], "roof": True},
    "club_house":       {"name": "Club House / 俱乐部",    "floors": ["basement", "1f", "2f"], "roof": True},
    "consulate":        {"name": "Consulate / 领事馆",     "floors": ["basement", "1f", "2f"], "roof": True},
    "hereford_base":    {"name": "Hereford Base / 赫里福德基地", "floors": ["basement", "1f", "2f", "3f"], "roof": True},
    "house":            {"name": "House / 木屋",           "floors": ["basement", "1f", "2f"], "roof": True},
    "kafe_dostoyevsky": {"name": "Kafe Dostoyevsky / 咖啡馆", "floors": ["1f", "2f", "3f"], "roof": True},
    "kanal":            {"name": "Kanal / 运河",           "floors": ["basement", "1f", "2f"], "roof": True},
    "oregon":           {"name": "Oregon / 俄勒冈",        "floors": ["basement", "1f", "2f", "3f"], "roof": True},
    "plane":            {"name": "Plane / 总统专机",        "floors": ["1f", "2f", "3f"], "roof": False},
    "yacht":            {"name": "Yacht / 游艇",           "floors": ["1f", "2f", "3f", "4f"], "roof": False},
    "favela":           {"name": "Favela / 贫民窟",        "floors": ["1f", "2f", "3f"], "roof": True},
    "skyscraper":       {"name": "Skyscraper / 摩天大楼",   "floors": ["1f", "2f"], "roof": True},
    "coastline":        {"name": "Coastline / 海岸线",      "floors": ["1f", "2f"], "roof": True},
    "theme_park":       {"name": "Theme Park / 游乐园",    "floors": ["1f", "2f"], "roof": True},
    "tower":            {"name": "Tower / 塔楼",           "floors": ["1f", "2f"], "roof": True},
    "villa":            {"name": "Villa / 庄园",           "floors": ["basement", "1f", "2f"], "roof": True},
    "fortress":         {"name": "Fortress / 要塞",        "floors": ["1f", "2f"], "roof": True},
    "outback":          {"name": "Outback / 内陆",         "floors": ["1f", "2f"], "roof": True},
    "nighthaven_labs":  {"name": "Nighthaven Labs / 夜港实验室", "floors": ["1f", "2f"], "roof": True},
    "emerald_plains":   {"name": "Emerald Plains / 翡翠平原", "floors": ["1f", "2f"], "roof": True},
    "lair":             {"name": "Lair / 巢穴",            "floors": ["1f", "2f"], "roof": True},
    "stadium":          {"name": "Stadium / 竞技场",        "floors": ["1f", "2f"], "roof": False},
    "close_quarter":    {"name": "Close Quarter / 近距离",  "floors": ["1f", "2f"], "roof": False},
}

# ========================
# 资源 1: irestone/r6s-maps
# ========================
# 文件结构: public/assets/maps/{map_name}/{floor}.jpg
# 楼层命名: basement.jpg, 1-floor.jpg, 2-floor.jpg, 3-floor.jpg, roof.jpg, preview.jpg

IRESTONE_BASE = "https://raw.githubusercontent.com/irestone/r6s-maps/view/public/assets/maps"

# irestone 项目中的地图名称映射 (地图ID -> irestone目录名)
IRESTONE_MAP_NAMES = {
    "bank": "bank",
    "bartlett_u": "bartlett",
    "border": "border",
    "chalet": "chalet",
    "club_house": "club-house",
    "consulate": "consulate",
    "hereford_base": "hereford",
    "house": "house",
    "kafe_dostoyevsky": "kafe",
    "kanal": "kanal",
    "oregon": "oregon",
    "plane": "plane",
    "yacht": "yacht",
    "favela": "favela",
    "skyscraper": "skyscraper",
    "coastline": "coastline",
    "theme_park": "theme-park",
    "tower": "tower",
    "villa": "villa",
    "fortress": "fortress",
    "outback": "outback",
}

# irestone 楼层命名
IRESTONE_FLOOR_FILES = {
    "basement": "basement.jpg",
    "1f": "1-floor.jpg",
    "2f": "2-floor.jpg",
    "3f": "3-floor.jpg",
    "4f": "4-floor.jpg",
    "roof": "roof.jpg",
    "preview": "preview.jpg",
}


# ========================
# 资源 2: capajon/r6maps
# ========================
# 文件结构: site/img/{map_name}/{map_name}-{index}.jpg
# 楼层编号: 0=地下室(如有), 1=1楼, 2=2楼, 3=3楼 (具体取决于地图)

CAPAJON_BASE = "https://raw.githubusercontent.com/capajon/r6maps/master/site/img"

CAPAJON_MAP_NAMES = {
    "bank": "bank",
    "bartlett_u": "bartlett",
    "border": "border",
    "chalet": "chalet",
    "club_house": "club-house",
    "consulate": "consulate",
    "hereford_base": "hereford",
    "house": "house",
    "kafe_dostoyevsky": "kafe",
    "kanal": "kanal",
    "oregon": "oregon",
    "plane": "plane",
    "yacht": "yacht",
    "favela": "favela",
    "skyscraper": "skyscraper",
    "coastline": "coastline",
    "theme_park": "themepark",
    "tower": "tower",
}


# ========================
# 资源 3: otariga/R6TAC_ALLMAPS
# ========================
# 文件结构: {map_shortname}{floor}.jpg 直接在根目录
# 示例: bank1f.jpg, bankb1.jpg, cafe2f.jpg

OTARIGA_BASE = "https://raw.githubusercontent.com/otariga/R6TAC_ALLMAPS/master"

OTARIGA_MAP_NAMES = {
    "bank": "bank",
    "bartlett_u": "bartlett",
    "border": "border",
    "chalet": "chalet",
    "club_house": "club",
    "consulate": "consulate",
    "coastline": "coastline",
    "hereford_base": "hereford",  # 可能不存在
    "house": "house",
    "kafe_dostoyevsky": "cafe",
    "kanal": "kanal",
    "oregon": "oregon",
    "plane": "plane",  # 可能不存在
    "yacht": "yacht",
    "favela": "favela",
    "skyscraper": "skyscraper",
    "theme_park": "themepark",
    "tower": "tower",
    "villa": "villa",
    "fortress": "fortress",
    "outback": "outback",
    "emerald_plains": "ep",
}

# otariga 楼层命名
OTARIGA_FLOOR_SUFFIX = {
    "basement": "b1",
    "1f": "1f",
    "2f": "2f",
    "3f": "3f",
    "4f": "4f",
}


def download_file(url, save_path, session=None):
    """下载单个文件"""
    try:
        s = session or requests
        r = s.get(url, timeout=30, headers=HEADERS)
        if r.status_code == 200:
            # 验证是图片
            content_type = r.headers.get("Content-Type", "")
            if "image" in content_type or len(r.content) > 1000:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(r.content)
                size_kb = len(r.content) / 1024
                return True, f"OK ({size_kb:.1f} KB)"
            else:
                return False, f"Not an image (Content-Type: {content_type}, size: {len(r.content)})"
        else:
            return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


def download_from_irestone(map_id, map_info, session):
    """从 irestone/r6s-maps 下载地图平面图"""
    dir_name = IRESTONE_MAP_NAMES.get(map_id)
    if not dir_name:
        return 0, []
    
    downloaded = 0
    files = []
    
    # 下载每一层
    for floor in map_info["floors"]:
        floor_file = IRESTONE_FLOOR_FILES.get(floor)
        if not floor_file:
            continue
        url = f"{IRESTONE_BASE}/{dir_name}/{floor_file}"
        save_path = os.path.join(OUTPUT_DIR, map_id, f"{floor}.jpg")
        
        if os.path.exists(save_path):
            files.append(f"{floor}.jpg")
            downloaded += 1
            continue
        
        ok, msg = download_file(url, save_path, session)
        if ok:
            files.append(f"{floor}.jpg")
            downloaded += 1
            print(f"  [irestone] {map_id}/{floor}: {msg}")
        time.sleep(0.3)
    
    # 下载屋顶
    if map_info.get("roof"):
        url = f"{IRESTONE_BASE}/{dir_name}/roof.jpg"
        save_path = os.path.join(OUTPUT_DIR, map_id, "roof.jpg")
        if not os.path.exists(save_path):
            ok, msg = download_file(url, save_path, session)
            if ok:
                files.append("roof.jpg")
                downloaded += 1
                print(f"  [irestone] {map_id}/roof: {msg}")
            time.sleep(0.3)
        else:
            files.append("roof.jpg")
            downloaded += 1
    
    # 下载预览图
    url = f"{IRESTONE_BASE}/{dir_name}/preview.jpg"
    save_path = os.path.join(OUTPUT_DIR, map_id, "preview.jpg")
    if not os.path.exists(save_path):
        ok, msg = download_file(url, save_path, session)
        if ok:
            files.append("preview.jpg")
            downloaded += 1
            print(f"  [irestone] {map_id}/preview: {msg}")
        time.sleep(0.3)
    else:
        files.append("preview.jpg")
        downloaded += 1
    
    return downloaded, files


def download_from_capajon(map_id, map_info, session):
    """从 capajon/r6maps 下载地图平面图"""
    dir_name = CAPAJON_MAP_NAMES.get(map_id)
    if not dir_name:
        return 0, []
    
    downloaded = 0
    files = []
    
    # capajon 用编号: map-0.jpg, map-1.jpg, ...
    # 0 通常是地下室(如有), 1=1楼, 2=2楼
    num_floors = len(map_info["floors"])
    for idx in range(num_floors):
        floor_name = map_info["floors"][idx]
        url = f"{CAPAJON_BASE}/{dir_name}/{dir_name}-{idx}.jpg"
        save_path = os.path.join(OUTPUT_DIR, map_id, f"{floor_name}.jpg")
        
        if os.path.exists(save_path):
            files.append(f"{floor_name}.jpg")
            downloaded += 1
            continue
        
        ok, msg = download_file(url, save_path, session)
        if ok:
            files.append(f"{floor_name}.jpg")
            downloaded += 1
            print(f"  [capajon] {map_id}/{floor_name}: {msg}")
        time.sleep(0.3)
    
    return downloaded, files


def download_from_otariga(map_id, map_info, session):
    """从 otariga/R6TAC_ALLMAPS 下载地图平面图"""
    prefix = OTARIGA_MAP_NAMES.get(map_id)
    if not prefix:
        return 0, []
    
    downloaded = 0
    files = []
    
    for floor in map_info["floors"]:
        suffix = OTARIGA_FLOOR_SUFFIX.get(floor)
        if not suffix:
            continue
        url = f"{OTARIGA_BASE}/{prefix}{suffix}.jpg"
        save_path = os.path.join(OUTPUT_DIR, map_id, f"{floor}.jpg")
        
        if os.path.exists(save_path):
            files.append(f"{floor}.jpg")
            downloaded += 1
            continue
        
        ok, msg = download_file(url, save_path, session)
        if ok:
            files.append(f"{floor}.jpg")
            downloaded += 1
            print(f"  [otariga] {map_id}/{floor}: {msg}")
        time.sleep(0.3)
    
    return downloaded, files


def generate_manifest(results):
    """生成地图平面图的索引文件"""
    manifest = {
        "version": "1.0",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "R6 Siege 地图楼层平面图索引",
        "sources": [
            "irestone/r6s-maps (GitHub)",
            "capajon/r6maps (GitHub)",
            "otariga/R6TAC_ALLMAPS (GitHub)"
        ],
        "maps": {}
    }
    
    for map_id, info in results.items():
        manifest["maps"][map_id] = {
            "name": ALL_MAPS[map_id]["name"],
            "floors": info["floors"],
            "files": info["files"],
            "source": info["source"],
            "total_files": len(info["files"])
        }
    
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 索引文件已保存: {manifest_path}")
    return manifest_path


def main():
    print("=" * 60)
    print("🗺️  R6 Siege 地图平面图下载器")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    results = {}
    total_downloaded = 0
    total_skipped = 0
    failed_maps = []
    
    for map_id, map_info in ALL_MAPS.items():
        print(f"\n--- {map_info['name']} ({map_id}) ---")
        
        # 检查是否已经有文件了
        map_dir = os.path.join(OUTPUT_DIR, map_id)
        existing_files = []
        if os.path.exists(map_dir):
            existing_files = [f for f in os.listdir(map_dir) if f.endswith(('.jpg', '.png'))]
        
        if len(existing_files) >= len(map_info["floors"]):
            print(f"  ✅ 已有 {len(existing_files)} 个文件，跳过")
            results[map_id] = {
                "floors": map_info["floors"],
                "files": existing_files,
                "source": "cached",
            }
            total_skipped += 1
            continue
        
        # 策略：按优先级尝试不同资源
        downloaded = 0
        files = []
        source = ""
        
        # 1. 先尝试 irestone (最高质量)
        d, f = download_from_irestone(map_id, map_info, session)
        if d > 0:
            downloaded += d
            files.extend(f)
            source = "irestone/r6s-maps"
        
        # 2. 对于缺失楼层，尝试 capajon
        missing_floors = [fl for fl in map_info["floors"] 
                         if f"{fl}.jpg" not in files]
        if missing_floors:
            d, f = download_from_capajon(map_id, map_info, session)
            if d > 0:
                # 只添加还没有的
                for fname in f:
                    if fname not in files:
                        files.append(fname)
                        downloaded += 1
                source = source + " + capajon/r6maps" if source else "capajon/r6maps"
        
        # 3. 对于仍然缺失的，尝试 otariga
        missing_floors = [fl for fl in map_info["floors"] 
                         if f"{fl}.jpg" not in files]
        if missing_floors:
            d, f = download_from_otariga(map_id, map_info, session)
            if d > 0:
                for fname in f:
                    if fname not in files:
                        files.append(fname)
                        downloaded += 1
                source = source + " + otariga" if source else "otariga"
        
        if downloaded > 0:
            print(f"  ✅ 下载了 {downloaded} 个文件 (来源: {source})")
            total_downloaded += downloaded
            results[map_id] = {
                "floors": map_info["floors"],
                "files": files,
                "source": source,
            }
        else:
            print(f"  ❌ 未能下载任何文件")
            failed_maps.append(map_id)
            results[map_id] = {
                "floors": map_info["floors"],
                "files": [],
                "source": "none",
            }
    
    # 生成索引
    manifest_path = generate_manifest(results)
    
    # 汇总
    print("\n" + "=" * 60)
    print("📊 下载结果汇总")
    print("=" * 60)
    
    success_maps = [m for m, r in results.items() if len(r["files"]) > 0]
    print(f"  成功: {len(success_maps)}/{len(ALL_MAPS)} 张地图")
    print(f"  新下载: {total_downloaded} 个文件")
    print(f"  已缓存: {total_skipped} 张地图")
    
    if failed_maps:
        print(f"\n  ❌ 失败的地图:")
        for m in failed_maps:
            print(f"    - {ALL_MAPS[m]['name']} ({m})")
    
    print(f"\n  输出目录: {OUTPUT_DIR}")
    print(f"  索引文件: {manifest_path}")
    
    # 列出每张地图的文件数
    print(f"\n  详细清单:")
    for map_id in sorted(results.keys()):
        r = results[map_id]
        status = "✅" if len(r["files"]) > 0 else "❌"
        print(f"    {status} {ALL_MAPS[map_id]['name']:30s} | {len(r['files']):2d} 文件 | {r['source']}")


if __name__ == "__main__":
    main()

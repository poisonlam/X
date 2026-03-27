"""
诊断脚本: 分析"没有match"玩家的原因，并测试替代数据源
=======================================================
目标:
  1. 从V2日志中统计各种跳过原因的比例
  2. 从anomaly文件分析异常类型分布
  3. 随机抽样5个"无match"玩家，直接访问stats.cc查看真实响应
  4. 用同样的玩家测试替代数据源(R6Tracker, Ubisoft API等)
"""
import requests, json, os, re, time, random, sys, io
from collections import Counter, defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'extra_match_data')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',  # 不要br! requests不支持brotli解压
}

def parse_nuxt(html):
    blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    return json.loads(blocks[0]) if blocks else None

def deref(data, idx, depth=0, max_depth=25, cache=None):
    if cache is None: cache = {}
    if idx in cache: return cache[idx]
    if depth > max_depth or idx >= len(data): return None
    item = data[idx]
    if isinstance(item, (str, float, bool)) or item is None: return item
    if isinstance(item, int): return item
    if isinstance(item, list):
        if len(item) == 2 and isinstance(item[0], str) and item[0] in ('ShallowReactive','Reactive','ShallowRef','Ref','Set'):
            r = deref(data, item[1], depth+1, max_depth, cache); cache[idx] = r; return r
        r = [deref(data, i, depth+1, max_depth, cache) if isinstance(i, int) else i for i in item]
        cache[idx] = r; return r
    if isinstance(item, dict):
        r = {k: deref(data, v, depth+1, max_depth, cache) if isinstance(v, int) else v for k, v in item.items()}
        cache[idx] = r; return r
    return item

# ===========================================================
# Part 1: 分析V2日志中的跳过原因分布
# ===========================================================
def analyze_v2_logs():
    print("=" * 70)
    print("Part 1: V2日志分析 — 玩家跳过原因分布")
    print("=" * 70)
    
    total_players = 0
    has_new_match = 0  # 有新match要采集
    no_new_match = 0   # 有数据但没有新的ranked match
    fetch_fail = 0     # fetch_player返回None
    empty_result = 0   # fetch_player返回空列表
    type_error = 0     # 类型异常
    
    for sid in range(8):
        logf = os.path.join(OUTPUT_DIR, f'v2_shard_{sid}_log.txt')
        if not os.path.exists(logf): continue
        try:
            lines = open(logf, 'r', encoding='utf-8').readlines()
        except:
            continue
        
        for i, line in enumerate(lines):
            if '[ExV2-S' in line:
                total_players += 1
                # 看接下来的几行判断结果
                context = ''.join(lines[i:min(i+5, len(lines))])
                if 'Rank:' in context and 'new' in context:
                    has_new_match += 1
                elif '[SAVE]' in context or (i+1 < len(lines) and '[ExV2-S' in lines[i+1]):
                    # 快速跳过（没有后续输出就到下个玩家了）
                    no_new_match += 1
    
    print(f"  总处理玩家: {total_players}")
    print(f"  有新match需要采集: {has_new_match}")
    print(f"  没有新match(快速跳过): {no_new_match}")
    print(f"  差值(fetch失败/异常等): {total_players - has_new_match - no_new_match}")
    print()

# ===========================================================
# Part 2: Anomaly异常池分析
# ===========================================================
def analyze_anomalies():
    print("=" * 70)
    print("Part 2: Anomaly异常池分析")
    print("=" * 70)
    
    anomaly_file = os.path.join(OUTPUT_DIR, '_anomaly_players.json')
    if not os.path.exists(anomaly_file):
        print("  未找到anomaly文件")
        return []
    
    anomalies = json.load(open(anomaly_file, 'r', encoding='utf-8'))
    print(f"  总异常玩家数: {len(anomalies)}")
    
    reason_counter = Counter()
    for a in anomalies:
        reason_counter[a.get('reason', 'unknown')] += 1
    
    print(f"\n  异常原因分布:")
    for reason, count in reason_counter.most_common():
        print(f"    {reason}: {count} ({count/len(anomalies)*100:.1f}%)")
    
    print()
    return anomalies

# ===========================================================
# Part 3: 直接请求stats.cc，诊断几个样本玩家
# ===========================================================
def diagnose_sample_players(anomalies):
    print("=" * 70)
    print("Part 3: 样本玩家直接诊断 (stats.cc)")
    print("=" * 70)
    
    # 收集不同类型的样本
    samples = []
    
    # 1) 从anomaly池随机选3个
    if anomalies:
        sample_anomaly = random.sample(anomalies, min(3, len(anomalies)))
        for a in sample_anomaly:
            samples.append({
                'name': a['player_name'], 
                'pid': a['profile_id'], 
                'source': f'anomaly({a["reason"][:20]})'
            })
    
    # 2) 加载extra_players，找一些appearances很高但可能没match的
    try:
        extra = json.load(open(os.path.join(OUTPUT_DIR, '_extra_players.json'), 'r', encoding='utf-8'))
        # 从appearances前100（最活跃）中随机挑2个
        top = extra[:100]
        picks = random.sample(top, min(2, len(top)))
        for p in picks:
            samples.append({
                'name': p['displayName'],
                'pid': p['profileId'],
                'source': f'top_player(appearances={p["appearances"]})'
            })
    except Exception as e:
        print(f"  加载extra_players失败: {e}")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    results = []
    for i, s in enumerate(samples):
        name, pid = s['name'], s['pid']
        print(f"\n  [{i+1}/{len(samples)}] {name} ({pid[:12]}...) — 来源: {s['source']}")
        
        url = f'https://stats.cc/siege/{name}/{pid}'
        print(f"    URL: {url}")
        
        try:
            r = session.get(url, timeout=20)
            print(f"    HTTP状态码: {r.status_code}")
            print(f"    响应大小: {len(r.text)} bytes")
            
            if r.status_code == 404:
                print(f"    → 玩家页面404：stats.cc没有收录此玩家")
                results.append({'player': name, 'statscc_status': '404_not_found', 'has_data': False})
            elif r.status_code == 200 or r.status_code == 500:
                nuxt = parse_nuxt(r.text)
                if not nuxt:
                    print(f"    → 页面存在但无Nuxt数据（可能是空白页或错误页）")
                    # 检查页面标题
                    title = re.search(r'<title>(.*?)</title>', r.text)
                    if title:
                        print(f"    → 页面标题: {title.group(1)[:100]}")
                    results.append({'player': name, 'statscc_status': f'{r.status_code}_no_nuxt', 'has_data': False})
                else:
                    # 解析实际数据
                    player_info = {}
                    for j in range(len(nuxt)):
                        it = nuxt[j]
                        if isinstance(it, dict) and 'rank' in it and 'rankPoints' in it:
                            res = deref(nuxt, j, max_depth=15)
                            if res and isinstance(res.get('rankPoints'), (int, float)):
                                player_info = res
                                break
                    
                    all_matches = []
                    for j in range(len(nuxt)):
                        it = nuxt[j]
                        if isinstance(it, dict) and 'map' in it and 'playlist' in it and 'scores' in it:
                            m = deref(nuxt, j, max_depth=20)
                            if m and isinstance(m.get('id'), str):
                                all_matches.append(m)
                    
                    ranked = [m for m in all_matches if m.get('playlist') == 'ranked']
                    casual = [m for m in all_matches if m.get('playlist') != 'ranked']
                    
                    rank_str = player_info.get('rank', 'N/A')
                    rp = player_info.get('rankPoints', 0)
                    
                    print(f"    → Nuxt数据解析成功!")
                    print(f"    → 段位: {rank_str}, RP: {rp}")
                    print(f"    → 总对局: {len(all_matches)} (ranked: {len(ranked)}, 非ranked: {len(casual)})")
                    
                    if all_matches:
                        playlists = Counter(m.get('playlist', 'unknown') for m in all_matches)
                        print(f"    → 对局类型分布: {dict(playlists)}")
                        maps = Counter(m.get('map', 'unknown') for m in all_matches[:10])
                        print(f"    → 前10场地图: {dict(maps)}")
                    
                    if not ranked and all_matches:
                        print(f"    ★ 关键发现: 此玩家有 {len(all_matches)} 场对局，但全部是非ranked!")
                        print(f"      → 只打休闲/非竞技模式的玩家，我们的采集只关注ranked所以跳过了")
                    elif not all_matches:
                        print(f"    ★ 关键发现: stats.cc有此玩家主页但没有任何对局记录")
                        print(f"      → 可能是新号/刚开始玩/数据未同步")
                    
                    results.append({
                        'player': name, 
                        'statscc_status': f'{r.status_code}_ok',
                        'has_data': True,
                        'rank': rank_str, 'rp': rp,
                        'total_matches': len(all_matches),
                        'ranked_matches': len(ranked),
                        'casual_matches': len(casual)
                    })
            elif r.status_code == 429:
                print(f"    → 被限流了!")
                results.append({'player': name, 'statscc_status': '429_rate_limited', 'has_data': False})
            else:
                print(f"    → 其他HTTP状态码: {r.status_code}")
                results.append({'player': name, 'statscc_status': f'{r.status_code}', 'has_data': False})
        
        except Exception as e:
            print(f"    → 请求异常: {e}")
            results.append({'player': name, 'statscc_status': f'error: {e}', 'has_data': False})
        
        time.sleep(1.5)
    
    return results, samples

# ===========================================================
# Part 4: 测试替代数据源
# ===========================================================
def test_alternative_sources(samples):
    print("\n" + "=" * 70)
    print("Part 4: 替代数据源测试")
    print("=" * 70)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # 只取前3个样本测试
    test_samples = samples[:3]
    
    alt_sources = [
        {
            'name': 'R6Tracker (Tracker Network)',
            'url_template': 'https://r6.tracker.network/r6siege/profile/uplay/{name}/overview',
            'type': 'html',
        },
        {
            'name': 'R6Tracker API',
            'url_template': 'https://api.tracker.gg/api/v2/r6siege/standard/profile/uplay/{name}',
            'type': 'json',
        },
        {
            'name': 'r6data.eu operatorStats',
            'url_template': 'https://r6data.eu/api/stats?type=operatorStats&nameOnPlatform={name}&platformType=uplay',
            'type': 'json',
        },
        {
            'name': 'r6data.eu matchHistory',
            'url_template': 'https://r6data.eu/api/stats?type=matchHistory&nameOnPlatform={name}&platformType=uplay',
            'type': 'json',
        },
        {
            'name': 'Ubisoft Public Stats',
            'url_template': 'https://www.ubisoft.com/en-us/game/rainbow-six/siege/stats/players/{name}/overview',
            'type': 'html',
        },
    ]
    
    for s in test_samples:
        name = s['name']
        print(f"\n  --- 玩家: {name} ---")
        
        for src in alt_sources:
            url = src['url_template'].format(name=name)
            print(f"\n    [{src['name']}]")
            print(f"    URL: {url}")
            
            try:
                r = session.get(url, timeout=15, allow_redirects=True)
                print(f"    HTTP {r.status_code}, 大小: {len(r.text)} bytes")
                
                if r.status_code == 200:
                    if src['type'] == 'json':
                        try:
                            data = r.json()
                            # 简化输出关键字段
                            if isinstance(data, dict):
                                keys = list(data.keys())[:10]
                                print(f"    → JSON keys: {keys}")
                                if 'data' in data:
                                    print(f"    → data type: {type(data['data']).__name__}")
                                    if isinstance(data['data'], dict):
                                        print(f"    → data keys: {list(data['data'].keys())[:10]}")
                                if 'errors' in data:
                                    print(f"    → errors: {data['errors']}")
                            elif isinstance(data, list):
                                print(f"    → JSON array, {len(data)} items")
                                if data:
                                    print(f"    → first item keys: {list(data[0].keys())[:10] if isinstance(data[0], dict) else 'not_dict'}")
                            print(f"    ★ 此数据源可用!")
                        except:
                            print(f"    → 200但非JSON响应")
                    else:
                        # HTML - 检查标题和关键信息
                        title = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
                        if title:
                            print(f"    → 页面标题: {title.group(1)[:80]}")
                        
                        # 检查是否有"not found"类信息
                        if 'not found' in r.text.lower() or '404' in r.text[:500]:
                            print(f"    → 页面内容表示未找到")
                        elif len(r.text) > 5000:
                            print(f"    ★ 页面内容丰富，此数据源可能可用!")
                        else:
                            print(f"    → 页面较短，可能没有实质数据")
                elif r.status_code == 403:
                    print(f"    → 被封禁/需要认证")
                elif r.status_code == 404:
                    print(f"    → 玩家不存在")
                elif r.status_code == 429:
                    print(f"    → 限流")
                else:
                    print(f"    → 状态码: {r.status_code}")
            except requests.exceptions.Timeout:
                print(f"    → 超时")
            except Exception as e:
                print(f"    → 异常: {str(e)[:100]}")
            
            time.sleep(1)

# ===========================================================
# Part 5: 分析真正"没有match"的规模
# ===========================================================
def analyze_no_match_scale():
    print("\n" + "=" * 70)
    print("Part 5: '没有新match' 的真实规模分析")
    print("=" * 70)
    
    # 加载全局已完成
    global_done_file = os.path.join(OUTPUT_DIR, '_global_completed_players.json')
    v2_done = set()
    for i in range(8):
        pf = os.path.join(OUTPUT_DIR, f'_v2_shard_{i}_progress.json')
        if os.path.exists(pf):
            try:
                d = json.load(open(pf, 'r', encoding='utf-8'))
                v2_done.update(d.get('completed_players', []))
            except: pass
    
    # V2的match数
    v2_matches = set()
    for i in range(8):
        pf = os.path.join(OUTPUT_DIR, f'_v2_shard_{i}_progress.json')
        if os.path.exists(pf):
            try:
                d = json.load(open(pf, 'r', encoding='utf-8'))
                v2_matches.update(d.get('completed_matches', []))
            except: pass
    
    # 旧分片的match数
    old_matches = set()
    for i in range(16):
        pf = os.path.join(OUTPUT_DIR, f'_shard_{i}_progress.json')
        if os.path.exists(pf):
            try:
                d = json.load(open(pf, 'r', encoding='utf-8'))
                old_matches.update(d.get('completed_matches', []))
            except: pass
    
    # 主排行榜match
    main_dir = os.path.join(BASE_DIR, 'output', 'match_data')
    main_matches = set()
    for i in range(20):
        pf = os.path.join(main_dir, f'_shard_{i}_progress.json')
        if os.path.exists(pf):
            try:
                d = json.load(open(pf, 'r', encoding='utf-8'))
                main_matches.update(d.get('completed_matches', []))
            except: pass
    gp = os.path.join(main_dir, '_progress.json')
    if os.path.exists(gp):
        try:
            d = json.load(open(gp, 'r', encoding='utf-8'))
            main_matches.update(d.get('completed_matches', []))
        except: pass
    
    all_matches = main_matches | old_matches | v2_matches
    
    # JSONL中实际有多少新match
    v2_jsonl_matches = 0
    for i in range(8):
        jf = os.path.join(OUTPUT_DIR, f'v2_shard_{i}', 'match_details.jsonl')
        if os.path.exists(jf):
            try:
                v2_jsonl_matches += sum(1 for l in open(jf, 'r', encoding='utf-8') if l.strip())
            except: pass
    
    # anomaly数
    anomaly_count = 0
    af = os.path.join(OUTPUT_DIR, '_anomaly_players.json')
    if os.path.exists(af):
        try:
            anomaly_count = len(json.load(open(af, 'r', encoding='utf-8')))
        except: pass
    
    total_extra = 112816  # 已知
    
    print(f"  总Extra玩家: {total_extra}")
    print(f"  V2已处理玩家: {len(v2_done)}")
    print(f"  异常池玩家: {anomaly_count}")
    print()
    print(f"  主排行榜match: {len(main_matches)}")
    print(f"  旧Extra分片match: {len(old_matches)}")
    print(f"  V2新增match: {len(v2_matches)}")
    print(f"  V2 JSONL实际条目: {v2_jsonl_matches}")
    print(f"  全局唯一match总数: {len(all_matches)}")
    print()
    
    # 核心分析：V2处理了这么多玩家，但新match数量极少
    if len(v2_done) > 0:
        match_ratio = len(v2_matches) / len(v2_done) * 100
        print(f"  V2 match/player 比率: {match_ratio:.2f}%")
        print(f"  → 意味着每100个V2处理的玩家，只有 {match_ratio:.1f} 个贡献了新match")
    
    print()
    print("  ★ 关键结论:")
    print("  这些'没有match'的玩家主要有以下几种情况:")
    print("  1. 玩家的ranked match已经被其他玩家的采集覆盖了（最常见）")
    print("     → 因为同一场match出现在所有10个参与者的记录中")
    print("  2. 玩家只玩casual/quickmatch，没有ranked记录")
    print("  3. 玩家改名/注销，stats.cc 404")
    print("  4. stats.cc 服务器对该玩家返回500（数据不完整）")
    print("  5. 玩家是新账号/低活跃度，stats.cc没有收录")

# ===========================================================
# Main
# ===========================================================
if __name__ == '__main__':
    print(f"R6 Siege 数据采集 — 缺失玩家诊断报告")
    print(f"生成时间: {datetime.now().isoformat()}")
    print()
    
    analyze_v2_logs()
    anomalies = analyze_anomalies()
    results, samples = diagnose_sample_players(anomalies)
    test_alternative_sources(samples)
    analyze_no_match_scale()
    
    print("\n" + "=" * 70)
    print("诊断完成!")
    print("=" * 70)

"""
Extra玩家采集 v2 — 全局去重优化版
用法:
  python extra_v2.py run --shard-id 0 --total-shards 8
  python extra_v2.py status
  python extra_v2.py merge
"""
import requests, re, sys, io, json, os, time, argparse, random, tempfile
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',  # 不要br! requests不支持brotli解压
}

_session = None
def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        a = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=0)
        _session.mount('https://', a)
        _session.mount('http://', a)
    return _session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'extra_match_data')
MAIN_MATCH_DIR = os.path.join(BASE_DIR, 'output', 'match_data')
EXTRA_PLAYERS_FILE = os.path.join(OUTPUT_DIR, '_extra_players.json')
ANOMALY_FILE = os.path.join(OUTPUT_DIR, '_anomaly_players.json')
GLOBAL_DONE_FILE = os.path.join(OUTPUT_DIR, '_global_completed_players.json')

# ===== 全局去重 =====
def load_global_done():
    done = set()
    if os.path.exists(GLOBAL_DONE_FILE):
        try:
            with open(GLOBAL_DONE_FILE, 'r', encoding='utf-8') as f:
                done.update(json.load(f))
        except: pass
    for i in range(20):
        for pat in [os.path.join(OUTPUT_DIR, f'_shard_{i}_progress.json'),
                    os.path.join(OUTPUT_DIR, f'_v2_shard_{i}_progress.json')]:
            if os.path.exists(pat):
                try:
                    with open(pat, 'r', encoding='utf-8') as f:
                        done.update(json.load(f).get('completed_players', []))
                except: pass
    return done

def atomic_save(filepath, data):
    tmp = filepath + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, filepath)

def load_all_known_matches():
    known = set()
    for i in range(20):
        for d in [MAIN_MATCH_DIR, OUTPUT_DIR]:
            for pat in [f'_shard_{i}_progress.json', f'_v2_shard_{i}_progress.json']:
                pf = os.path.join(d, pat)
                if os.path.exists(pf):
                    try:
                        with open(pf, 'r', encoding='utf-8') as f:
                            known.update(json.load(f).get('completed_matches', []))
                    except: pass
    gp = os.path.join(MAIN_MATCH_DIR, '_progress.json')
    if os.path.exists(gp):
        try:
            with open(gp, 'r', encoding='utf-8') as f:
                known.update(json.load(f).get('completed_matches', []))
        except: pass
    return known

# ===== Nuxt解析 =====
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

def parse_nuxt(html):
    blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    return json.loads(blocks[0]) if blocks else None

def check_health():
    try:
        r = get_session().get('https://stats.cc/siege/matches/3f4a671e-7fe1-4f35-a7e4-d99522109330', timeout=10)
        return r.status_code == 200
    except: return False

# ===== 自适应Delay =====
class AdaptiveDelay:
    def __init__(self, base=1.5, lo=0.8, hi=5.0):
        self.cur = base; self.lo = lo; self.hi = hi
        self.ok_cnt = 0; self.rate_cnt = 0
    def ok(self):
        self.ok_cnt += 1
        if self.ok_cnt >= 20:
            self.cur = max(self.lo, self.cur * 0.9); self.ok_cnt = 0; self.rate_cnt = 0
    def limited(self):
        self.rate_cnt += 1; self.ok_cnt = 0
        self.cur = min(self.hi, self.cur * 1.5)
    def get(self): return self.cur + random.uniform(0.2, 0.8)
    def __str__(self): return f"d={self.cur:.1f}s"

# ===== 数据获取 =====
def fetch_player(name, pid, ad, retries=4):
    s = get_session(); url = f'https://stats.cc/siege/{name}/{pid}'
    for att in range(retries):
        try:
            r = s.get(url, timeout=(10, 25))
            if r.status_code == 429:
                ad.limited(); w = min(5*(2**att), 60)
                print(f"    [429] wait {w}s ({ad})"); time.sleep(w); continue
            if r.status_code == 404: ad.ok(); return None
            if r.status_code in (200, 500):
                ad.ok(); nuxt = parse_nuxt(r.text)
                if not nuxt:
                    if r.status_code == 500: return []
                    return {'matches': [], 'player_info': {}}
                pi = {}
                for i in range(len(nuxt)):
                    it = nuxt[i]
                    if isinstance(it, dict) and 'rank' in it and 'rankPoints' in it and 'wins' in it:
                        res = deref(nuxt, i, max_depth=15)
                        if res and isinstance(res.get('rankPoints'), (int, float)): pi = res; break
                ms = []
                for i in range(len(nuxt)):
                    it = nuxt[i]
                    if isinstance(it, dict) and 'map' in it and 'playlist' in it and 'scores' in it:
                        m = deref(nuxt, i, max_depth=20)
                        if m and isinstance(m.get('id'), str) and len(m.get('id','')) > 10:
                            ms.append({k: m.get(k) for k in ('id','map','playlist','mode','scores','started_at','ended_at','outcome')})
                if ms:
                    # 统一 match_id 字段
                    for m in ms: m['match_id'] = m.pop('id', m.get('match_id'))
                    if r.status_code == 500: print(f"    [*] 500 but got {len(ms)} matches")
                    return {'matches': ms, 'player_info': pi}
                elif r.status_code == 500: return []
                else: return {'matches': [], 'player_info': pi}
            print(f"    [!] HTTP {r.status_code} (att {att+1})")
            if r.status_code >= 500 and att < retries-1: time.sleep(min(10*(2**att),120)); continue
            if att < retries-1: time.sleep(2); continue
            return None
        except requests.exceptions.Timeout:
            print(f"    [!] Timeout (att {att+1})")
            if att < retries-1: time.sleep(2)
        except Exception as e:
            print(f"    [!] Error: {e}")
            if att < retries-1: time.sleep(3)
    return None

def fetch_match(mid, ad, retries=4):
    s = get_session(); url = f'https://stats.cc/siege/matches/{mid}'
    for att in range(retries):
        try:
            r = s.get(url, timeout=(10, 25))
            if r.status_code == 429:
                ad.limited(); w = min(5*(2**att),60)
                print(f"      [429] wait {w}s"); time.sleep(w); continue
            if r.status_code == 404: ad.ok(); return None
            if r.status_code != 200:
                if r.status_code >= 500 and att < retries-1: time.sleep(min(10*(2**att),120)); continue
                if att < retries-1: time.sleep(2); continue
                return None
            ad.ok(); nuxt = parse_nuxt(r.text)
            if not nuxt: return None
            meta = None
            for i in range(len(nuxt)):
                it = nuxt[i]
                if isinstance(it, dict) and 'map' in it and 'scores' in it and 'playlist' in it:
                    meta = deref(nuxt, i, max_depth=15); break
            rounds = []
            for i in range(len(nuxt)):
                it = nuxt[i]
                if isinstance(it, dict) and 'operator' in it and 'outcome' in it and 'profile_id' in it:
                    res = deref(nuxt, i, max_depth=12)
                    if res: rounds.append(res)
            summaries = []
            for i in range(len(nuxt)):
                it = nuxt[i]
                if isinstance(it, dict) and 'username' in it and 'rounds' in it and 'round_wins' in it and 'team' in it:
                    res = deref(nuxt, i, max_depth=12)
                    if res: summaries.append(res)
            if not rounds: return None
            return {
                'match_id': mid,
                'map': meta.get('map') if meta else None,
                'playlist': meta.get('playlist') if meta else None,
                'mode': meta.get('mode') if meta else None,
                'scores': meta.get('scores') if meta else None,
                'started_at': meta.get('started_at') if meta else None,
                'ended_at': meta.get('ended_at') if meta else None,
                'player_summaries': summaries,
                'round_records': rounds,
                'total_rounds': len(rounds) // max(len(summaries),1) if summaries else 0,
                'total_players': len(summaries),
            }
        except requests.exceptions.Timeout:
            if att < retries-1: time.sleep(2)
        except Exception as e:
            print(f"      [!] {e}")
            if att < retries-1: time.sleep(3)
    return None

def save_anomaly(name, pid, reason="数据异常"):
    try:
        lst = json.load(open(ANOMALY_FILE,'r',encoding='utf-8')) if os.path.exists(ANOMALY_FILE) else []
    except: lst = []
    if pid not in {p['profile_id'] for p in lst}:
        lst.append({'player_name':name,'profile_id':pid,'reason':reason,'recorded_at':datetime.now().isoformat()})
        with open(ANOMALY_FILE,'w',encoding='utf-8') as f: json.dump(lst, f, ensure_ascii=False, indent=2)

# ===== Run =====
def cmd_run(args):
    sid = args.shard_id; ts = args.total_shards; mm = args.max_matches
    os.makedirs(os.path.join(OUTPUT_DIR, f'v2_shard_{sid}'), exist_ok=True)
    
    with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
        all_players = json.load(f)
    
    # 全局去重: 加载所有已完成玩家
    global_done = load_global_done()
    print(f"[v2] 全局已完成玩家: {len(global_done)} / {len(all_players)}")
    
    # 过滤未完成的玩家，然后分片
    remaining = [p for p in all_players if p['profileId'] not in global_done]
    print(f"[v2] 剩余玩家: {len(remaining)}")
    
    shard_players = [p for i, p in enumerate(remaining) if i % ts == sid]
    print(f"[v2] 本分片(Shard {sid}/{ts-1}): {len(shard_players)} 玩家")
    
    # 加载v2分片进度
    v2_pf = os.path.join(OUTPUT_DIR, f'_v2_shard_{sid}_progress.json')
    v2_done = set()
    v2_matches = set()
    if os.path.exists(v2_pf):
        try:
            with open(v2_pf, 'r', encoding='utf-8') as f:
                d = json.load(f)
            v2_done = set(d.get('completed_players', []))
            v2_matches = set(d.get('completed_matches', []))
        except: pass
    
    # 再次过滤本分片已完成的
    shard_players = [p for p in shard_players if p['profileId'] not in v2_done]
    print(f"[v2] 本分片待处理: {len(shard_players)} (已跳过 {len(v2_done)})")
    
    all_known = load_all_known_matches()
    all_known.update(v2_matches)
    print(f"[v2] 全局已知matches: {len(all_known)}")
    
    # JSONL追加文件
    jsonl_file = os.path.join(OUTPUT_DIR, f'v2_shard_{sid}', 'match_details.jsonl')
    ad = AdaptiveDelay(base=args.delay)
    
    new_players = 0; new_matches = 0; consec_fail = 0; save_counter = 0
    
    def maybe_save(idx_val):
        nonlocal save_counter
        save_counter += 1
        if save_counter % 20 == 0 or idx_val == len(shard_players) - 1:
            _save_v2(sid, v2_done, v2_matches)
            print(f"  [SAVE] {len(v2_done)} players done, {new_matches} new matches ({ad})")
    
    for idx, player in enumerate(shard_players):
        pname = player['displayName']; pid = player['profileId']
        apps = player.get('appearances', 0)
        print(f"[ExV2-S{sid}][{idx+1}/{len(shard_players)}] {pname} (seen {apps}x) ({ad})")
        
        result = fetch_player(pname, pid, ad)
        
        if result is None:
            consec_fail += 1
            if consec_fail >= 10:
                print(f"  [!] {consec_fail} consecutive fails! Health check...")
                _save_v2(sid, v2_done, v2_matches)
                time.sleep(min(60, consec_fail * 10))
                if check_health():
                    consec_fail = 0; save_anomaly(pname, pid, "连续失败但服务器正常")
                    v2_done.add(pid); maybe_save(idx); time.sleep(ad.get()); continue
                else:
                    print(f"  [!] Server down, skipping"); time.sleep(ad.get()); continue
            v2_done.add(pid); maybe_save(idx); time.sleep(ad.get()); continue
        elif isinstance(result, list) and len(result) == 0:
            save_anomaly(pname, pid); v2_done.add(pid); consec_fail = 0
            maybe_save(idx); time.sleep(0.3); continue
        elif not isinstance(result, dict):
            save_anomaly(pname, pid, f"type={type(result).__name__}")
            v2_done.add(pid); consec_fail = 0; maybe_save(idx); time.sleep(0.3); continue
        else:
            consec_fail = 0
        
        matches = result.get('matches', [])
        pi = result.get('player_info', {})
        ranked = [m for m in matches if m.get('playlist') == 'ranked']
        new = [m for m in ranked if m.get('match_id') and m['match_id'] not in all_known]
        to_fetch = new[:mm]
        
        if not to_fetch:
            v2_done.add(pid); new_players += 1
            maybe_save(idx); time.sleep(0.3); continue
        
        print(f"  Rank: {pi.get('rank','-')} RP: {pi.get('rankPoints',0)} | {len(ranked)} ranked, {len(to_fetch)} new")
        
        for mi, m in enumerate(to_fetch):
            mid = m['match_id']; mmap = m.get('map','?')
            print(f"    [{mi+1}/{len(to_fetch)}] {mid[:12]}... ({mmap})", end=' ', flush=True)
            detail = fetch_match(mid, ad)
            if detail:
                detail['source_player'] = {'displayName':pname,'profileId':pid,
                    'rank':pi.get('rank',''),'rankPoints':pi.get('rankPoints',0),'source':'extra_v2'}
                # 追加到JSONL
                with open(jsonl_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(detail, ensure_ascii=False) + '\n')
                all_known.add(mid); v2_matches.add(mid); new_matches += 1
                print(f"OK ({detail.get('total_players',0)}p)")
            else:
                print("FAIL")
            time.sleep(ad.get())
        
        v2_done.add(pid); new_players += 1
        maybe_save(idx)
        time.sleep(ad.get())
    
    _save_v2(sid, v2_done, v2_matches)
    print(f"\n{'='*60}\nShard {sid} 完成! 玩家:{new_players} 新对局:{new_matches}\n{'='*60}")

def _save_v2(sid, done, matches):
    pf = os.path.join(OUTPUT_DIR, f'_v2_shard_{sid}_progress.json')
    atomic_save(pf, {
        'shard_id': sid, 'version': 'v2',
        'completed_players': list(done), 'completed_matches': list(matches),
        'last_updated': datetime.now().isoformat(),
        'stats': {'total_players_done': len(done), 'total_matches_done': len(matches)}
    })

# ===== Status =====
def cmd_status(args):
    # 加载extra总数
    total = 0
    if os.path.exists(EXTRA_PLAYERS_FILE):
        with open(EXTRA_PLAYERS_FILE, 'r', encoding='utf-8') as f:
            total = len(json.load(f))
    
    global_done = load_global_done()
    all_matches = load_all_known_matches()
    
    print(f"{'='*60}")
    print(f"Extra采集进度 (真实去重)")
    print(f"{'='*60}")
    print(f"  总Extra玩家: {total}")
    print(f"  已完成(去重): {len(global_done)}")
    print(f"  剩余: {total - len(global_done)}")
    print(f"  完成率: {len(global_done)/max(total,1)*100:.1f}%")
    print(f"  全局唯一matches: {len(all_matches)}")
    
    # V2分片状态
    print(f"\n  V2分片状态:")
    for i in range(20):
        pf = os.path.join(OUTPUT_DIR, f'_v2_shard_{i}_progress.json')
        if os.path.exists(pf):
            with open(pf, 'r', encoding='utf-8') as f:
                d = json.load(f)
            print(f"    V2-Shard {i}: {d['stats']['total_players_done']} players, {d['stats']['total_matches_done']} matches, updated: {d.get('last_updated','?')}")

# ===== Merge =====
def cmd_merge(args):
    print("合并所有Extra数据...")
    seen = set(); all_data = []
    # 旧分片
    for i in range(16):
        df = os.path.join(OUTPUT_DIR, f'shard_{i}', 'match_details.json')
        if os.path.exists(df):
            with open(df, 'r', encoding='utf-8') as f:
                data = json.load(f)
            n = 0
            for d in data:
                mid = d.get('match_id')
                if mid and mid not in seen: all_data.append(d); seen.add(mid); n += 1
            print(f"  Old shard {i}: {n} new / {len(data)} total")
    # V2分片
    for i in range(20):
        jf = os.path.join(OUTPUT_DIR, f'v2_shard_{i}', 'match_details.jsonl')
        if os.path.exists(jf):
            n = 0
            with open(jf, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            d = json.loads(line)
                            mid = d.get('match_id')
                            if mid and mid not in seen: all_data.append(d); seen.add(mid); n += 1
                        except: pass
            print(f"  V2 shard {i}: {n} new")
    
    out = os.path.join(OUTPUT_DIR, 'all_extra_match_details.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False)
    print(f"\n合并完成: {len(all_data)} unique matches -> {out}")

def main():
    p = argparse.ArgumentParser(description='Extra玩家采集 v2')
    sub = p.add_subparsers(dest='command')
    
    rp = sub.add_parser('run')
    rp.add_argument('--shard-id', type=int, required=True)
    rp.add_argument('--total-shards', type=int, required=True)
    rp.add_argument('--max-matches', type=int, default=5)
    rp.add_argument('--delay', type=float, default=1.5)
    
    sub.add_parser('status')
    sub.add_parser('merge')
    
    a = p.parse_args()
    if a.command == 'run': cmd_run(a)
    elif a.command == 'status': cmd_status(a)
    elif a.command == 'merge': cmd_merge(a)
    else: p.print_help()

if __name__ == '__main__':
    main()

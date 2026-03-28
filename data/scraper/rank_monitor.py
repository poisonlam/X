"""Web 版段位采集监控面板 — HTTP API + 静态页面"""
import json, os, time, threading
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = BASE_DIR / 'output' / 'rank_data'
PLAYERS_FILE = BASE_DIR / 'output' / '_players_need_rank.json'

TOTAL_PLAYERS = 0
cache = {'data': None, 'time': 0}

RANK_ORDER = [
    'champion',
    'diamond-i','diamond-ii','diamond-iii','diamond-iv','diamond-v',
    'emerald-i','emerald-ii','emerald-iii','emerald-iv','emerald-v',
    'platinum-i','platinum-ii','platinum-iii','platinum-iv','platinum-v',
    'gold-i','gold-ii','gold-iii','gold-iv','gold-v',
    'silver-i','silver-ii','silver-iii','silver-iv','silver-v',
    'bronze-i','bronze-ii','bronze-iii','bronze-iv','bronze-v',
    'copper-i','copper-ii','copper-iii','copper-iv','copper-v',
    'unranked','unknown','error','timeout'
]

def get_stats():
    now = time.time()
    if cache['data'] and now - cache['time'] < 5:
        return cache['data']
    
    all_c = {}
    shard_counts = {}
    gf = OUTPUT_DIR / '_global_completed.json'
    if gf.exists():
        try: all_c.update(json.load(open(gf,'r',encoding='utf-8')))
        except: pass
    for pf in sorted(OUTPUT_DIR.glob('shard_*_progress.json')):
        try:
            sn = pf.stem.replace('_progress','')
            d = json.load(open(pf,'r',encoding='utf-8'))
            c = d.get('completed',{})
            all_c.update(c)
            shard_counts[sn] = len(c)
        except: pass

    done = len(all_c)
    ranks = Counter()
    for v in all_c.values():
        r = v.get('rank','unknown') if isinstance(v,dict) else v
        ranks[r] += 1

    active = 0
    for pf in OUTPUT_DIR.glob('shard_*_progress.json'):
        try:
            if now - pf.stat().st_mtime < 120: active += 1
        except: pass

    rank_dist = []
    for r in RANK_ORDER:
        c = ranks.get(r, 0)
        if c > 0 or r in RANK_ORDER[:36]:
            rank_dist.append({'rank': r, 'count': c})

    shards = []
    ps = TOTAL_PLAYERS // 32 if TOTAL_PLAYERS else 1
    for i in range(32):
        cnt = shard_counts.get(f'shard_{i}', 0)
        shards.append({'id': i, 'done': cnt, 'total': ps})

    result = {
        'total': TOTAL_PLAYERS, 'done': done, 'remaining': TOTAL_PLAYERS - done,
        'pct': round(done / TOTAL_PLAYERS * 100, 2) if TOTAL_PLAYERS else 0,
        'active': active, 'time': datetime.now().strftime('%H:%M:%S'),
        'ranks': rank_dist, 'shards': shards,
    }
    cache['data'] = result
    cache['time'] = now
    return result

HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>R6 段位采集监控</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#f3f4f6;font-family:'Segoe UI',sans-serif;padding:20px}
.header{text-align:center;padding:20px 0;border-bottom:2px solid #f59e0b;margin-bottom:20px}
.header h1{font-size:24px;color:#f59e0b}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px}
.stat{background:#1a2332;border-radius:10px;padding:16px;text-align:center}
.stat .val{font-size:28px;font-weight:800;color:#f59e0b}
.stat .lbl{font-size:12px;color:#9ca3af;margin-top:4px}
.progress-bar{background:#1a2332;border-radius:10px;padding:16px;margin-bottom:20px}
.bar-outer{background:#374151;border-radius:8px;height:32px;overflow:hidden}
.bar-inner{background:linear-gradient(90deg,#f59e0b,#10b981);height:100%;transition:width 0.5s;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.panel{background:#1a2332;border-radius:10px;padding:16px}
.panel h3{color:#f59e0b;margin-bottom:12px;font-size:15px}
.rank-row{display:flex;align-items:center;gap:8px;margin-bottom:3px;font-size:12px}
.rank-name{width:110px;text-align:right;color:#9ca3af}
.rank-bar-outer{flex:1;background:#374151;border-radius:3px;height:16px;overflow:hidden}
.rank-bar-inner{height:100%;border-radius:3px;transition:width 0.5s;min-width:1px}
.rank-count{width:60px;font-size:11px;color:#9ca3af}
.rank-pct{width:45px;font-size:11px;color:#6b7280;text-align:right}
.shard-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.shard{background:#111827;border-radius:6px;padding:8px;font-size:11px}
.shard .id{color:#9ca3af;font-weight:600}
.shard .cnt{color:#f3f4f6;font-weight:700}
.shard-bar{background:#374151;border-radius:2px;height:4px;margin-top:4px;overflow:hidden}
.shard-bar-inner{background:#3b82f6;height:100%;transition:width 0.5s}
.tier-champion{color:#ff4500}.tier-diamond{color:#00bfff}.tier-emerald{color:#10b981}
.tier-platinum{color:#8b5cf6}.tier-gold{color:#f59e0b}.tier-silver{color:#9ca3af}
.tier-bronze{color:#b87333}.tier-copper{color:#d2691e}.tier-other{color:#6b7280}
.footer{text-align:center;color:#6b7280;font-size:12px;margin-top:16px}
</style></head><body>
<div class="header"><h1>🎯 R6 段位采集监控</h1></div>
<div class="stats">
  <div class="stat"><div class="val" id="done">-</div><div class="lbl">已完成</div></div>
  <div class="stat"><div class="val" id="total">-</div><div class="lbl">总计</div></div>
  <div class="stat"><div class="val" id="speed">-</div><div class="lbl">速率/小时</div></div>
  <div class="stat"><div class="val" id="eta">-</div><div class="lbl">预计剩余</div></div>
  <div class="stat"><div class="val" id="active">-</div><div class="lbl">活跃分片</div></div>
</div>
<div class="progress-bar">
  <div class="bar-outer"><div class="bar-inner" id="pbar" style="width:0%">0%</div></div>
</div>
<div class="grid">
  <div class="panel"><h3>📊 段位分布</h3><div id="rankDist"></div></div>
  <div class="panel"><h3>⚙️ 分片状态</h3><div class="shard-grid" id="shards"></div></div>
</div>
<div class="footer" id="footer">每10秒自动刷新</div>
<script>
const tierColor = r => {
  if(r.startsWith('champion')) return '#ff4500';
  if(r.startsWith('diamond')) return '#00bfff';
  if(r.startsWith('emerald')) return '#10b981';
  if(r.startsWith('platinum')) return '#8b5cf6';
  if(r.startsWith('gold')) return '#f59e0b';
  if(r.startsWith('silver')) return '#9ca3af';
  if(r.startsWith('bronze')) return '#b87333';
  if(r.startsWith('copper')) return '#d2691e';
  return '#6b7280';
};
const fmt = n => n.toLocaleString();
let prevDone=0, prevTime=Date.now(), speeds=[];

async function refresh() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    const now = Date.now();
    
    // speed
    const dt = (now - prevTime) / 3600000;
    if(dt > 0 && d.done > prevDone) {
      speeds.push((d.done - prevDone) / dt);
      if(speeds.length > 10) speeds = speeds.slice(-10);
    }
    prevDone = d.done; prevTime = now;
    const avgSpd = speeds.length ? speeds.reduce((a,b)=>a+b)/speeds.length : 0;
    
    // eta
    let etaStr = '计算中...';
    if(avgSpd > 0) {
      const hrs = d.remaining / avgSpd;
      const etaDate = new Date(now + hrs*3600000);
      etaStr = hrs.toFixed(1) + 'h';
      document.getElementById('eta').title = 'ETA: ' + etaDate.toLocaleString();
    }
    
    document.getElementById('done').textContent = fmt(d.done);
    document.getElementById('total').textContent = fmt(d.total);
    document.getElementById('speed').textContent = fmt(Math.round(avgSpd));
    document.getElementById('eta').textContent = etaStr;
    document.getElementById('active').textContent = d.active + '/32';
    document.getElementById('pbar').style.width = d.pct + '%';
    document.getElementById('pbar').textContent = d.pct.toFixed(2) + '%';
    
    // ranks
    const maxCount = Math.max(...d.ranks.map(r=>r.count), 1);
    document.getElementById('rankDist').innerHTML = d.ranks
      .filter(r => r.count > 0 || !['unranked','unknown','error','timeout'].includes(r.rank))
      .map(r => {
        const w = (r.count/maxCount*100).toFixed(1);
        const p = d.done ? (r.count/d.done*100).toFixed(1) : '0.0';
        const c = tierColor(r.rank);
        return '<div class="rank-row">' +
          '<div class="rank-name" style="color:'+c+'">'+r.rank+'</div>' +
          '<div class="rank-bar-outer"><div class="rank-bar-inner" style="width:'+w+'%;background:'+c+'"></div></div>' +
          '<div class="rank-count">'+fmt(r.count)+'</div>' +
          '<div class="rank-pct">'+p+'%</div></div>';
      }).join('');
    
    // shards
    document.getElementById('shards').innerHTML = d.shards.map(s => {
      const p = s.total ? (s.done/s.total*100).toFixed(1) : '0';
      return '<div class="shard"><span class="id">S'+s.id+'</span> <span class="cnt">'+fmt(s.done)+'</span> <span style="color:#6b7280;font-size:10px">'+p+'%</span>' +
        '<div class="shard-bar"><div class="shard-bar-inner" style="width:'+p+'%"></div></div></div>';
    }).join('');
    
    document.getElementById('footer').textContent = '更新于 ' + d.time + ' | 每10秒刷新';
  } catch(e) {
    document.getElementById('footer').textContent = '⚠ 连接失败: ' + e.message;
  }
}
refresh();
setInterval(refresh, 10000);
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stats':
            data = get_stats()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
    def log_message(self, format, *args): pass

def main():
    global TOTAL_PLAYERS
    TOTAL_PLAYERS = len(json.load(open(PLAYERS_FILE,'r',encoding='utf-8')))
    port = 8766
    server = HTTPServer(('127.0.0.1', port), Handler)
    print(f'监控面板已启动: http://localhost:{port}')
    server.serve_forever()

if __name__ == '__main__':
    main()

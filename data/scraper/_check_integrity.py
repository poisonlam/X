import json, os

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'match_data')

print("=== JSON 文件完整性检查 ===")
for s in range(5):
    f = os.path.join(base, f'shard_{s}', 'match_details.json')
    if not os.path.exists(f):
        print(f"Shard {s}: NOT FOUND")
        continue
    
    size = os.path.getsize(f)
    print(f"Shard {s}: {size:,} bytes ({size/1024/1024:.1f} MB)", end=" ")
    
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        print(f"-> VALID ({len(data)} matches)")
    except json.JSONDecodeError as e:
        print(f"-> CORRUPT! Error at position {e.pos}: {e.msg}")
        # 尝试截断修复
        with open(f, 'r', encoding='utf-8') as fh:
            raw = fh.read()
        # 找最后一个完整的 }, 结尾
        last_bracket = raw.rfind('}]')
        if last_bracket > 0:
            truncated = raw[:last_bracket+2]
            try:
                data = json.loads(truncated)
                print(f"   -> Can be recovered: {len(data)} matches (truncating at {last_bracket+2})")
            except:
                # 更激进：找最后一个 }, 然后加 ]
                last_obj = raw.rfind('},')
                if last_obj > 0:
                    truncated2 = raw[:last_obj+1] + ']'
                    try:
                        data = json.loads(truncated2)
                        print(f"   -> Can be recovered (method 2): {len(data)} matches")
                    except Exception as e2:
                        print(f"   -> Cannot recover: {e2}")
                else:
                    print(f"   -> Cannot find recovery point")
        else:
            print(f"   -> Cannot find recovery point")

print()
print("=== 各分片进度文件检查 ===")
for s in range(5):
    pf = os.path.join(base, f'_shard_{s}_progress.json')
    if os.path.exists(pf):
        with open(pf, 'r', encoding='utf-8') as fh:
            p = json.load(fh)
        print(f"Shard {s}: {len(p.get('completed_players',[]))} players, {len(p.get('completed_matches',[]))} matches, last: {p.get('last_updated','?')}")
    else:
        print(f"Shard {s}: No progress file")

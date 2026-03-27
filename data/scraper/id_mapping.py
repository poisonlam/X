"""
R6 Siege 数据名称映射模块
=========================
用途：
1. 将 stats.cc 返回的地图 slug（如 "club-house"）映射到项目内部 ID（如 "club_house"）
2. 将 stats.cc 返回的干员 slug（如 "solid-snake"）映射到标准名称
3. 自动检测 stats.cc 是否更改了数据格式（脱敏检测）
4. 从已有的采集数据中自动构建映射表

映射表保存在 output/_id_mappings.json，采集脚本启动时自动加载。
"""
import sys
import io
import json
import os
import glob
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
MAPPINGS_FILE = os.path.join(OUTPUT_DIR, '_id_mappings.json')

# ===== 手工维护的已知地图映射 =====
# stats.cc slug -> 项目内部 ID
KNOWN_MAP_SLUG_TO_ID = {
    # 当前排位池
    'club-house': 'club_house',
    'chalet': 'chalet',
    'nighthaven-labs': 'nighthaven_labs',
    'oregon': 'oregon',
    'border': 'border',
    'consulate': 'consulate',
    'kafe-dostoyevsky': 'kafe_dostoyevsky',
    'fortress': 'fortress',
    'coastline': 'coastline',
    'villa': 'villa',
    'bank': 'bank',
    'lair': 'lair',
    'emerald-plains': 'emerald_plains',
    # 非排位池 / 历史地图
    'house': 'house',
    'hereford-base': 'hereford_base',
    'presidential-plane': 'presidential_plane',
    'bartlett-university': 'bartlett_u',
    'kanal': 'kanal',
    'favela': 'favela',
    'skyscraper': 'skyscraper',
    'yacht': 'yacht',
    'theme-park': 'theme_park',
    'tower': 'tower',
    'outback': 'outback',
    'stadium': 'stadium',
    'close-quarter': 'close_quarter',
}

# R6 Tracker 显示名 -> 项目内部 ID
KNOWN_MAP_DISPLAY_TO_ID = {
    'Bank': 'bank',
    'Bartlett University': 'bartlett_u',
    'Border': 'border',
    'Chalet': 'chalet',
    'Club House': 'club_house',
    'Coastline': 'coastline',
    'Consulate': 'consulate',
    'Emerald Plains': 'emerald_plains',
    'Favela': 'favela',
    'Fortress': 'fortress',
    'Hereford Base': 'hereford_base',
    'House': 'house',
    'Kafe Dostoyevsky': 'kafe_dostoyevsky',
    'Kanal': 'kanal',
    'Lair': 'lair',
    'Nighthaven Labs': 'nighthaven_labs',
    'Oregon': 'oregon',
    'Outback': 'outback',
    'Presidential Plane': 'presidential_plane',
    'Skyscraper': 'skyscraper',
    'Theme Park': 'theme_park',
    'Tower': 'tower',
    'Villa': 'villa',
    'Yacht': 'yacht',
}

# ===== 已知干员名称映射 =====
# stats.cc slug -> 标准名称（大部分slug和标准名相同，这里只列出有差异的）
KNOWN_OPERATOR_ALIASES = {
    'solid-snake': 'solid-snake',  # 这就是官方名称
    # 如果未来发现有改名的，在这里添加
}

# 攻击方干员集合
ATTACKERS = {
    'sledge', 'thatcher', 'ash', 'thermite', 'twitch', 'montagne', 'blitz', 'iq', 'fuze', 'glaz',
    'buck', 'blackbeard', 'capitao', 'hibana', 'jackal', 'ying', 'zofia', 'dokkaebi', 'lion', 'finka',
    'maverick', 'nomad', 'gridlock', 'nokk', 'amaru', 'kali', 'iana', 'ace', 'zero', 'flores',
    'osa', 'sens', 'grim', 'brava', 'ram', 'striker', 'deimos', 'solid-snake', 'rauora',
}
# 防守方干员集合
DEFENDERS = {
    'smoke', 'mute', 'castle', 'pulse', 'doc', 'rook', 'jager', 'bandit', 'tachanka', 'kapkan',
    'frost', 'valkyrie', 'caveira', 'echo', 'mira', 'lesion', 'ela', 'vigil', 'alibi', 'maestro',
    'clash', 'kaid', 'mozzie', 'warden', 'goyo', 'wamai', 'oryx', 'melusi', 'aruni', 'thunderbird',
    'thorn', 'azami', 'solis', 'fenrir', 'tubarao', 'skopos', 'neon', 'denari', 'sentry',
}

ALL_KNOWN_OPERATORS = ATTACKERS | DEFENDERS


class IDMapper:
    """名称映射管理器"""
    
    def __init__(self, auto_load=True):
        self.map_slug_to_id = dict(KNOWN_MAP_SLUG_TO_ID)
        self.map_display_to_id = dict(KNOWN_MAP_DISPLAY_TO_ID)
        self.operator_aliases = dict(KNOWN_OPERATOR_ALIASES)
        self.unknown_maps = set()         # 遇到但无法映射的地图名
        self.unknown_operators = set()    # 遇到但无法识别的干员名
        self.format_changes = []          # 检测到的格式变化记录
        self._loaded_from_file = False
        
        if auto_load:
            self.load()
    
    def load(self):
        """从文件加载映射表"""
        if os.path.exists(MAPPINGS_FILE):
            try:
                with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 合并（文件中的优先）
                if 'map_slug_to_id' in data:
                    self.map_slug_to_id.update(data['map_slug_to_id'])
                if 'operator_aliases' in data:
                    self.operator_aliases.update(data['operator_aliases'])
                if 'unknown_maps' in data:
                    self.unknown_maps = set(data['unknown_maps'])
                if 'unknown_operators' in data:
                    self.unknown_operators = set(data['unknown_operators'])
                if 'format_changes' in data:
                    self.format_changes = data['format_changes']
                self._loaded_from_file = True
            except Exception as e:
                print(f"[IDMapper] 加载映射文件失败: {e}")
    
    def save(self):
        """保存映射表到文件"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        data = {
            'map_slug_to_id': self.map_slug_to_id,
            'map_display_to_id': self.map_display_to_id,
            'operator_aliases': self.operator_aliases,
            'unknown_maps': sorted(self.unknown_maps),
            'unknown_operators': sorted(self.unknown_operators),
            'format_changes': self.format_changes,
            'last_updated': datetime.now().isoformat(),
            'stats': {
                'total_map_slugs': len(self.map_slug_to_id),
                'total_operator_aliases': len(self.operator_aliases),
                'unknown_maps_count': len(self.unknown_maps),
                'unknown_operators_count': len(self.unknown_operators),
            }
        }
        tmp_file = MAPPINGS_FILE + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, MAPPINGS_FILE)
    
    def normalize_map(self, raw_map_name):
        """
        将原始地图名（来自 stats.cc）转换为项目内部 ID
        
        Args:
            raw_map_name: stats.cc 返回的地图名（slug 格式如 "club-house"）
        
        Returns:
            项目内部 ID（如 "club_house"）
        """
        if not raw_map_name:
            return 'unknown'
        
        name = raw_map_name.strip().lower()
        
        # 1. 直接查 slug 映射表
        if name in self.map_slug_to_id:
            return self.map_slug_to_id[name]
        
        # 2. 尝试自动转换（slug → underscore）
        auto_id = name.replace('-', '_')
        # 检查是否是已知的地图 ID
        known_ids = set(self.map_slug_to_id.values()) | set(self.map_display_to_id.values())
        if auto_id in known_ids:
            self.map_slug_to_id[name] = auto_id
            return auto_id
        
        # 3. 检查是否是 R6 Tracker 显示名格式
        if raw_map_name in self.map_display_to_id:
            return self.map_display_to_id[raw_map_name]
        
        # 4. 可能是新的格式（数据脱敏？）
        self._detect_format_change('map', raw_map_name)
        self.unknown_maps.add(raw_map_name)
        
        # 返回自动推断的 ID（用下划线替换连字符）
        return auto_id
    
    def normalize_operator(self, raw_operator_name):
        """
        将原始干员名转换为标准名称
        
        Args:
            raw_operator_name: stats.cc 返回的干员名（slug 格式如 "solid-snake"）
        
        Returns:
            标准干员名
        """
        if not raw_operator_name:
            return 'unknown'
        
        name = raw_operator_name.strip().lower()
        
        # 1. 查别名映射
        if name in self.operator_aliases:
            return self.operator_aliases[name]
        
        # 2. 检查是否是已知干员
        if name in ALL_KNOWN_OPERATORS:
            return name
        
        # 3. 未知干员
        self.unknown_operators.add(name)
        self._detect_format_change('operator', raw_operator_name)
        
        return name
    
    def get_operator_side(self, operator_name):
        """获取干员阵营"""
        name = operator_name.strip().lower()
        # 先检查别名
        if name in self.operator_aliases:
            name = self.operator_aliases[name]
        if name in ATTACKERS:
            return 'attack'
        elif name in DEFENDERS:
            return 'defense'
        return 'unknown'
    
    def _detect_format_change(self, field_type, raw_value):
        """检测可能的数据格式变化"""
        # 检查是否看起来像 ID / hash（可能是数据脱敏）
        is_suspicious = False
        reason = ''
        
        if re.match(r'^[0-9a-f]{8,}$', raw_value):
            is_suspicious = True
            reason = f"看起来像 hash/ID: {raw_value}"
        elif re.match(r'^[0-9]+$', raw_value) and len(raw_value) > 3:
            is_suspicious = True
            reason = f"纯数字 ID: {raw_value}"
        elif re.match(r'^[A-Z0-9_]+$', raw_value) and '_' in raw_value:
            is_suspicious = True
            reason = f"看起来像编码后的 ID: {raw_value}"
        
        if is_suspicious:
            change_record = {
                'type': field_type,
                'raw_value': raw_value,
                'reason': reason,
                'detected_at': datetime.now().isoformat(),
            }
            # 避免重复记录
            existing_values = {c['raw_value'] for c in self.format_changes}
            if raw_value not in existing_values:
                self.format_changes.append(change_record)
                print(f"[IDMapper] ⚠️ 疑似数据格式变化 ({field_type}): {reason}")
    
    def check_data_integrity(self, match_data):
        """
        检查一条比赛数据的完整性，发现异常返回警告列表
        
        Args:
            match_data: 一条比赛数据 dict
        
        Returns:
            list of warning strings
        """
        warnings = []
        
        # 检查地图名
        map_name = match_data.get('map', '')
        if map_name:
            normalized = self.normalize_map(map_name)
            if map_name in self.unknown_maps:
                warnings.append(f"未知地图: {map_name} → {normalized}")
        
        # 检查干员名
        for rd in match_data.get('round_records', []):
            op = rd.get('operator', '')
            if op:
                self.normalize_operator(op)
        
        # 检查关键字段
        if not match_data.get('match_id'):
            warnings.append("缺少 match_id")
        if not match_data.get('round_records'):
            warnings.append("缺少 round_records")
        if not match_data.get('player_summaries'):
            warnings.append("缺少 player_summaries")
        
        return warnings
    
    def get_format_change_report(self):
        """获取格式变化报告"""
        if not self.format_changes:
            return "未检测到数据格式变化"
        
        report = f"检测到 {len(self.format_changes)} 个可疑的格式变化:\n"
        for c in self.format_changes:
            report += f"  [{c['type']}] {c['reason']} (发现于 {c['detected_at']})\n"
        return report


def scan_existing_data():
    """扫描所有已有的采集数据，构建完整的映射表"""
    mapper = IDMapper(auto_load=True)
    
    all_maps = set()
    all_operators = set()
    
    # 扫描所有比赛数据分片
    patterns = [
        os.path.join(OUTPUT_DIR, 'match_data', 'shard_*', 'match_details.json'),
        os.path.join(OUTPUT_DIR, 'extra_match_data', 'shard_*', 'match_details.json'),
    ]
    
    total_matches = 0
    for pattern in patterns:
        for fpath in sorted(glob.glob(pattern)):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    matches = json.load(f)
                for m in matches:
                    total_matches += 1
                    map_name = m.get('map', '')
                    if map_name:
                        all_maps.add(map_name)
                        mapper.normalize_map(map_name)
                    for rd in m.get('round_records', []):
                        op = rd.get('operator', '')
                        if op:
                            all_operators.add(op)
                            mapper.normalize_operator(op)
                print(f"  Scanned {os.path.relpath(fpath, BASE_DIR)}: {len(matches)} matches")
            except Exception as e:
                print(f"  [WARN] {fpath}: {e}")
    
    mapper.save()
    
    print(f"\n扫描完成:")
    print(f"  总比赛数: {total_matches}")
    print(f"  地图名称: {len(all_maps)}")
    for m in sorted(all_maps):
        mid = mapper.normalize_map(m)
        status = '[OK]' if m not in mapper.unknown_maps else '[??]'
        print(f"    {status} {m} -> {mid}")
    print(f"  干员名称: {len(all_operators)}")
    for o in sorted(all_operators):
        side = mapper.get_operator_side(o)
        status = '[OK]' if o not in mapper.unknown_operators else '[??]'
        print(f"    {status} {o} ({side})")
    
    if mapper.unknown_maps:
        print(f"\n  [WARN] 未知地图 ({len(mapper.unknown_maps)}):")
        for m in sorted(mapper.unknown_maps):
            print(f"    {m}")
    
    if mapper.unknown_operators:
        print(f"\n  [WARN] 未知干员 ({len(mapper.unknown_operators)}):")
        for o in sorted(mapper.unknown_operators):
            print(f"    {o}")
    
    print(f"\n  格式变化报告:")
    print(f"  {mapper.get_format_change_report()}")
    
    print(f"\n  映射表已保存到: {MAPPINGS_FILE}")
    return mapper


# 全局单例（采集脚本直接 import 使用）
_global_mapper = None

def get_mapper():
    """获取全局映射器单例"""
    global _global_mapper
    if _global_mapper is None:
        _global_mapper = IDMapper(auto_load=True)
    return _global_mapper


if __name__ == '__main__':
    # 确保 stdout 使用 UTF-8 编码（仅主程序时设置）
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 70)
    print("R6 Siege 数据名称映射 - 扫描与构建")
    print("=" * 70)
    scan_existing_data()

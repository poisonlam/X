/**
 * Rainbow Six Siege - 地图楼层平面图数据
 * 
 * 从多个开源社区资源收集的地图楼层布局图
 * 图片文件存放在 data/map_layouts/{map_id}/ 目录下
 * 
 * 资源来源:
 * - irestone/r6s-maps (GitHub) - 高质量蓝图
 * - capajon/r6maps (GitHub) - r6maps.com 源码
 * - otariga/R6TAC_ALLMAPS (GitHub) - 日本战术地图
 * - ivanyeungtc/r6calls (GitHub) - R6Calls 社区地图
 */

const MAP_LAYOUTS = {
  bank: {
    name: "Bank / 银行",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [
      { id: "roof", name: "屋顶 (Roof)", file: "roof.jpg" },
      { id: "preview", name: "预览图 (Preview)", file: "preview.jpg" }
    ],
    source: "irestone/r6s-maps",
    totalFiles: 5
  },
  bartlett_u: {
    name: "Bartlett U. / 巴特利特大学",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 2
  },
  border: {
    name: "Border / 边境",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 2
  },
  chalet: {
    name: "Chalet / 别墅",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [
      { id: "roof", name: "屋顶 (Roof)", file: "roof.jpg" },
      { id: "preview", name: "预览图 (Preview)", file: "preview.jpg" }
    ],
    source: "irestone/r6s-maps",
    totalFiles: 5
  },
  club_house: {
    name: "Club House / 俱乐部",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    totalFiles: 3
  },
  coastline: {
    name: "Coastline / 海岸线",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 2
  },
  consulate: {
    name: "Consulate / 领事馆",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [
      { id: "roof", name: "屋顶 (Roof)", file: "roof.jpg" },
      { id: "preview", name: "预览图 (Preview)", file: "preview.jpg" }
    ],
    source: "irestone/r6s-maps",
    totalFiles: 5
  },
  emerald_plains: {
    name: "Emerald Plains / 翡翠平原",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "otariga",
    totalFiles: 2
  },
  favela: {
    name: "Favela / 贫民窟",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" },
      { id: "3f", name: "三楼 (3rd Floor)", file: "3f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 3
  },
  fortress: {
    name: "Fortress / 要塞",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "otariga",
    totalFiles: 2
  },
  hereford_base: {
    name: "Hereford Base / 赫里福德基地",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" },
      { id: "3f", name: "三楼 (3rd Floor)", file: "3f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    totalFiles: 4
  },
  house: {
    name: "House / 木屋",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    totalFiles: 3
  },
  kafe_dostoyevsky: {
    name: "Kafe Dostoyevsky / 咖啡馆",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" },
      { id: "3f", name: "三楼 (3rd Floor)", file: "3f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 3
  },
  kanal: {
    name: "Kanal / 运河",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 3
  },
  oregon: {
    name: "Oregon / 俄勒冈",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" },
      { id: "3f", name: "三楼 (3rd Floor)", file: "3f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    totalFiles: 4
  },
  outback: {
    name: "Outback / 内陆",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [
      { id: "3f", name: "屋顶/外部 (Roof/Exterior)", file: "3f.jpg" }
    ],
    source: "ivanyeungtc/r6calls",
    totalFiles: 3
  },
  plane: {
    name: "Plane / 总统专机",
    floors: [
      { id: "2f", name: "中层 (Mid Level)", file: "2f.jpg" },
      { id: "3f", name: "上层 (Upper Level)", file: "3f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    note: "部分楼层缺失(1F/下层)",
    totalFiles: 2
  },
  skyscraper: {
    name: "Skyscraper / 摩天大楼",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 2
  },
  theme_park: {
    name: "Theme Park / 游乐园",
    floors: [
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps + otariga",
    totalFiles: 2
  },
  tower: {
    name: "Tower / 塔楼",
    floors: [
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    note: "部分楼层缺失(1F)",
    totalFiles: 1
  },
  villa: {
    name: "Villa / 庄园",
    floors: [
      { id: "basement", name: "地下室 (Basement)", file: "basement.jpg" },
      { id: "1f", name: "一楼 (1st Floor)", file: "1f.jpg" },
      { id: "2f", name: "二楼 (2nd Floor)", file: "2f.jpg" }
    ],
    extras: [],
    source: "otariga",
    totalFiles: 3
  },
  yacht: {
    name: "Yacht / 游艇",
    floors: [
      { id: "2f", name: "二层 (2nd Deck)", file: "2f.jpg" },
      { id: "3f", name: "三层 (3rd Deck)", file: "3f.jpg" },
      { id: "4f", name: "四层 (4th Deck)", file: "4f.jpg" }
    ],
    extras: [],
    source: "capajon/r6maps",
    note: "部分楼层缺失(1F/底层)",
    totalFiles: 3
  }
};

// 缺失平面图的地图 (较新地图，社区资源尚未覆盖)
const MAPS_WITHOUT_LAYOUTS = [
  { id: "nighthaven_labs", name: "Nighthaven Labs / 夜港实验室", reason: "较新地图(Y7S4)，开源社区暂无平面图资源" },
  { id: "lair", name: "Lair / 巢穴", reason: "较新地图(Y8S3)，开源社区暂无平面图资源" },
  { id: "stadium", name: "Stadium / 竞技场", reason: "活动/特殊地图，开源社区暂无平面图资源" },
  { id: "close_quarter", name: "Close Quarter / 近距离", reason: "TDM专属小地图，开源社区暂无平面图资源" },
];

// 统计信息
const LAYOUT_STATS = {
  totalMapsWithLayouts: Object.keys(MAP_LAYOUTS).length,  // 22
  totalMapsWithoutLayouts: MAPS_WITHOUT_LAYOUTS.length,    // 4
  totalImageFiles: Object.values(MAP_LAYOUTS).reduce((sum, m) => sum + m.totalFiles, 0),  // 64
  basePath: "data/map_layouts/",
  sources: [
    { name: "irestone/r6s-maps", url: "https://github.com/irestone/r6s-maps", quality: "高", maps: 3 },
    { name: "capajon/r6maps", url: "https://github.com/capajon/r6maps", quality: "中", maps: 12 },
    { name: "otariga/R6TAC_ALLMAPS", url: "https://github.com/otariga/R6TAC_ALLMAPS", quality: "中", maps: 8 },
    { name: "ivanyeungtc/r6calls", url: "https://github.com/ivanyeungtc/r6calls", quality: "中高", maps: 1 },
  ],
  collectionDate: "2026-03-24"
};

if (typeof module !== 'undefined') module.exports = { MAP_LAYOUTS, MAPS_WITHOUT_LAYOUTS, LAYOUT_STATS };

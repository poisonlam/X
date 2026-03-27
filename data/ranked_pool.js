/**
 * Rainbow Six Siege - 排位图池历史数据
 * 记录从发售至今每个赛季排位地图池的变化
 * 
 * 说明：
 * - 早期(Y1-Y2)排位图池基本等于所有可用PvP地图
 * - Y3S2开始引入正式的Ranked地图池概念，不再包含所有地图
 * - 竞技(Competitive/Pro League)图池是排位图池的子集，本文件主要记录排位(Ranked)图池
 */

const RANKED_POOL_HISTORY = [
  // ==================== Year 1 (2016) ====================
  {
    season: "发售",
    seasonCode: "Launch",
    operation: "Launch",
    date: "2015-12-01",
    year: 0,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Consulate",
      "Hereford Base", "House", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Plane", "Yacht"
    ],
    added: [],
    removed: [],
    notes: "游戏发售，首发地图全部可用于排位。Bartlett University仅限恐怖猎人模式。"
  },
  {
    season: "Y1S1",
    seasonCode: "Y1S1",
    operation: "Black Ice",
    date: "2016-02-02",
    year: 1,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Consulate",
      "Hereford Base", "House", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Plane", "Yacht"
    ],
    added: ["Yacht"],
    removed: [],
    notes: "Yacht（游艇）作为首个DLC地图加入。此时所有多人地图均可排位。"
  },
  {
    season: "Y1S2",
    seasonCode: "Y1S2",
    operation: "Dust Line",
    date: "2016-05-10",
    year: 1,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Consulate",
      "Hereford Base", "House", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Plane", "Yacht"
    ],
    added: [],
    removed: [],
    notes: "本赛季无新地图加入（Border已在首发中），排位图池不变。"
  },
  {
    season: "Y1S3",
    seasonCode: "Y1S3",
    operation: "Skull Rain",
    date: "2016-08-02",
    year: 1,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Consulate",
      "Favela", "Hereford Base", "House", "Kafe Dostoyevsky",
      "Kanal", "Oregon", "Plane", "Yacht"
    ],
    added: ["Favela"],
    removed: [],
    notes: "Favela（贫民窟）加入排位。这张地图后因严重的攻防不平衡引发争议。"
  },
  {
    season: "Y1S4",
    seasonCode: "Y1S4",
    operation: "Red Crow",
    date: "2016-11-17",
    year: 1,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Consulate",
      "Favela", "Hereford Base", "House", "Kafe Dostoyevsky",
      "Kanal", "Oregon", "Plane", "Skyscraper", "Yacht"
    ],
    added: ["Skyscraper"],
    removed: [],
    notes: "Skyscraper（摩天大楼）加入排位。Bartlett University在本赛季中期加入多人模式但仅限休闲。"
  },

  // ==================== Year 2 (2017) ====================
  {
    season: "Y2S1",
    seasonCode: "Y2S1",
    operation: "Velvet Shell",
    date: "2017-02-07",
    year: 2,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Favela", "Hereford Base", "House",
      "Kafe Dostoyevsky", "Kanal", "Oregon", "Plane",
      "Skyscraper", "Yacht"
    ],
    added: ["Coastline"],
    removed: [],
    notes: "Coastline（海岸线）加入——后来成为游戏最受欢迎的竞技地图之一，至今从未需要重做。"
  },
  {
    season: "Y2S2",
    seasonCode: "Y2S2",
    operation: "Health",
    date: "2017-06-07",
    year: 2,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Hereford Base", "House",
      "Kafe Dostoyevsky", "Kanal", "Oregon", "Skyscraper"
    ],
    added: [],
    removed: ["Favela", "Yacht", "Plane"],
    notes: "Operation Health是一个专注于修复游戏问题的赛季（无新内容）。首次从排位池移除地图：Favela、Yacht和Plane因平衡问题被移除。这是排位图池概念真正开始的标志。"
  },
  {
    season: "Y2S3",
    seasonCode: "Y2S3",
    operation: "Blood Orchid",
    date: "2017-09-05",
    year: 2,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Skyscraper", "Theme Park"
    ],
    added: ["Theme Park"],
    removed: ["Hereford Base", "House"],
    notes: "Theme Park（主题乐园）加入。Hereford Base和House因不适合竞技被移出排位池。排位池开始精简。"
  },
  {
    season: "Y2S4",
    seasonCode: "Y2S4",
    operation: "White Noise",
    date: "2017-12-05",
    year: 2,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Skyscraper", "Theme Park", "Tower"
    ],
    added: ["Tower"],
    removed: [],
    notes: "Tower（塔楼）加入排位。但很快因地图过大和缺乏可破坏外墙而被社区广泛批评。"
  },

  // ==================== Year 3 (2018) ====================
  {
    season: "Y3S1",
    seasonCode: "Y3S1",
    operation: "Chimera",
    date: "2018-03-06",
    year: 3,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Skyscraper", "Theme Park"
    ],
    added: [],
    removed: ["Tower"],
    notes: "Tower仅在排位池待了一个赛季就被移除——成为被移出排位最快的地图之一。本赛季无新地图。"
  },
  {
    season: "Y3S2",
    seasonCode: "Y3S2",
    operation: "Para Bellum",
    date: "2018-06-07",
    year: 3,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Skyscraper", "Villa"
    ],
    added: ["Villa"],
    removed: ["Theme Park"],
    notes: "Villa（别墅）加入排位。Theme Park因光照和可见度问题被移出。Club House在本赛季进行了中型重做。Bartlett University在本赛季被永久移除。"
  },
  {
    season: "Y3S3",
    seasonCode: "Y3S3",
    operation: "Grim Sky",
    date: "2018-09-04",
    year: 3,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Hereford Base", "Kafe Dostoyevsky",
      "Kanal", "Oregon", "Skyscraper", "Villa"
    ],
    added: ["Hereford Base"],
    removed: [],
    notes: "Hereford Base经完全重做后重新加入排位池。但新版Hereford被社区评价为最失败的重做案例之一。"
  },
  {
    season: "Y3S4",
    seasonCode: "Y3S4",
    operation: "Wind Bastion",
    date: "2018-12-04",
    year: 3,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Hereford Base", "Kafe Dostoyevsky",
      "Kanal", "Oregon", "Skyscraper", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Fortress（堡垒）作为新地图发布，但因面积过大直接被归类为休闲地图，未进入排位池。排位图池不变。"
  },

  // ==================== Year 4 (2019) ====================
  {
    season: "Y4S1",
    seasonCode: "Y4S1",
    operation: "Burnt Horizon",
    date: "2019-03-06",
    year: 4,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Villa"
    ],
    added: ["Outback"],
    removed: ["Hereford Base"],
    notes: "Outback（内陆）加入排位。Hereford Base因持续争议被移出排位池。Theme Park在本赛季进行了光照修复（第一次重做）。"
  },
  {
    season: "Y4S2",
    seasonCode: "Y4S2",
    operation: "Phantom Sight",
    date: "2019-06-11",
    year: 4,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Kafe Dostoyevsky在本赛季进行了中型重做（三楼重新设计）。无新图加入排位。"
  },
  {
    season: "Y4S3",
    seasonCode: "Y4S3",
    operation: "Ember Rise",
    date: "2019-09-11",
    year: 4,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: ["Theme Park"],
    removed: [],
    notes: "Kanal进行了大型重做。Theme Park在经过光照修复后重新加入排位池。"
  },
  {
    season: "Y4S4",
    seasonCode: "Y4S4",
    operation: "Shifting Tides",
    date: "2019-12-03",
    year: 4,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "排位图池不变。无新地图发布。"
  },

  // ==================== Year 5 (2020) ====================
  {
    season: "Y5S1",
    seasonCode: "Y5S1",
    operation: "Void Edge",
    date: "2020-03-10",
    year: 5,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Oregon进行了中型重做（地下室和大塔楼区域）。排位图池不变。"
  },
  {
    season: "Y5S2",
    seasonCode: "Y5S2",
    operation: "Steel Wave",
    date: "2020-06-16",
    year: 5,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "House进行了小型调整（仅休闲模式）。排位图池不变。"
  },
  {
    season: "Y5S3",
    seasonCode: "Y5S3",
    operation: "Shadow Legacy",
    date: "2020-09-10",
    year: 5,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Chalet进行了大型重做。Sam Fisher（零）作为新干员加入。排位图池不变。"
  },
  {
    season: "Y5S4",
    seasonCode: "Y5S4",
    operation: "Neon Dawn",
    date: "2020-12-01",
    year: 5,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Skyscraper进行了中型重做（减少阳台依赖，增加室内进攻路线）。排位图池不变。"
  },

  // ==================== Year 6 (2021) ====================
  {
    season: "Y6S1",
    seasonCode: "Y6S1",
    operation: "Crimson Heist",
    date: "2021-03-16",
    year: 6,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Border进行了中型重做（二楼东翼区域重新设计）。Stadium作为永久地图加入但暂未进入Ranked池。"
  },
  {
    season: "Y6S2",
    seasonCode: "Y6S2",
    operation: "North Star",
    date: "2021-06-14",
    year: 6,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Favela进行了大型重做（减少软墙数量）。排位图池不变。"
  },
  {
    season: "Y6S3",
    seasonCode: "Y6S3",
    operation: "Crystal Guard",
    date: "2021-09-07",
    year: 6,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "多张地图进行了小幅调整（Bank等）。排位图池整体保持稳定。"
  },
  {
    season: "Y6S4",
    seasonCode: "Y6S4",
    operation: "High Calibre",
    date: "2021-12-07",
    year: 6,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Kafe Dostoyevsky", "Kanal",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Outback进行了调整。排位图池不变。整个Y6年度图池极为稳定。"
  },

  // ==================== Year 7 (2022) ====================
  {
    season: "Y7S1",
    seasonCode: "Y7S1",
    operation: "Demon Veil",
    date: "2022-03-15",
    year: 7,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Oregon", "Outback", "Skyscraper",
      "Theme Park", "Villa"
    ],
    added: ["Emerald Plains"],
    removed: [],
    notes: "Emerald Plains（翡翠平原）作为新地图加入排位。这是自Y4S1 Outback以来第一张直接加入排位池的全新地图。"
  },
  {
    season: "Y7S2",
    seasonCode: "Y7S2",
    operation: "Vector Glare",
    date: "2022-06-14",
    year: 7,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Oregon", "Outback",
      "Skyscraper", "Theme Park", "Villa"
    ],
    added: ["Close Quarter"],
    removed: [],
    notes: "Close Quarter（近距离）加入排位池。这张小型地图主打紧凑近距离战斗。"
  },
  {
    season: "Y7S3",
    seasonCode: "Y7S3",
    operation: "Brutal Swarm",
    date: "2022-09-06",
    year: 7,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Oregon", "Outback",
      "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Stadium Bravo作为新地图发布但未加入排位。排位图池不变。"
  },
  {
    season: "Y7S4",
    seasonCode: "Y7S4",
    operation: "Solar Raid",
    date: "2022-12-06",
    year: 7,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Nighthaven Labs",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: ["Nighthaven Labs"],
    removed: [],
    notes: "Nighthaven Labs（暗夜港湾实验室）加入排位。引入了Ranked 2.0系统和主机跨平台。"
  },

  // ==================== Year 8 (2023) ====================
  {
    season: "Y8S1",
    seasonCode: "Y8S1",
    operation: "Commanding Force",
    date: "2023-03-07",
    year: 8,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Nighthaven Labs",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "排位图池不变。MouseTrap反作弊系统上线。"
  },
  {
    season: "Y8S2",
    seasonCode: "Y8S2",
    operation: "Dread Factor",
    date: "2023-05-30",
    year: 8,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Nighthaven Labs",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Consulate进行了中型重做（部分点位重新设计）。排位图池不变。"
  },
  {
    season: "Y8S3",
    seasonCode: "Y8S3",
    operation: "Heavy Mettle",
    date: "2023-08-29",
    year: 8,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Nighthaven Labs",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Lair（巢穴）作为新地图发布。Quick Match 2.0上线。Lair暂未加入排位池。"
  },
  {
    season: "Y8S4",
    seasonCode: "Y8S4",
    operation: "Deep Freeze",
    date: "2023-12-05",
    year: 8,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Close Quarter", "Emerald Plains",
      "Kafe Dostoyevsky", "Kanal", "Lair", "Nighthaven Labs",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: ["Lair"],
    removed: [],
    notes: "Lair（巢穴）正式加入排位图池。排位池达到17张地图，为历史最大规模之一。"
  },

  // ==================== Year 9 (2024) ====================
  {
    season: "Y9S1",
    seasonCode: "Y9S1",
    operation: "Deadly Omen",
    date: "2024-03-05",
    year: 9,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: ["Close Quarter"],
    notes: "Close Quarter从排位池移除。新干员Deimos登场，Shield机制重做。"
  },
  {
    season: "Y9S2",
    seasonCode: "Y9S2",
    operation: "New Blood",
    date: "2024-06-11",
    year: 9,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Recruit重做（Striker & Sentry）。会员系统上线。排位图池不变。"
  },
  {
    season: "Y9S3",
    seasonCode: "Y9S3",
    operation: "Twin Shells",
    date: "2024-09-03",
    year: 9,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "新干员Skopos登场。无人机机制大改。排位图池不变。"
  },
  {
    season: "Y9S4",
    seasonCode: "Y9S4",
    operation: "Collision Point",
    date: "2024-12-03",
    year: 9,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Blackbeard重做。Siege Cup测试版。排位图池不变。整个Y9图池非常稳定。"
  },

  // ==================== Year 10 (2025) - 围攻X ====================
  {
    season: "Y10S1",
    seasonCode: "Y10S1",
    operation: "围攻X预热",
    date: "2025-03-04",
    year: 10,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "围攻X准备期，排位图池维持不变。"
  },
  {
    season: "Y10S2",
    seasonCode: "Y10S2",
    operation: "Daybreak (围攻X)",
    date: "2025-06-11",
    year: 10,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "围攻X正式上线！游戏转免费。Bank、Kafe、Chalet、Border、Club House 5张地图获得视觉翻新+环境互动系统。引入6v6双重战线模式。排位图池不变。"
  },
  {
    season: "Y10S3",
    seasonCode: "Y10S3",
    operation: "High Stakes",
    date: "2025-09-01",
    year: 10,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Kafe Dostoyevsky",
      "Kanal", "Lair", "Nighthaven Labs", "Oregon",
      "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: [],
    removed: [],
    notes: "Consulate、Stadium、Nighthaven Labs 3张地图获得视觉翻新。新干员Denari登场。排位图池不变。"
  },
  {
    season: "Y10S4",
    seasonCode: "Y10S4",
    operation: "Tenfold Pursuit",
    date: "2025-12-02",
    year: 10,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Fortress",
      "Kafe Dostoyevsky", "Kanal", "Lair", "Nighthaven Labs",
      "Oregon", "Outback", "Skyscraper", "Theme Park", "Villa"
    ],
    added: ["Fortress"],
    removed: [],
    notes: "Fortress（堡垒）经完全重做后加入排位池！这是Fortress自2018年发布以来首次进入排位。Theme Park和Skyscraper获得视觉翻新。Thatcher重做。10周年庆典。"
  },

  // ==================== Year 11 (2026) ====================
  {
    season: "Y11S1",
    seasonCode: "Y11S1",
    operation: "Silent Hunt",
    date: "2026-03-03",
    year: 11,
    pool: [
      "Bank", "Border", "Chalet", "Club House", "Coastline",
      "Consulate", "Emerald Plains", "Fortress",
      "Kafe Dostoyevsky", "Lair", "Nighthaven Labs",
      "Oregon", "Villa"
    ],
    added: [],
    removed: ["Kanal", "Skyscraper", "Theme Park", "Outback"],
    midSeasonChange: {
      description: "Y11S1引入了双阶段地图轮换机制，赛季中段会发生图池变化",
      phase2: {
        removed: ["Coastline", "Villa", "Oregon", "Emerald Plains"],
        added: ["Skyscraper", "Theme Park", "Stadium Bravo", "Favela"],
        pool: [
          "Bank", "Border", "Chalet", "Club House",
          "Consulate", "Favela", "Fortress",
          "Kafe Dostoyevsky", "Lair", "Nighthaven Labs",
          "Skyscraper", "Stadium Bravo", "Theme Park"
        ]
      }
    },
    notes: "首次引入双阶段地图轮换机制！第一阶段移除Kanal、Skyscraper、Theme Park、Outback，图池缩至13张。赛季中段进行第二波轮换：Coastline、Villa、Oregon、Emerald Plains被移出，Skyscraper、Theme Park回归，并加入Stadium Bravo和Favela。合金装备联动干员Solid Snake登场。Coastline、Villa、Oregon获得视觉翻新。"
  }
];

// 统计辅助数据
const RANKED_POOL_STATS = {
  // 在排位池中待过最久的地图（从未被移出）
  neverRemoved: ["Bank", "Border", "Chalet", "Club House", "Consulate", "Kafe Dostoyevsky", "Oregon"],
  // 被移出过排位池的地图
  removedAtLeastOnce: [
    { map: "Favela", removedIn: "Y2S2", reason: "攻防严重不平衡" },
    { map: "Yacht", removedIn: "Y2S2", reason: "线性布局+平衡问题" },
    { map: "Plane", removedIn: "Y2S2", reason: "线性布局不适合竞技" },
    { map: "Hereford Base", removedIn: "Y2S3 / Y4S1", reason: "原版不适合竞技；重做版争议过大" },
    { map: "House", removedIn: "Y2S3", reason: "地图过小不适合竞技" },
    { map: "Tower", removedIn: "Y3S1", reason: "地图过大+无可破坏外墙（仅待了1个赛季）" },
    { map: "Theme Park", removedIn: "Y3S2 / Y11S1", reason: "光照问题 / 图池轮换" },
    { map: "Close Quarter", removedIn: "Y9S1", reason: "竞技适用性不足" },
    { map: "Kanal", removedIn: "Y11S1", reason: "双阶段轮换机制调整" },
    { map: "Skyscraper", removedIn: "Y11S1", reason: "双阶段轮换（后在第二阶段回归）" },
    { map: "Outback", removedIn: "Y11S1", reason: "双阶段轮换机制调整" }
  ],
  // 从休闲到排位的逆袭
  casualToRanked: [
    { map: "Fortress", addedIn: "Y10S4", note: "经完全重做后从休闲地图晋升为排位地图" },
    { map: "Hereford Base", addedIn: "Y3S3", note: "经完全重做后重回排位，但后来又被移出" }
  ],
  // 地图在排位池中存在的总赛季数（截至Y11S1第一阶段）
  totalSeasonsInPool: {
    "Bank": "全勤（所有赛季）",
    "Border": "全勤（所有赛季）",
    "Chalet": "全勤（所有赛季）",
    "Club House": "全勤（所有赛季）",
    "Consulate": "全勤（所有赛季）",
    "Kafe Dostoyevsky": "全勤（所有赛季）",
    "Oregon": "全勤（所有赛季）",
    "Coastline": "Y2S1起全勤",
    "Kanal": "多数赛季（Y11S1被移出）",
    "Villa": "Y3S2起至今",
    "Skyscraper": "Y1S4起（Y11S1第一阶段被移出，第二阶段回归）",
    "Outback": "Y4S1-Y10S4",
    "Theme Park": "断断续续（Y2S3加入→Y3S2移出→Y4S3回归→Y11S1移出后第二阶段回归）",
    "Emerald Plains": "Y7S1起",
    "Nighthaven Labs": "Y7S4起",
    "Lair": "Y8S4起",
    "Fortress": "Y10S4起（完全重做后）",
    "Close Quarter": "Y7S2-Y8S4（4个赛季）",
    "Tower": "Y2S4（仅1个赛季，最短记录）",
    "Hereford Base": "发售-Y2S3(被移出) → Y3S3-Y3S4/Y4S1(重做后短暂回归)",
    "Favela": "发售-Y2S2",
    "Yacht": "发售-Y2S2",
    "Plane": "发售-Y2S2",
    "House": "发售-Y2S3"
  }
};

if (typeof module !== 'undefined') module.exports = { RANKED_POOL_HISTORY, RANKED_POOL_STATS };

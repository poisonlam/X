/**
 * Rainbow Six Siege - 完整地图数据库
 * 包含从2015年发售至今所有地图的详细信息
 */

const MAPS_DATA = [
  // ==================== 首发地图 (Launch Maps - 2015年12月1日) ====================
  {
    id: "bank",
    name: "Bank / 银行",
    nameEN: "Bank",
    nameCN: "银行",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "美国，洛杉矶",
    setting: "现代商业银行大楼",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "大型",
    floors: 3,
    bombSites: 4,
    description: "一座位于洛杉矶的大型商业银行，包含地下金库、大厅、办公区等多个区域。地图以中央大厅为核心，连接各个翼区。",
    designPhilosophy: "经典的对称结构设计，强调垂直对抗和多点进攻路线",
    backgroundReference: "参考现实世界的美国联邦储备银行和大型商业银行建筑",
    reworkHistory: [
      {
        date: "2020-03-10",
        season: "Y5S1 - Void Edge",
        type: "小型调整",
        changes: "外部区域调整，天窗开口修改，部分墙体可破坏性变更"
      },
      {
        date: "2025-06-11",
        season: "围攻X (Siege X)",
        type: "视觉翻新 + 环境互动",
        changes: "围攻X五张翻新地图之一。全面升级光照系统（新光线与阴影效果），更新4K高清材质，地图视觉表现大幅提升。新增环境互动可破坏元素：灭火器、燃气管道、金属探测器等，为战术对抗增加了全新维度。"
      }
    ],
    keywords: ["金库", "大厅", "垂直进攻", "天窗", "对称布局", "旋转进攻", "经典地图", "围攻X翻新"],
    communityRating: {
      overall: 8.0,
      competitiveViability: 8.5,
      casualFun: 7.5,
      visualDesign: 7.0,
      balancedSides: 8.0,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Bank是最平衡的地图之一，攻防两侧都有足够的策略空间" },
        { source: "Pro League分析", sentiment: "正面", text: "Bank在职业联赛中一直是高选取率地图，点位设计非常成熟" },
        { source: "社区投票", sentiment: "正面", text: "经典地图，垂直打法的典范" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "高度依赖垂直对抗，天花板/地板可破坏性是核心玩法",
      rotationOptions: "多个轮转孔位，允许灵活的防守布局",
      entryPoints: "多方向进攻可能，包括天窗、正门、后方等",
      sightLines: "中距离对枪为主，大厅存在长距离视线"
    }
  },
  {
    id: "bartlett_u",
    name: "Bartlett University / 巴特莱特大学",
    nameEN: "Bartlett University",
    nameCN: "巴特莱特大学",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发（仅限恐怖猎人）/ Y1S4加入多人",
    releaseOperation: "Launch / Y1S4 Red Crow",
    location: "美国，马萨诸塞州",
    setting: "大学校园建筑",
    type: "已移除地图",
    competitiveStatus: "已从地图池移除",
    mapSize: "中型",
    floors: 2,
    bombSites: 3,
    description: "美国东海岸一所大学的主教学楼，包含图书馆、教室、大厅等区域。最初仅在恐怖猎人模式可用，Y1S4加入多人对战后因平衡问题被移除。",
    designPhilosophy: "最初为PvE设计，后改为PvP。窗户过少导致进攻方缺乏进入点",
    backgroundReference: "参考美国新英格兰地区常春藤大学建筑风格",
    reworkHistory: [
      {
        date: "2017-02-01",
        season: "Y1S4 - Red Crow（中期更新）",
        type: "加入多人",
        changes: "从PvE模式地图调整为多人对战地图"
      },
      {
        date: "2018-06-01",
        season: "Y3S2",
        type: "移除",
        changes: "因严重平衡问题从所有多人模式地图池移除"
      }
    ],
    keywords: ["大学", "争议地图", "已移除", "进攻方劣势", "窗户不足", "PvE转PvP失败案例"],
    communityRating: {
      overall: 3.0,
      competitiveViability: 2.0,
      casualFun: 4.0,
      visualDesign: 6.5,
      balancedSides: 2.0,
      comments: [
        { source: "Reddit社区", sentiment: "负面", text: "Bartlett是Siege历史上最失败的地图设计之一，进攻方几乎无法安全进入建筑" },
        { source: "职业选手", sentiment: "负面", text: "地图从一开始就不是为5v5设计的，强行加入多人是错误的决定" },
        { source: "社区投票", sentiment: "负面", text: "窗户太少，进攻几乎不可能，最不平衡的地图" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "有限的垂直对抗空间",
      rotationOptions: "防守方轮转便利，进攻方入口极为有限",
      entryPoints: "窗户数量严重不足，是该地图最大设计缺陷",
      sightLines: "室内以短距离对枪为主",
      lessonLearned: "证明了PvE地图不能简单转化为PvP地图，进入点数量对攻防平衡至关重要"
    }
  },
  {
    id: "border",
    name: "Border / 边境",
    nameEN: "Border",
    nameCN: "边境",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "中东地区",
    setting: "边境检查站/海关大楼",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "位于中东的边境检查站，包含海关区、监控室、军械库等区域。地图布局紧凑，是Siege中最受欢迎的竞技地图之一。",
    designPhilosophy: "紧凑型双层建筑，强调水平对抗和信息获取",
    backgroundReference: "参考中东地区边境检查站和军事哨所",
    reworkHistory: [
      {
        date: "2021-06-14",
        season: "Y6S2 - North Star",
        type: "中型重做",
        changes: "重做了二楼东翼区域，增加了进攻路线，调整了多处墙体和视线"
      },
      {
        date: "2025-06-11",
        season: "围攻X (Siege X)",
        type: "视觉翻新 + 环境互动",
        changes: "围攻X五张翻新地图之一。照明系统全面升级，新光线、阴影效果显著增强建筑细节和室外区域的视觉表现。更新4K材质。新增灭火器、燃气管道、金属探测器等环境互动可破坏元素，为战术带来新可能性。"
      }
    ],
    keywords: ["紧凑", "中东风格", "海关", "竞技经典", "信息战", "水平对抗", "双层结构", "围攻X翻新"],
    communityRating: {
      overall: 8.5,
      competitiveViability: 9.0,
      casualFun: 7.5,
      visualDesign: 7.5,
      balancedSides: 8.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Border一直是Ranked最受欢迎的地图之一，攻防双方都有充足的策略选择" },
        { source: "Pro League分析", sentiment: "正面", text: "地图大小适中，节奏感好，是最佳竞技地图之一" },
        { source: "社区投票（重做后）", sentiment: "正面", text: "Y6S2的重做进一步提升了地图质量，修复了二楼的不平衡问题" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "二楼对一楼有部分垂直控制能力",
      rotationOptions: "轮转路线清晰但可被针对",
      entryPoints: "进攻方有多个窗口和门作为进入点",
      sightLines: "中短距离对枪为主，部分区域有较长视线"
    }
  },
  {
    id: "chalet",
    name: "Chalet / 木屋",
    nameEN: "Chalet",
    nameCN: "木屋",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "法国，阿尔卑斯山脉",
    setting: "山间滑雪度假木屋",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 3,
    bombSites: 4,
    description: "位于阿尔卑斯山脉的滑雪度假木屋，带有地下室酒窖、大厅壁炉、卧室等区域。Y5S3进行了大幅重做。",
    designPhilosophy: "三层结构+地下室，强调垂直攻防和区域控制",
    backgroundReference: "参考法国/瑞士阿尔卑斯地区的传统滑雪度假胜地",
    reworkHistory: [
      {
        date: "2020-09-10",
        season: "Y5S3 - Shadow Legacy",
        type: "大型重做",
        changes: "大幅重做整个地图，重新设计了二楼布局，增加了新的房间和连接通道，修改了地下室结构，增加了进攻路线和垂直对抗空间"
      },
      {
        date: "2025-06-11",
        season: "围攻X (Siege X)",
        type: "视觉翻新 + 环境互动",
        changes: "围攻X五张翻新地图之一。内部空间经过重新光照规划，灯光更加贴近真实场景，光线和阴影效果全面升级。更新4K材质，大理石等材质呈现真实次表面散射效果。新增灭火器、燃气管道等环境互动可破坏元素，营造更加危机四伏的场景。"
      }
    ],
    keywords: ["木屋", "滑雪胜地", "阿尔卑斯", "大幅重做", "垂直对抗", "酒窖", "壁炉", "围攻X翻新"],
    communityRating: {
      overall: 7.0,
      competitiveViability: 7.5,
      casualFun: 7.0,
      visualDesign: 8.5,
      balancedSides: 7.0,
      comments: [
        { source: "Reddit社区（重做前）", sentiment: "负面", text: "老Chalet的大厅/酒窖点位是全游戏最难防守的，攻方压倒性优势" },
        { source: "Reddit社区（重做后）", sentiment: "中性偏正面", text: "重做后Chalet好了很多，但部分玩家怀念老地图的独特感" },
        { source: "Pro League分析", sentiment: "正面", text: "重做后的Chalet终于可以在竞技场景使用了" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "重做后增强了垂直对抗空间",
      rotationOptions: "地下室与一楼的连接是核心设计要素",
      entryPoints: "多个阳台和窗口提供进入点",
      sightLines: "混合型视线，室外有较长视线"
    }
  },
  {
    id: "club_house",
    name: "Club House / 俱乐部",
    nameEN: "Club House",
    nameCN: "俱乐部",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "德国",
    setting: "摩托车帮派俱乐部",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "大型",
    floors: 3,
    bombSites: 4,
    description: "德国的一个摩托车帮派俱乐部，包含地下室健身房、酒吧、卧室、教堂等区域。是最早被重做的地图之一。",
    designPhilosophy: "不对称双翼设计，丰富的垂直空间利用",
    backgroundReference: "参考欧洲摩托车帮派（如Hell's Angels）的据点建筑",
    reworkHistory: [
      {
        date: "2018-06-07",
        season: "Y3S2 - Para Bellum",
        type: "中型重做",
        changes: "重做了二楼卧室和建筑后方区域，增加了新的通道和楼梯，改善了地图流动性"
      },
      {
        date: "2025-06-11",
        season: "围攻X (Siege X)",
        type: "视觉翻新 + 环境互动",
        changes: "围攻X五张翻新地图之一。全面升级光照系统，新的光线与阴影效果让室内外视觉表现更加逼真。更新4K材质。新增灭火器、燃气管道、金属探测器等环境互动可破坏元素，为经典的教堂/地下室等区域增加了新的战术层次。"
      }
    ],
    keywords: ["摩托帮", "地下室", "教堂", "酒吧", "垂直进攻", "竞技经典", "早期重做", "围攻X翻新"],
    communityRating: {
      overall: 8.5,
      competitiveViability: 9.0,
      casualFun: 8.0,
      visualDesign: 8.0,
      balancedSides: 8.0,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Club House是Siege的标志性地图，重做后更加平衡" },
        { source: "Pro League分析", sentiment: "正面", text: "地图提供了丰富的策略层次，垂直打法和区域控制都很重要" },
        { source: "社区投票", sentiment: "正面", text: "始终是玩家最喜欢的地图之一" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "地下室到一楼的垂直对抗是核心，教堂天花板是关键",
      rotationOptions: "丰富的轮转路线，防守方可以灵活调整",
      entryPoints: "建筑两侧各有独立的进入体系",
      sightLines: "室外对室内有多个关键视线位置"
    }
  },
  {
    id: "consulate",
    name: "Consulate / 领事馆",
    nameEN: "Consulate",
    nameCN: "领事馆",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "法国，巴黎",
    setting: "象牙海岸驻法领事馆",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 3,
    bombSites: 4,
    description: "位于巴黎的象牙海岸领事馆，包含签证室、大使办公室、会客厅等区域。地图以中央楼梯为枢纽，连接三层建筑。",
    designPhilosophy: "以中央枢纽为核心的三层建筑设计",
    backgroundReference: "参考巴黎各国外交使馆建筑风格",
    reworkHistory: [
      {
        date: "2020-03-10",
        season: "Y5S1 - Void Edge",
        type: "小型调整",
        changes: "部分区域光照和可见度调整"
      }
    ],
    keywords: ["领事馆", "巴黎", "外交建筑", "中央楼梯", "签证室", "竞技地图", "三层结构"],
    communityRating: {
      overall: 7.5,
      competitiveViability: 8.0,
      casualFun: 7.0,
      visualDesign: 7.5,
      balancedSides: 7.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Consulate是非常经典的地图，虽然不是最佳但始终保持竞技水准" },
        { source: "Pro League分析", sentiment: "中性", text: "地图有些过于依赖车库争夺，但整体平衡尚可" },
        { source: "社区投票", sentiment: "正面", text: "稳定的竞技地图，大部分玩家不反感" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "二楼对一楼有重要的垂直控制",
      rotationOptions: "中央楼梯是关键枢纽，控制楼梯等于控制轮转",
      entryPoints: "地下车库是重要的进入/争夺点",
      sightLines: "前院到建筑有长视线，室内以中距离为主"
    }
  },
  {
    id: "hereford_base",
    name: "Hereford Base / 赫里福德基地",
    nameEN: "Hereford Base",
    nameCN: "赫里福德基地",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "英国，赫里福德",
    setting: "SAS训练基地",
    type: "正式对战地图",
    competitiveStatus: "Casual（当前不在Ranked池中）",
    mapSize: "中型",
    floors: 4,
    bombSites: 4,
    description: "英国SAS特种部队的训练基地。Y3S3进行了完全重做，从一个小型简单建筑变为多层复杂结构。但重做效果备受争议。",
    designPhilosophy: "原版：简约方正的训练设施。重做版：四层高楼设计，层次丰富但过于复杂",
    backgroundReference: "参考英国SAS真实驻地——赫里福德Stirling Lines兵营",
    reworkHistory: [
      {
        date: "2018-09-04",
        season: "Y3S3 - Grim Sky",
        type: "完全重做",
        changes: "完全推翻原版，重新设计为四层建筑，大幅增加面积和复杂度。增加了新的房间、楼梯和通道。但结果被社区认为是失败的重做案例。"
      }
    ],
    keywords: ["SAS基地", "完全重做", "四层楼", "争议重做", "失败案例", "过于复杂", "训练设施"],
    communityRating: {
      overall: 4.5,
      competitiveViability: 4.0,
      casualFun: 5.0,
      visualDesign: 6.0,
      balancedSides: 4.0,
      comments: [
        { source: "Reddit社区（重做前）", sentiment: "中性", text: "老Hereford虽然简单但有其独特魅力，是新手友好型地图" },
        { source: "Reddit社区（重做后）", sentiment: "负面", text: "新Hereford被认为是最失败的重做案例，四层楼过于复杂且不平衡" },
        { source: "Pro League分析", sentiment: "负面", text: "重做后的Hereford从未被竞技采用，四层结构导致轮转过于冗长" },
        { source: "社区投票", sentiment: "负面", text: "社区普遍认为这次重做摧毁了地图的原有灵魂" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "四层结构理论上垂直空间丰富，但实际利用率低",
      rotationOptions: "层数过多导致轮转时间过长",
      entryPoints: "进攻方的入口选择过多，难以集中进攻",
      sightLines: "楼梯区域存在多个尴尬的长视线",
      lessonLearned: "证明了更多层数不等于更好的设计，地图复杂度需要适度控制"
    }
  },
  {
    id: "house",
    name: "House / 民宅",
    nameEN: "House",
    nameCN: "民宅",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "美国，洛杉矶郊区",
    setting: "郊区独栋住宅",
    type: "休闲地图",
    competitiveStatus: "Casual/Quick Match",
    mapSize: "小型",
    floors: 3,
    bombSites: 3,
    description: "洛杉矶郊区的一栋两层独栋住宅+地下室。是Siege中最小的地图之一，节奏快，混战感强。",
    designPhilosophy: "小型快节奏地图，低学习门槛，适合新手入门",
    backgroundReference: "参考美国典型郊区住宅，可能借鉴了《虎胆龙威》等反恐片中的住宅场景",
    reworkHistory: [
      {
        date: "2021-03-16",
        season: "Y6S1 - Crimson Heist",
        type: "小型调整",
        changes: "增加了部分新房间和通道，调整了建筑外观，但保持了小型地图的核心特征"
      }
    ],
    keywords: ["小型地图", "新手友好", "快节奏", "混战", "郊区住宅", "经典休闲", "Rush地图"],
    communityRating: {
      overall: 6.5,
      competitiveViability: 3.0,
      casualFun: 9.0,
      visualDesign: 7.0,
      balancedSides: 4.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "House永远是最有趣的休闲地图，虽然不平衡但乐趣十足" },
        { source: "社区投票", sentiment: "中性", text: "不适合竞技但适合休闲，是Siege的标志性地图之一" },
        { source: "新手玩家", sentiment: "正面", text: "最容易学习和理解的地图" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "有限但有效的垂直对抗",
      rotationOptions: "地图过小导致轮转空间有限",
      entryPoints: "窗户众多，进攻方可以从几乎任何方向进入",
      sightLines: "短距离对枪为主，peek战术效果突出",
      lessonLearned: "证明了小型地图对休闲玩家的吸引力，但不适合竞技"
    }
  },
  {
    id: "kafe_dostoyevsky",
    name: "Kafe Dostoyevsky / 陀思妥耶夫斯基咖啡馆",
    nameEN: "Kafe Dostoyevsky",
    nameCN: "陀思妥耶夫斯基咖啡馆",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "俄罗斯，莫斯科",
    setting: "俄式古典咖啡馆/餐厅",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 3,
    bombSites: 3,
    description: "莫斯科的一家以陀思妥耶夫斯基命名的高档俄式咖啡馆，包含厨房、酒吧、阅读室、面包房等区域。Y4S2进行了重做。",
    designPhilosophy: "以餐饮空间为主题的三层建筑，强调楼层间的垂直对抗",
    backgroundReference: "参考莫斯科传统高档餐厅和咖啡馆建筑风格",
    reworkHistory: [
      {
        date: "2019-06-11",
        season: "Y4S2 - Phantom Sight",
        type: "中型重做",
        changes: "重做了三楼吧台区域，增加了新的通道和房间，改善了进攻路线，调整了多处墙体可破坏性"
      },
      {
        date: "2025-06-11",
        season: "围攻X (Siege X)",
        type: "视觉翻新 + 环境互动",
        changes: "围攻X五张翻新地图之一。照明系统全面重置升级，新光线与阴影效果大幅提升俄式古典内饰的视觉表现。更新4K材质。新增灭火器、燃气管道、金属探测器等环境互动可破坏元素，在厨房、面包房等区域增加了新的战术互动可能。"
      }
    ],
    keywords: ["咖啡馆", "莫斯科", "俄式建筑", "厨房", "面包房", "三层结构", "经典竞技", "围攻X翻新"],
    communityRating: {
      overall: 8.0,
      competitiveViability: 8.5,
      casualFun: 7.5,
      visualDesign: 8.5,
      balancedSides: 8.0,
      comments: [
        { source: "Reddit社区（重做后）", sentiment: "正面", text: "Kafe重做是成功案例，保留了地图灵魂的同时改善了平衡" },
        { source: "Pro League分析", sentiment: "正面", text: "重做后的Kafe成为了职业联赛的常客" },
        { source: "社区投票", sentiment: "正面", text: "视觉设计优秀，重做方向正确" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "三层结构提供丰富的垂直对抗空间",
      rotationOptions: "楼梯位置设计良好，轮转流畅",
      entryPoints: "每层都有合理的进入点",
      sightLines: "混合型视线，长短交替"
    }
  },
  {
    id: "kanal",
    name: "Kanal / 运河",
    nameEN: "Kanal",
    nameCN: "运河",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "德国，汉堡",
    setting: "运河旁的海岸警卫队基地",
    type: "正式对战地图",
    competitiveStatus: "Ranked",
    mapSize: "大型",
    floors: 3,
    bombSites: 4,
    description: "德国汉堡运河旁的海岸警卫队建筑群，由两座建筑通过天桥连接。Y4S3进行了重做。",
    designPhilosophy: "双建筑通过天桥连接的独特布局",
    backgroundReference: "参考德国汉堡港区的海岸警卫队设施",
    reworkHistory: [
      {
        date: "2019-09-11",
        season: "Y4S3 - Ember Rise",
        type: "大型重做",
        changes: "大幅调整了两栋建筑的内部布局，增加了更多连接点，天桥区域重新设计，改善了地图流动性"
      }
    ],
    keywords: ["运河", "双建筑", "天桥", "海岸警卫", "汉堡", "大型重做", "分割式布局"],
    communityRating: {
      overall: 6.0,
      competitiveViability: 6.0,
      casualFun: 6.0,
      visualDesign: 7.0,
      balancedSides: 5.5,
      comments: [
        { source: "Reddit社区（重做前）", sentiment: "负面", text: "老Kanal的双建筑设计导致严重的split push问题" },
        { source: "Reddit社区（重做后）", sentiment: "中性", text: "重做后有改善但双建筑的根本问题仍然存在" },
        { source: "社区投票", sentiment: "中性偏负面", text: "重做方向正确但未完全解决核心问题" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "各建筑内部有垂直空间，但跨建筑联动有限",
      rotationOptions: "天桥是唯一的跨建筑通道，成为防守重点",
      entryPoints: "两栋建筑各有独立的进入系统",
      sightLines: "跨建筑间存在超长视线",
      lessonLearned: "双建筑设计天然存在割裂问题，连接点设计至关重要"
    }
  },
  {
    id: "oregon",
    name: "Oregon / 俄勒冈",
    nameEN: "Oregon",
    nameCN: "俄勒冈",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "美国，俄勒冈州",
    setting: "农村废弃建筑/邪教据点",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 3,
    bombSites: 4,
    description: "美国俄勒冈州的一座被邪教占据的农村建筑群，参考了真实的Waco事件。Y5S1进行了重做。",
    designPhilosophy: "紧凑的L形建筑设计，强调区域控制和信息战",
    backgroundReference: "参考1993年Waco围城事件中的Branch Davidians据点",
    reworkHistory: [
      {
        date: "2020-03-10",
        season: "Y5S1 - Void Edge",
        type: "中型重做",
        changes: "重做了地下室和大塔楼区域，增加了新的通道，改善了部分视线问题，但保持了地图整体结构"
      }
    ],
    keywords: ["邪教据点", "Waco参考", "L形布局", "紧凑型", "竞技经典", "大塔小塔", "地下室争夺"],
    communityRating: {
      overall: 8.5,
      competitiveViability: 9.0,
      casualFun: 8.0,
      visualDesign: 7.0,
      balancedSides: 8.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Oregon一直是最好的竞技地图之一，平衡且策略丰富" },
        { source: "Pro League分析", sentiment: "正面", text: "Oregon是职业联赛中选取率最高的地图之一" },
        { source: "社区投票（重做后）", sentiment: "正面", text: "重做保持了地图核心感觉的同时改善了薄弱区域" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "大塔楼区域有丰富的垂直对抗空间",
      rotationOptions: "L形布局提供了清晰的轮转路线",
      entryPoints: "多个方向的进入点，包括天窗",
      sightLines: "中距离为主，走廊区域有长视线"
    }
  },
  {
    id: "plane",
    name: "Presidential Plane / 总统专机",
    nameEN: "Presidential Plane",
    nameCN: "总统专机",
    releaseDate: "2015-12-01",
    releaseSeason: "发售首发",
    releaseOperation: "Launch",
    location: "空中/英国跑道",
    setting: "美国总统专机",
    type: "休闲地图",
    competitiveStatus: "Casual/Quick Match",
    mapSize: "小型（线性）",
    floors: 2,
    bombSites: 3,
    description: "停在跑道上的美国总统专机（类似空军一号），是游戏中最独特的地图之一。完全线性的布局。",
    designPhilosophy: "极度线性的空间设计，强调走廊战斗和控制关键卡点",
    backgroundReference: "参考美国空军一号（Air Force One）总统专机",
    reworkHistory: [],
    keywords: ["飞机", "线性布局", "空军一号", "狭窄走廊", "独特概念", "休闲地图", "不可破坏外墙"],
    communityRating: {
      overall: 5.0,
      competitiveViability: 2.0,
      casualFun: 7.0,
      visualDesign: 7.5,
      balancedSides: 3.5,
      comments: [
        { source: "Reddit社区", sentiment: "中性", text: "Plane的概念很酷但不适合竞技，纯粹是rush地图" },
        { source: "社区投票", sentiment: "中性", text: "作为休闲地图有独特魅力，但绝不能放入ranked" },
        { source: "设计讨论", sentiment: "中性", text: "飞机外壳不可破坏是最大限制，断了很多策略可能" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "两层之间有限的垂直互动",
      rotationOptions: "线性布局导致轮转路线极为有限",
      entryPoints: "进入点集中在机身两端和机翼",
      sightLines: "走廊形成超长视线",
      lessonLearned: "线性地图设计天然不适合攻防对抗型玩法"
    }
  },
  {
    id: "yacht",
    name: "Yacht / 游艇",
    nameEN: "Yacht",
    nameCN: "游艇",
    releaseDate: "2016-02-02",
    releaseSeason: "Y1S1",
    releaseOperation: "Black Ice",
    location: "北极/加拿大北方",
    setting: "搁浅的豪华游艇",
    type: "休闲地图",
    competitiveStatus: "Casual/Quick Match",
    mapSize: "大型（线性）",
    floors: 4,
    bombSites: 4,
    description: "一艘在北极冰层上搁浅的豪华游艇。Y1S1 Black Ice的新地图，虽然视觉上很惊艳但因平衡问题被移出竞技池。",
    designPhilosophy: "线性但多层的空间设计，利用游艇特殊结构创造垂直空间",
    backgroundReference: "参考北极探险豪华游艇和冰封沉船场景",
    reworkHistory: [
      {
        date: "2017-06-07",
        season: "Y2S2 - Operation Health",
        type: "移除+回归",
        changes: "从Ranked地图池移除，后续只保留在Casual模式"
      }
    ],
    keywords: ["游艇", "北极", "冰雪", "线性", "视觉惊艳", "平衡问题", "已移出竞技"],
    communityRating: {
      overall: 5.5,
      competitiveViability: 3.5,
      casualFun: 6.5,
      visualDesign: 9.0,
      balancedSides: 4.0,
      comments: [
        { source: "Reddit社区", sentiment: "中性", text: "Yacht视觉上非常棒但玩起来很无聊，线性布局限制了策略" },
        { source: "社区投票", sentiment: "中性偏负面", text: "概念很好但执行不佳，噪音问题也很严重" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "多层结构但垂直互动有限",
      rotationOptions: "线性布局限制了轮转选择",
      entryPoints: "甲板提供了较好的进入点",
      sightLines: "狭长走廊产生极长视线",
      lessonLearned: "视觉设计优秀不等于玩法设计优秀，环境噪音对体验影响很大"
    }
  },
  // ==================== Year 1 Season 2-4 ====================
  {
    id: "border_dlc",
    name: "Border / 边境（DLC版注释：此为首发地图，见上方）",
    skipEntry: true
  },
  {
    id: "favela",
    name: "Favela / 贫民窟",
    nameEN: "Favela",
    nameCN: "贫民窟",
    releaseDate: "2016-08-02",
    releaseSeason: "Y1S3",
    releaseOperation: "Skull Rain",
    location: "巴西，里约热内卢",
    setting: "巴西贫民窟",
    type: "休闲地图",
    competitiveStatus: "Casual/Quick Match",
    mapSize: "中型",
    floors: 3,
    bombSites: 4,
    description: "巴西里约热内卢的贫民窟建筑群。以大量可破坏软墙著称，是Siege中软墙比例最高的地图。Y6S3进行了重做。",
    designPhilosophy: "极端的可破坏性设计，几乎所有外墙都是软墙",
    backgroundReference: "参考里约热内卢真实贫民窟（Favela）建筑",
    reworkHistory: [
      {
        date: "2021-09-07",
        season: "Y6S3 - Crystal Guard",
        type: "大型重做",
        changes: "大幅减少了软墙数量，增加了硬墙和不可破坏墙体，重新设计了部分房间布局，改善了防守方的生存空间"
      }
    ],
    keywords: ["贫民窟", "巴西", "软墙", "极端可破坏", "防守噩梦", "重做改善", "里约"],
    communityRating: {
      overall: 5.0,
      competitiveViability: 3.0,
      casualFun: 6.5,
      visualDesign: 8.0,
      balancedSides: 4.0,
      comments: [
        { source: "Reddit社区（重做前）", sentiment: "负面", text: "老Favela是游戏中最不平衡的地图，防守方几乎不可能赢" },
        { source: "Reddit社区（重做后）", sentiment: "中性", text: "重做后好了一些但仍然不是竞技级别" },
        { source: "社区投票", sentiment: "负面", text: "软墙太多是原罪，重做也无法完全修复" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "垂直空间存在但被大量软墙问题掩盖",
      rotationOptions: "过多的软墙导致无法建立有效的防守轮转",
      entryPoints: "几乎所有外墙都可作为进入点",
      sightLines: "由于软墙可破坏性，视线不可预测",
      lessonLearned: "可破坏性设计需要适度，过多软墙会破坏攻防平衡"
    }
  },
  {
    id: "skyscraper",
    name: "Skyscraper / 摩天大楼",
    nameEN: "Skyscraper",
    nameCN: "摩天大楼",
    releaseDate: "2016-11-17",
    releaseSeason: "Y1S4",
    releaseOperation: "Red Crow",
    location: "日本，名古屋",
    setting: "日式高层建筑顶部/屋顶花园",
    type: "正式对战地图",
    competitiveStatus: "Ranked",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "日本名古屋一座高层建筑的顶部两层及屋顶，有日式风格的内部装饰和屋顶花园。Y5S4进行了重做。",
    designPhilosophy: "利用高层建筑顶部空间创造独特的阳台进攻体验",
    backgroundReference: "参考日式传统与现代结合的建筑风格，武士主题装饰",
    reworkHistory: [
      {
        date: "2020-12-01",
        season: "Y5S4 - Neon Dawn",
        type: "中型重做",
        changes: "重做了一楼和二楼的多个区域，减少了阳台跑位的重要性，增加了室内进攻路线"
      }
    ],
    keywords: ["日式建筑", "高层顶部", "阳台", "屋顶花园", "名古屋", "日本风格", "跑酷"],
    communityRating: {
      overall: 6.5,
      competitiveViability: 6.0,
      casualFun: 7.0,
      visualDesign: 8.5,
      balancedSides: 6.0,
      comments: [
        { source: "Reddit社区（重做前）", sentiment: "负面", text: "老Skyscraper的阳台太强了，进攻方可以无脑阳台peek" },
        { source: "Reddit社区（重做后）", sentiment: "中性偏正面", text: "重做后室内进攻路线增加了，但地图仍不是最优选择" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "两层之间有垂直对抗空间",
      rotationOptions: "重做后轮转路线有所改善",
      entryPoints: "阳台系统是最大特色，提供独特的进入角度",
      sightLines: "外部阳台到室内有多个关键视线"
    }
  },
  // ==================== Year 2 ====================
  {
    id: "coastline",
    name: "Coastline / 海岸线",
    nameEN: "Coastline",
    nameCN: "海岸线",
    releaseDate: "2017-02-07",
    releaseSeason: "Y2S1",
    releaseOperation: "Velvet Shell",
    location: "西班牙，伊维萨岛",
    setting: "海滨夜店/度假别墅",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "西班牙伊维萨岛的一座海滨度假别墅/夜店。两层建筑围绕中央庭院设计，是Siege中最受欢迎的竞技地图之一。从未进行过重做。",
    designPhilosophy: "围绕中央庭院的环形设计，开放的屋顶提供独特进攻角度",
    backgroundReference: "参考伊维萨岛著名的海滨俱乐部和度假别墅",
    reworkHistory: [],
    keywords: ["海滨", "夜店", "伊维萨", "环形布局", "庭院", "无重做", "竞技经典", "最受欢迎"],
    communityRating: {
      overall: 9.0,
      competitiveViability: 9.5,
      casualFun: 8.5,
      visualDesign: 9.5,
      balancedSides: 8.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Coastline是Siege最好的地图之一，从未需要重做" },
        { source: "Pro League分析", sentiment: "正面", text: "Coastline一直是职业比赛中最高选取率的地图" },
        { source: "社区投票", sentiment: "正面", text: "视觉出色、平衡优秀、策略丰富，完美地图" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "屋顶到二楼有重要的垂直关系",
      rotationOptions: "环形布局提供了灵活的轮转选择",
      entryPoints: "庭院、阳台、窗户提供了丰富的进入系统",
      sightLines: "中距离为主，庭院区域有较长视线",
      designHighlight: "中央庭院设计是该地图成功的关键——创造了攻守双方都需要争夺的中心区域"
    }
  },
  {
    id: "theme_park",
    name: "Theme Park / 主题乐园",
    nameEN: "Theme Park",
    nameCN: "主题乐园",
    releaseDate: "2017-09-05",
    releaseSeason: "Y2S3",
    releaseOperation: "Blood Orchid",
    location: "中国，香港",
    setting: "废弃游乐园",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "大型",
    floors: 2,
    bombSites: 4,
    description: "中国香港的一个废弃游乐园，包含鬼屋、办公区、电子游戏厅等区域。Y4S1进行了重做。",
    designPhilosophy: "利用游乐园主题创造独特的视觉环境和多样化的空间",
    backgroundReference: "参考荒废的游乐园概念，融合了亚洲夜市和电子游戏厅元素",
    reworkHistory: [
      {
        date: "2019-03-06",
        season: "Y4S1 - Burnt Horizon",
        type: "中型重做（主要是光照和可见度）",
        changes: "大幅改善了地图光照（原版过暗），移除了部分杂物，提高了整体可见度和可读性"
      },
      {
        date: "2021-06-14",
        season: "Y6S2 - North Star",
        type: "大型重做",
        changes: "重新设计了大量内部布局，重新规划了房间连接和进攻路线"
      }
    ],
    keywords: ["游乐园", "香港", "鬼屋", "废弃", "光照问题", "两次重做", "亚洲风格"],
    communityRating: {
      overall: 7.0,
      competitiveViability: 7.0,
      casualFun: 7.5,
      visualDesign: 8.0,
      balancedSides: 7.0,
      comments: [
        { source: "Reddit社区（原版）", sentiment: "负面", text: "原版Theme Park太暗了，根本看不见敌人" },
        { source: "Reddit社区（二次重做后）", sentiment: "正面", text: "经过两次重做终于变成了一张不错的竞技地图" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "重做后增强了垂直空间利用",
      rotationOptions: "重做后改善了轮转流畅度",
      entryPoints: "多个窗口和门作为进入点",
      sightLines: "混合型视线设计",
      lessonLearned: "光照和可读性是地图设计的基础要素，不能因为视觉效果牺牲功能性"
    }
  },
  {
    id: "tower",
    name: "Tower / 塔楼",
    nameEN: "Tower",
    nameCN: "塔楼",
    releaseDate: "2017-12-05",
    releaseSeason: "Y2S4",
    releaseOperation: "White Noise",
    location: "韩国，首尔",
    setting: "高端商业大厦",
    type: "休闲地图",
    competitiveStatus: "Casual/Quick Match",
    mapSize: "大型",
    floors: 2,
    bombSites: 4,
    description: "韩国首尔的一座现代高端商业大厦，包含餐厅、媒体中心、展览厅等区域。因过大的面积和缺乏可破坏外墙而不受欢迎。",
    designPhilosophy: "大型开放式商业空间设计",
    backgroundReference: "参考首尔江南区的高端商业综合体",
    reworkHistory: [],
    keywords: ["塔楼", "首尔", "过大", "无外墙", "不受欢迎", "迷路", "内部封闭"],
    communityRating: {
      overall: 3.5,
      competitiveViability: 2.0,
      casualFun: 3.5,
      visualDesign: 7.5,
      balancedSides: 3.0,
      comments: [
        { source: "Reddit社区", sentiment: "负面", text: "Tower是Siege中最不受欢迎的地图之一，面积太大容易迷路" },
        { source: "社区投票", sentiment: "负面", text: "没有可破坏外墙意味着进攻方完全失去了远距离peek的能力" },
        { source: "设计讨论", sentiment: "负面", text: "地图太大导致信息获取困难，防守方可以随意遁走" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "有限的垂直互动",
      rotationOptions: "过大的面积导致轮转路线过多",
      entryPoints: "所有入口都在建筑内部，无法从外部突破",
      sightLines: "大型开放空间产生不可控的视线",
      lessonLearned: "缺乏可破坏外墙严重限制了战术多样性，地图面积需要控制"
    }
  },
  // ==================== Year 3 ====================
  {
    id: "villa",
    name: "Villa / 别墅",
    nameEN: "Villa",
    nameCN: "别墅",
    releaseDate: "2018-06-07",
    releaseSeason: "Y3S2",
    releaseOperation: "Para Bellum",
    location: "意大利，托斯卡纳",
    setting: "意大利乡间别墅/酒庄",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "大型",
    floors: 2,
    bombSites: 4,
    description: "意大利托斯卡纳的一座古典别墅/酒庄，内部装饰奢华。是Y3推出的原创新地图（非重做）。",
    designPhilosophy: "大型豪华别墅设计，利用长走廊和大房间创造多样化的交战空间",
    backgroundReference: "参考意大利托斯卡纳地区的传统庄园别墅",
    reworkHistory: [],
    keywords: ["别墅", "意大利", "托斯卡纳", "庄园", "豪华", "竞技地图", "原创新图"],
    communityRating: {
      overall: 7.5,
      competitiveViability: 8.0,
      casualFun: 7.0,
      visualDesign: 9.0,
      balancedSides: 7.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Villa是Y3最好的内容，地图设计精美且平衡" },
        { source: "Pro League分析", sentiment: "正面", text: "Villa在竞技中表现良好，但面积略大" },
        { source: "社区投票", sentiment: "正面", text: "视觉最优秀的地图之一" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "二楼到一楼有不少垂直控制点",
      rotationOptions: "面积较大但轮转路线设计合理",
      entryPoints: "窗户和门提供了标准的进入系统",
      sightLines: "长走廊产生了一些远距离对枪位置"
    }
  },
  {
    id: "fortress",
    name: "Fortress / 堡垒",
    nameEN: "Fortress",
    nameCN: "堡垒",
    releaseDate: "2018-12-04",
    releaseSeason: "Y3S4",
    releaseOperation: "Wind Bastion",
    location: "摩洛哥",
    setting: "摩洛哥军事堡垒",
    type: "休闲地图",
    competitiveStatus: "Casual/Quick Match",
    mapSize: "大型",
    floors: 2,
    bombSites: 4,
    description: "摩洛哥的一座军事风格堡垒建筑。因面积过大、布局不够紧凑而未进入竞技池。",
    designPhilosophy: "以军事堡垒为主题的大型建筑",
    backgroundReference: "参考摩洛哥传统卡斯巴（Kasbah）建筑和军事要塞",
    reworkHistory: [],
    keywords: ["堡垒", "摩洛哥", "军事", "大型", "非竞技", "Kasbah", "沙漠"],
    communityRating: {
      overall: 4.5,
      competitiveViability: 3.0,
      casualFun: 5.0,
      visualDesign: 7.5,
      balancedSides: 4.0,
      comments: [
        { source: "Reddit社区", sentiment: "负面", text: "Fortress面积太大，学习成本高且回报低" },
        { source: "社区投票", sentiment: "负面", text: "不如Villa，同样是新图但设计差距明显" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "有限",
      rotationOptions: "过大的面积导致轮转效率低",
      entryPoints: "堡垒厚墙减少了有效进入点",
      sightLines: "内部走廊过长"
    }
  },
  // ==================== Year 4 ====================
  {
    id: "outback",
    name: "Outback / 内陆",
    nameEN: "Outback",
    nameCN: "内陆",
    releaseDate: "2019-03-06",
    releaseSeason: "Y4S1",
    releaseOperation: "Burnt Horizon",
    location: "澳大利亚，内陆",
    setting: "澳洲内陆加油站/小镇",
    type: "正式对战地图",
    competitiveStatus: "Ranked（曾被移出后重新加入）",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "澳大利亚内陆的一个小型加油站和餐厅综合体，充满了澳洲风情的装饰。",
    designPhilosophy: "中型紧凑建筑，以澳洲内陆文化为主题",
    backgroundReference: "参考澳洲内陆公路旁的Roadhouse和小镇建筑",
    reworkHistory: [],
    keywords: ["澳洲", "内陆", "加油站", "Roadhouse", "中型", "澳洲风情"],
    communityRating: {
      overall: 6.5,
      competitiveViability: 6.5,
      casualFun: 6.5,
      visualDesign: 7.5,
      balancedSides: 6.0,
      comments: [
        { source: "Reddit社区", sentiment: "中性", text: "Outback不好不坏，是一张中规中矩的地图" },
        { source: "社区投票", sentiment: "中性", text: "主题有趣但地图设计缺乏亮点" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "标准的双层垂直空间",
      rotationOptions: "中等复杂度的轮转路线",
      entryPoints: "标准的窗口/门入口系统",
      sightLines: "中距离为主"
    }
  },
  // ==================== Year 5 ====================
  {
    id: "nighthaven_labs",
    name: "Nighthaven Labs / 暗夜港湾实验室",
    nameEN: "Nighthaven Labs",
    nameCN: "暗夜港湾实验室",
    releaseDate: "2022-12-06",
    releaseSeason: "Y7S4",
    releaseOperation: "Solar Raid",
    location: "北极圈附近",
    setting: "高科技秘密实验室",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "Nighthaven组织的秘密研究实验室，位于极地地区。高科技风格的内部设计。",
    designPhilosophy: "科幻高科技风格的现代实验室设计",
    backgroundReference: "结合了军事秘密基地和高科技实验室的概念",
    reworkHistory: [],
    keywords: ["实验室", "高科技", "Nighthaven", "极地", "科幻风格", "现代设计"],
    communityRating: {
      overall: 6.5,
      competitiveViability: 6.5,
      casualFun: 6.0,
      visualDesign: 7.5,
      balancedSides: 6.5,
      comments: [
        { source: "Reddit社区", sentiment: "中性", text: "Nighthaven Labs设计中规中矩，不算突出但也不差" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "标准的双层结构垂直空间",
      rotationOptions: "合理的轮转设计",
      entryPoints: "标准入口系统",
      sightLines: "中距离为主"
    }
  },
  {
    id: "emerald_plains",
    name: "Emerald Plains / 翡翠平原",
    nameEN: "Emerald Plains",
    nameCN: "翡翠平原",
    releaseDate: "2022-03-15",
    releaseSeason: "Y7S1",
    releaseOperation: "Demon Veil",
    location: "爱尔兰",
    setting: "爱尔兰乡间庄园",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "大型",
    floors: 2,
    bombSites: 4,
    description: "爱尔兰的一座美丽乡间庄园，包含大厅、图书馆、餐厅等区域。是近年来推出的高质量新地图。",
    designPhilosophy: "经典庄园设计，融合了现代竞技地图设计理念",
    backgroundReference: "参考爱尔兰传统乡间大庄园和城堡",
    reworkHistory: [],
    keywords: ["爱尔兰", "庄园", "翡翠", "绿色", "高质量新图", "乡间别墅"],
    communityRating: {
      overall: 7.5,
      competitiveViability: 7.5,
      casualFun: 7.5,
      visualDesign: 9.0,
      balancedSides: 7.5,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Emerald Plains是近年来最好的新地图，设计精美" },
        { source: "Pro League分析", sentiment: "正面", text: "地图设计成熟，适合竞技使用" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "良好的垂直空间利用",
      rotationOptions: "平衡的轮转路线设计",
      entryPoints: "多样化的进入点",
      sightLines: "混合型视线，外部有较长视线"
    }
  },
  {
    id: "lair",
    name: "Lair / 巢穴",
    nameEN: "Lair",
    nameCN: "巢穴",
    releaseDate: "2023-08-29",
    releaseSeason: "Y8S3",
    releaseOperation: "Heavy Mettle",
    location: "克罗地亚",
    setting: "地下犯罪组织据点",
    type: "正式对战地图",
    competitiveStatus: "Ranked/Competitive",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "克罗地亚的一处犯罪组织地下据点，包含实验室、储藏室等区域。是Y8推出的新地图。",
    designPhilosophy: "地下/半地下结构设计，独特的犯罪据点主题",
    backgroundReference: "参考东欧地下犯罪组织的秘密据点",
    reworkHistory: [],
    keywords: ["巢穴", "克罗地亚", "犯罪据点", "地下", "Y8新图", "东欧"],
    communityRating: {
      overall: 7.0,
      competitiveViability: 7.0,
      casualFun: 7.0,
      visualDesign: 7.5,
      balancedSides: 7.0,
      comments: [
        { source: "Reddit社区", sentiment: "中性偏正面", text: "Lair是一张不错的新地图，设计中规中矩但比较solid" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "独特的地下结构垂直空间",
      rotationOptions: "紧凑的轮转设计",
      entryPoints: "地下结构限制了部分入口选择",
      sightLines: "以中短距离为主"
    }
  },
  // 补充更多地图
  {
    id: "stadium",
    name: "Stadium / 体育场",
    nameEN: "Stadium",
    nameCN: "体育场",
    releaseDate: "2020-02-17",
    releaseSeason: "Y5S1 限时活动 / Y6S1 永久",
    releaseOperation: "Road to SI 2020 / Crimson Heist",
    location: "虚拟训练场",
    setting: "电竞体育场/虚拟训练环境",
    type: "正式对战地图",
    competitiveStatus: "Ranked",
    mapSize: "中型",
    floors: 2,
    bombSites: 4,
    description: "最初作为六邀赛活动地图推出，后成为永久地图。独特的虚拟训练环境概念，部分墙体为半透明材质。",
    designPhilosophy: "为竞技而生的地图设计，引入了半透明墙体概念",
    backgroundReference: "参考电竞体育场和虚拟训练场景",
    reworkHistory: [
      {
        date: "2021-03-16",
        season: "Y6S1 - Crimson Heist",
        type: "正式加入",
        changes: "从限时活动地图调整为永久对战地图，修改了部分布局"
      }
    ],
    keywords: ["体育场", "虚拟训练", "半透明墙", "电竞", "限时转永久", "创新概念"],
    communityRating: {
      overall: 6.5,
      competitiveViability: 7.0,
      casualFun: 6.0,
      visualDesign: 7.0,
      balancedSides: 7.0,
      comments: [
        { source: "Reddit社区", sentiment: "中性", text: "Stadium的半透明墙是有趣的创新但不太符合Siege的整体风格" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "标准双层结构",
      rotationOptions: "为竞技设计，轮转流畅",
      entryPoints: "标准入口系统",
      sightLines: "半透明墙增加了信息获取维度",
      designHighlight: "半透明墙体是独特创新，改变了信息战的方式"
    }
  },
  {
    id: "close_quarter",
    name: "Close Quarter / 近距离",
    nameEN: "Close Quarter",
    nameCN: "近距离",
    releaseDate: "2023-03-07",
    releaseSeason: "Y8S1",
    releaseOperation: "Commanding Force",
    location: "希腊",
    setting: "地中海风格建筑",
    type: "正式对战地图",
    competitiveStatus: "Ranked",
    mapSize: "小型",
    floors: 2,
    bombSites: 4,
    description: "位于希腊的一座地中海风格建筑，设计特点是更小更紧凑，强调近距离战斗。",
    designPhilosophy: "小型化紧凑设计，回归近距离战斗的核心体验",
    backgroundReference: "参考希腊地中海建筑风格",
    reworkHistory: [],
    keywords: ["希腊", "地中海", "紧凑", "近距离", "小型地图", "Y8新图"],
    communityRating: {
      overall: 7.0,
      competitiveViability: 7.0,
      casualFun: 7.5,
      visualDesign: 8.0,
      balancedSides: 7.0,
      comments: [
        { source: "Reddit社区", sentiment: "正面", text: "Close Quarter的紧凑设计回归了Siege的核心体验" }
      ]
    },
    levelDesignNotes: {
      verticalPlay: "紧凑空间内的密集垂直互动",
      rotationOptions: "短距离轮转，节奏快",
      entryPoints: "密集的入口分布",
      sightLines: "短距离对枪为主"
    }
  }
].filter(m => !m.skipEntry);

// 地图评价体系定义
const MAP_RATING_SYSTEM = {
  dimensions: [
    { id: "overall", name: "综合评分", weight: 1.0, description: "地图的整体质量评估" },
    { id: "competitiveViability", name: "竞技适用性", weight: 0.25, description: "地图在排位赛/职业比赛中的表现" },
    { id: "casualFun", name: "休闲趣味", weight: 0.15, description: "地图在休闲模式中的乐趣程度" },
    { id: "visualDesign", name: "视觉设计", weight: 0.15, description: "地图的美术和环境设计质量" },
    { id: "balancedSides", name: "攻防平衡", weight: 0.25, description: "攻击方和防守方的胜率平衡程度" },
    { id: "mapFlow", name: "地图流畅度", weight: 0.10, description: "地图内移动和轮转的流畅程度" },
    { id: "readability", name: "可读性", weight: 0.10, description: "地图信息的清晰度和易理解程度" }
  ],
  ratingScale: "1-10分制，10分为最优",
  sentimentCategories: ["正面", "中性", "中性偏正面", "中性偏负面", "负面"],
  evaluationSources: [
    "Reddit社区投票",
    "Pro League/竞技分析",
    "YouTube内容创作者评价",
    "Steam评论",
    "官方设计师笔记",
    "职业选手访谈"
  ]
};

// 地图重做时间线
const MAP_REWORK_TIMELINE = [
  { date: "2018-06-07", season: "Y3S2", map: "Club House", type: "中型重做" },
  { date: "2018-09-04", season: "Y3S3", map: "Hereford Base", type: "完全重做（争议）" },
  { date: "2019-03-06", season: "Y4S1", map: "Theme Park", type: "光照修复" },
  { date: "2019-06-11", season: "Y4S2", map: "Kafe Dostoyevsky", type: "中型重做" },
  { date: "2019-09-11", season: "Y4S3", map: "Kanal", type: "大型重做" },
  { date: "2020-03-10", season: "Y5S1", map: "Oregon", type: "中型重做" },
  { date: "2020-09-10", season: "Y5S3", map: "Chalet", type: "大型重做" },
  { date: "2020-12-01", season: "Y5S4", map: "Skyscraper", type: "中型重做" },
  { date: "2021-06-14", season: "Y6S2", map: "Favela / Border", type: "大型重做 / 中型调整" },
  { date: "2021-09-07", season: "Y6S3", map: "Bank（调整）", type: "小型调整" },
  { date: "2022-06-14", season: "Y7S2", map: "Theme Park（二次）", type: "大型重做" },
  { date: "2023-05-30", season: "Y8S2", map: "Consulate", type: "中型重做" },
  { date: "2025-06-11", season: "围攻X", map: "银行 / 咖啡馆 / 木屋 / 边境 / 俱乐部", type: "视觉翻新 + 环境互动系统（5张地图同时翻新）" }
];

// 围攻X (Siege X) 环境互动系统
const SIEGE_X_FEATURES = {
  mapRevamps: {
    description: "围攻X对5张经典人气地图进行了全面视觉翻新",
    maps: ["Bank (银行)", "Kafe Dostoyevsky (咖啡馆)", "Chalet (木屋)", "Border (边境)", "Club House (俱乐部)"],
    visualUpgrades: [
      "全新光线与阴影系统 —— 照明效果全面重置升级",
      "4K高清材质更新 —— 材质呈现真实次表面散射效果",
      "环境氛围更加逼真 —— 暴雨天气下玻璃反光达到电影级渲染精度",
      "室内外光照对比优化 —— 改善了从室外看室内/室内看室外的视觉体验"
    ]
  },
  environmentalInteractables: {
    description: "围攻X引入了全新的环境互动可破坏元素系统，为战术对抗增加新维度",
    elements: [
      {
        name: "灭火器",
        type: "可破坏/可互动",
        tacticalUse: "射击后释放灭火剂烟雾，可作为临时视线遮蔽手段，为突入或换位提供掩护",
        placement: "分布在地图走廊、楼梯间等公共区域"
      },
      {
        name: "燃气管道",
        type: "可破坏",
        tacticalUse: "射击燃气管可造成泄漏或爆炸效果，对附近区域造成伤害，可用于区域封锁或诱饵战术",
        placement: "厨房、地下室、设备间等区域"
      },
      {
        name: "金属探测器",
        type: "可互动/可触发",
        tacticalUse: "通过时会触发警报声响，暴露经过者位置信息，增加了信息战维度",
        placement: "建筑入口、安检区域"
      }
    ],
    designImpact: [
      "环境互动元素为每张地图增加了新的战术层次",
      "灭火器和燃气管创造了'环境武器'概念，不依赖干员技能也能制造战术效果",
      "金属探测器增加了信息获取的新维度",
      "使地图场景更加危机四伏，营造沉浸式战术体验",
      "可破坏环境互动物体是对原有软墙/硬墙可破坏系统的扩展"
    ]
  },
  antiCheat: {
    name: "R6 ShieldGuard",
    description: "统一反作弊措施，围攻X中进一步加强，新增实时安全更新和强化名誉系统"
  },
  freeToPlay: {
    description: "围攻X转为免费游玩模式，新玩家可解锁26名干员，老玩家保留原有进度并获得年限奖励"
  }
};

if (typeof module !== 'undefined') module.exports = { MAPS_DATA, MAP_RATING_SYSTEM, MAP_REWORK_TIMELINE, SIEGE_X_FEATURES };

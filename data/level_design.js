/**
 * Rainbow Six Siege - 关卡设计辅助信息模块
 * 专为关卡设计师整理的参考资料和分析框架
 */

const LEVEL_DESIGN_DATA = {
  // ==================== 关卡设计核心原则（从Siege中提炼）====================
  designPrinciples: [
    {
      id: "destructibility",
      name: "可破坏环境系统",
      description: "Siege的核心设计基石——环境可破坏性创造了动态战场。包含软墙、硬墙、天花板、地板、舱口等不同层级的可破坏元素。",
      designGuidelines: [
        "软墙与硬墙的比例直接影响地图平衡（Favela的教训：软墙过多导致防守崩溃）",
        "垂直可破坏面（天花板/地板）创造Z轴战斗维度",
        "可破坏性需要与进入点系统协同设计",
        "加固系统（Reinforce）为防守方提供了有限的硬化资源，创造选择博弈"
      ],
      caseStudies: [
        { map: "Bank", lesson: "天花板可破坏性创造了经典的垂直进攻策略" },
        { map: "Favela", lesson: "过多软墙导致防守方几乎无法守住任何位置" },
        { map: "Grand Larceny活动", lesson: "全可破坏地板展示了极端垂直战斗的可能性" }
      ]
    },
    {
      id: "entry_systems",
      name: "进入点系统",
      description: "进攻方进入建筑的方式和路径设计。窗户、门、天窗、可破坏墙面都构成进入系统的一部分。",
      designGuidelines: [
        "进入点数量直接影响攻防平衡（Bartlett University教训：进入点不足）",
        "进入点应当分布在建筑多个方向，避免单一方向集中",
        "每个进入点应有对应的防守反制位",
        "进入点之间应有足够间距避免过于密集"
      ],
      caseStudies: [
        { map: "Bartlett University", lesson: "窗户数量不足导致进攻方无法安全进入" },
        { map: "Tower", lesson: "缺乏可破坏外墙等于移除了远距离peek进入方式" },
        { map: "Coastline", lesson: "阳台+窗户+门的多元进入系统是成功范例" }
      ]
    },
    {
      id: "vertical_play",
      name: "垂直对抗设计",
      description: "利用楼层之间的关系创造Z轴战斗空间。这是Siege区别于其他FPS的关键特征。",
      designGuidelines: [
        "每个炸弹点位应有可被垂直进攻的区域",
        "垂直对抗需要在上下层都提供安全的操作空间",
        "楼梯和舱口的位置影响垂直控制的优先级",
        "避免设计过多层数（Hereford四层的教训）"
      ],
      caseStudies: [
        { map: "Club House", lesson: "教堂天花板是经典的垂直进攻教学案例" },
        { map: "Hereford Base", lesson: "四层结构过于冗长，轮转成本太高" },
        { map: "Oregon", lesson: "大塔区域的垂直空间设计堪称典范" }
      ]
    },
    {
      id: "rotation_flow",
      name: "轮转路线设计",
      description: "防守方在不同区域间移动（轮转）的路线系统。轮转路线影响防守方的灵活性和策略多样性。",
      designGuidelines: [
        "轮转路线应当在安全性和效率之间取得平衡",
        "关键轮转路线可以通过可破坏墙创造（创造开墙战术的基础）",
        "避免设计死胡同或单一出口的区域",
        "轮转路线应能被进攻方通过控制关键区域来切断"
      ],
      caseStudies: [
        { map: "Border", lesson: "紧凑的轮转设计让防守方可以快速响应进攻" },
        { map: "Villa", lesson: "面积较大但轮转路线设计合理维持了节奏" }
      ]
    },
    {
      id: "sight_lines",
      name: "视线设计",
      description: "地图中的视线长度和方向影响交战距离和武器选择。",
      designGuidelines: [
        "长视线区域应当有掩体和转角提供战术选择",
        "避免设计不可避免的长视线（如直通走廊无掩体）",
        "室外到室内的视线是重要的peek机会",
        "视线设计应鼓励多种交战距离"
      ],
      caseStudies: [
        { map: "Plane", lesson: "狭长走廊产生的无法避免的长视线限制了战术多样性" },
        { map: "Coastline", lesson: "混合型视线设计鼓励不同武器和战术的使用" }
      ]
    },
    {
      id: "map_size",
      name: "地图尺寸控制",
      description: "地图面积和复杂度需要与游戏节奏、回合时间和玩家数量匹配。",
      designGuidelines: [
        "5v5模式中，地图面积不宜过大（Tower、Fortress的教训）",
        "中型地图是竞技最佳选择（Border、Coastline水平）",
        "小型地图适合休闲但不适合竞技（House）",
        "层数控制在2-3层为佳，避免4层及以上"
      ],
      sizeClassification: {
        small: { examples: ["House", "Plane"], sqm: "约1000-1500㎡", floors: "2层", note: "快节奏但不适合竞技" },
        medium: { examples: ["Border", "Coastline", "Oregon"], sqm: "约1500-2500㎡", floors: "2-3层", note: "竞技最佳尺寸" },
        large: { examples: ["Bank", "Villa", "Club House"], sqm: "约2500-3500㎡", floors: "2-3层+地下室", note: "适合竞技但需要更精密的设计" },
        oversized: { examples: ["Tower", "Fortress"], sqm: "超过3500㎡", floors: "2层但面积过大", note: "不适合竞技" }
      }
    },
    {
      id: "bomb_site_design",
      name: "炸弹点位设计",
      description: "Bomb模式中每张地图有4个炸弹点位对（A/B），点位设计是地图设计的核心。",
      designGuidelines: [
        "每个点位应有至少2-3种可行的进攻策略",
        "防守方应能通过加固、工事和干员技能构建有效防线",
        "A/B两个炸弹点之间的距离影响防守策略（太近容易被一起突破，太远难以协防）",
        "点位应有垂直进攻/防守的可能性",
        "最好的地图至少有3个竞技可用的点位"
      ]
    },
    {
      id: "information_warfare",
      name: "信息战设计",
      description: "摄像头、无人机、窗户、角度等信息获取手段的布局影响地图的信息战维度。",
      designGuidelines: [
        "默认摄像头位置应当覆盖关键通道但不过于强势",
        "无人机通道（地面通风口等）的设计影响攻击方的侦察能力",
        "窗口/洞口的角度影响双方的信息获取",
        "信息获取的不对称性是创造策略博弈的关键"
      ]
    }
  ],

  // ==================== 地图设计成功/失败案例分析 ====================
  designCaseStudies: {
    successCases: [
      {
        map: "Coastline",
        title: "最成功的地图设计",
        reasons: [
          "中央庭院创造了攻守双方都需争夺的核心区域",
          "环形布局提供了灵活的进攻和轮转选择",
          "屋顶进攻提供了独特的垂直维度",
          "视觉辨识度高，不同区域主题分明",
          "从未需要重做，说明初始设计质量高"
        ],
        designTakeaway: "中央争夺区域+环形布局是5v5战术射击地图的优秀模板"
      },
      {
        map: "Oregon",
        title: "经典竞技地图",
        reasons: [
          "L形布局紧凑但不拥挤",
          "大塔/小塔的双翼设计创造了清晰的进攻方向选择",
          "地下室争夺是独立的战术层面",
          "重做保持了核心布局同时改善了薄弱区域"
        ],
        designTakeaway: "L形/分翼布局适合创造多方向进攻选择"
      },
      {
        map: "Club House",
        title: "垂直对抗典范",
        reasons: [
          "教堂区域的垂直打法成为Siege标志性战术",
          "地下室和一楼的关系设计精妙",
          "重做方向正确，保留核心改善细节"
        ],
        designTakeaway: "精心设计的垂直关系可以成为地图的招牌特色"
      },
      {
        map: "Kafe Dostoyevsky (重做后)",
        title: "成功的地图重做案例",
        reasons: [
          "保留了地图核心结构和灵魂",
          "改善了三楼的平衡问题",
          "增加的通道和房间提供了新的策略选择",
          "视觉风格保持一致"
        ],
        designTakeaway: "地图重做应当保留核心灵魂，针对性改善薄弱区域"
      }
    ],
    failureCases: [
      {
        map: "Bartlett University",
        title: "PvE转PvP的失败",
        reasons: [
          "最初为PvE设计，窗户和进入点数量不满足PvP需求",
          "进攻方几乎无法安全进入建筑",
          "说明PvE和PvP地图设计有本质区别"
        ],
        designTakeaway: "PvE和PvP地图设计需求不同，不能简单转换"
      },
      {
        map: "Hereford Base (重做后)",
        title: "最失败的地图重做",
        reasons: [
          "完全推翻原版设计，失去了地图灵魂",
          "四层结构过于冗长，轮转成本太高",
          "复杂度远超必要水平",
          "社区几乎一致给出负面评价"
        ],
        designTakeaway: "更多≠更好，地图重做不应完全颠覆原有设计"
      },
      {
        map: "Tower",
        title: "过大且封闭的设计",
        reasons: [
          "面积过大导致信息获取困难",
          "缺乏可破坏外墙移除了重要战术维度",
          "内部全封闭设计让防守方过于自由"
        ],
        designTakeaway: "可破坏外墙和适当面积是战术射击地图的基本要求"
      },
      {
        map: "Favela",
        title: "极端可破坏性的失败",
        reasons: [
          "几乎所有外墙都是软墙",
          "防守方无法建立有效防线",
          "加固资源完全不够用",
          "即使重做也无法完全修复根本问题"
        ],
        designTakeaway: "可破坏性需要在进攻机会和防守稳定性之间取得平衡"
      }
    ]
  },

  // ==================== 关卡设计参考资源 ====================
  designResources: {
    gdcTalks: [
      {
        title: "Level Design in a Day: Siege Level Design",
        speaker: "Ubisoft Montreal Team",
        year: "2017",
        topic: "Siege地图设计的核心理念和流程",
        searchKeywords: "GDC Rainbow Six Siege level design Ubisoft"
      },
      {
        title: "The Art of Siege: Destruction-Based Level Design",
        speaker: "Ubisoft Montreal",
        year: "2018",
        topic: "可破坏环境如何影响关卡设计",
        searchKeywords: "GDC Siege destruction level design"
      }
    ],
    youtubeChannels: [
      { name: "Get_Flanked", focus: "地图策略、点位分析、meta讨论", url: "youtube.com/c/GetFlanked" },
      { name: "Gregor", focus: "深度策略分析、地图控制", url: "youtube.com/c/Gregor" },
      { name: "Braction", focus: "地图攻略、位置指南", url: "youtube.com/c/Braction" },
      { name: "KaoS", focus: "高水平对战、地图利用", url: "youtube.com/c/KaoS" },
      { name: "Coconut Brah", focus: "高级技巧、peek位置、地图tricks", url: "youtube.com/c/CoconutBrah" },
      { name: "Varsity Gaming", focus: "新手到高手的地图教学", url: "youtube.com/c/VarsityGaming" }
    ],
    bilibiliChannels: [
      { name: "彩六相关UP主", focus: "中文彩六教学和分析", searchKeywords: "B站 彩虹六号 地图攻略 关卡分析" }
    ],
    competitiveResources: [
      { name: "SiegeGG", url: "siegegg.com", description: "职业比赛数据分析，包含地图选取率、胜率等数据" },
      { name: "R6 Analyst", url: "analyst.r6s.com", description: "深度数据分析平台" },
      { name: "Ubisoft Designer's Notes", url: "ubisoft.com/siege/news-updates", description: "官方设计师笔记，说明平衡调整原因" }
    ],
    bookReferences: [
      { title: "Level Design: Concept, Theory, and Practice", author: "Rudolf Kremers", relevance: "通用关卡设计理论" },
      { title: "An Architectural Approach to Level Design", author: "Christopher W. Totten", relevance: "建筑学视角的关卡设计" },
      { title: "Game Level Design", author: "Ed Byrne", relevance: "游戏关卡设计实践" }
    ]
  },

  // ==================== 你可能还需要收集的额外信息 ====================
  additionalInfoSuggestions: [
    {
      category: "干员与地图互动",
      description: "每个干员在不同地图上的表现和选取率",
      importance: "高",
      reason: "干员能力直接影响地图体验，是关卡设计必须考虑的因素"
    },
    {
      category: "专业术语词汇表",
      description: "Siege社区特有的关卡相关术语",
      importance: "高",
      reason: "便于与团队和社区沟通",
      examples: ["Rotate（轮转）", "Pixel Peek（像素级窥视）", "Soft/Hard Breach（软/硬突破）", 
                 "Vertical Play（垂直打法）", "Roam（游走）", "Anchor（锚点防守）",
                 "Default Camera（默认摄像头）", "Hatch（舱口）", "Bandit Trick（Bandit电池技巧）"]
    },
    {
      category: "热力图数据",
      description: "玩家在各地图上的击杀/死亡热力图",
      importance: "中高",
      reason: "揭示地图中的实际交战热点区域"
    },
    {
      category: "职业比赛地图数据",
      description: "各地图在职业比赛中的选取率、ban率、攻防胜率",
      importance: "高",
      reason: "反映地图在最高水平竞技中的表现",
      source: "SiegeGG.com"
    },
    {
      category: "玩家动线分析",
      description: "攻击方和防守方在各地图上的典型移动路线",
      importance: "中高",
      reason: "理解玩家如何实际使用地图空间"
    },
    {
      category: "地图俯视图/平面图",
      description: "各地图的详细俯视图，标注房间名称和关键位置",
      importance: "高",
      reason: "关卡设计分析的基础参考材料",
      source: "R6Maps.com（社区制作的互动地图工具）"
    },
    {
      category: "季度更新的微调记录",
      description: "每个赛季的小型地图调整（非大型重做）",
      importance: "中",
      reason: "了解游戏团队如何通过微调持续优化地图"
    },
    {
      category: "竞技对手分析",
      description: "Valorant、CS2等竞品的地图设计对比分析",
      importance: "中",
      reason: "了解战术射击品类中不同的地图设计理念",
      competitors: [
        { game: "CS2", mapDesignFeature: "纯粹的几何空间设计，无可破坏环境" },
        { game: "Valorant", mapDesignFeature: "结合技能的地图设计，有视线阻挡物系统" },
        { game: "XDefiant", mapDesignFeature: "更偏向快节奏arcade风格的地图" }
      ]
    },
    {
      category: "音频设计与地图关系",
      description: "Siege的声音系统如何影响地图体验",
      importance: "中",
      reason: "声音传播与地图结构直接相关，影响信息战",
      examples: ["Yacht的环境噪音问题", "垂直声音传播的问题", "不同材质地面的脚步声差异"]
    },
    {
      category: "光照设计",
      description: "室内外光差、窗口光照方向对gameplay的影响",
      importance: "中",
      reason: "光照影响可见性和视觉舒适度",
      examples: ["Theme Park原版过暗的问题", "从室外看室内vs室内看室外的不对称性"]
    }
  ],

  // ==================== Siege关卡设计术语词汇表 ====================
  glossary: [
    { term: "Soft Wall / 软墙", definition: "可以被任何武器穿透和破坏的墙壁" },
    { term: "Hard Wall / 硬墙", definition: "只能被特定干员能力（Hard Breach）破坏的加固墙壁" },
    { term: "Reinforce / 加固", definition: "防守方用钢板加固软墙使其成为硬墙的动作" },
    { term: "Breach / 突破", definition: "攻击方破坏墙壁/地板创造新通道或视线的动作" },
    { term: "Hard Breach / 硬突破", definition: "使用Thermite、Hibana、Ace等干员的能力破坏加固墙" },
    { term: "Soft Breach / 软突破", definition: "使用炸药、Sledge等破坏未加固的墙壁和地板" },
    { term: "Rotate / 轮转", definition: "在墙壁上开洞创造新的移动通道" },
    { term: "Rotate Hole / 轮转孔", definition: "防守方在两个房间之间的软墙上开的通行洞" },
    { term: "Murder Hole / 杀人洞", definition: "在墙壁或地板上开的小洞用于观察或射击" },
    { term: "Pixel Peek / 像素窥视", definition: "利用极小的缝隙或角度进行侦察或射击" },
    { term: "Vertical Play / 垂直打法", definition: "利用楼层间的可破坏面进行上下层的对抗" },
    { term: "Roam / 游走", definition: "防守方离开点位在地图其他区域巡逻干扰攻击方" },
    { term: "Anchor / 锚点", definition: "防守方坚守在炸弹点位附近的防守策略" },
    { term: "Flank / 侧翼", definition: "从敌人侧面或背后发起攻击" },
    { term: "Spawn Peek / 出生点窥视", definition: "防守方在行动阶段开始时通过窗户射击正在接近的攻击方" },
    { term: "Run Out / 跑出", definition: "防守方短暂离开建筑到室外攻击敌人" },
    { term: "Default Plant / 默认下包位", definition: "各点位上最常见的拆弹器放置位置" },
    { term: "Site Setup / 点位布置", definition: "防守方在准备阶段对炸弹点位的加固和布置工作" },
    { term: "Map Control / 地图控制", definition: "进攻方逐步清理和控制建筑区域的过程" },
    { term: "Hatch / 舱口", definition: "楼层间的可开启/破坏的通道" },
    { term: "Rappel / 绳降", definition: "攻击方使用绳索在建筑外墙上移动和从窗户进入" },
    { term: "Barricade / 路障", definition: "用于封锁门窗的木板障碍" },
    { term: "Castle Barricade / Castle路障", definition: "Castle干员的特殊加固路障，更难破坏" },
    { term: "Drone Hole / 无人机通道", definition: "地面上供小型无人机通过的小洞" },
    { term: "Objective / 目标", definition: "炸弹、人质或区域等需要攻防的目标" },
    { term: "Off-site / 点外", definition: "炸弹点位旁边用于扩展防守范围的区域" }
  ]
};

if (typeof module !== 'undefined') module.exports = { LEVEL_DESIGN_DATA };

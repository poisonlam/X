/**
 * Rainbow Six Siege - 完整玩法模式数据库
 * 包含所有常驻模式、限时活动和特殊玩法
 */

const GAME_MODES_DATA = {
  // ==================== 核心常驻模式 ====================
  coreModes: [
    {
      id: "bomb",
      name: "炸弹 / Bomb",
      nameEN: "Bomb",
      nameCN: "炸弹",
      type: "核心对抗",
      category: "攻防对抗",
      status: "常驻",
      playerCount: "5v5",
      roundBased: true,
      maxRounds: "最多9局（先赢5局，加时赛制）",
      releaseDate: "2015-12-01",
      description: "Siege的核心玩法模式。攻击方需要在两个炸弹点中选择一个放置拆弹器（Defuser），防守方需要阻止或摧毁拆弹器。这是竞技和职业比赛的唯一模式。",
      mechanicBreakdown: {
        preparation: "45秒准备阶段——防守方设置防御工事、布置装备；攻击方用无人机侦察",
        action: "3分钟行动阶段——攻击方突入建筑尝试放置拆弹器",
        winConditions: {
          attacker: ["成功放置拆弹器并保护至引爆", "消灭所有防守方"],
          defender: ["消灭所有攻击方", "阻止放置拆弹器直到时间耗尽", "摧毁已放置的拆弹器"]
        },
        keyMechanics: ["可破坏环境", "干员技能体系", "无人机侦察系统", "加固系统", "禁选ban系统"]
      },
      gameplayType: "战术射击+策略博弈",
      archetypeReference: "搜索与摧毁（S&D）模式的进化版，参考CS系列的拆弹模式，但加入了环境破坏和干员系统",
      similarGames: ["CS:GO/CS2 Defuse模式", "Valorant 爆破模式", "CrossFire 爆破模式"],
      uniqueElements: ["可破坏环境改变战场", "干员独特技能", "摄像头/无人机信息系统", "准备阶段的战术布置"],
      competitiveStatus: "职业比赛唯一使用模式",
      communityRating: {
        overall: 9.5,
        depth: 10,
        accessibility: 6.0,
        replayability: 9.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Bomb是Siege的灵魂，无可替代的核心体验" },
          { source: "Pro Scene", sentiment: "正面", text: "平衡性最好的模式，职业赛唯一选择" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "Rainbow Six Siege: How to Play Bomb Mode - Beginner's Guide", type: "教学", url: "搜索关键词: R6 Siege bomb mode guide beginner" },
        { platform: "YouTube", title: "Pro League Strategies - Bomb Site Executions", type: "职业分析", url: "搜索关键词: R6 pro league bomb site execute" },
        { platform: "B站", title: "彩虹六号炸弹模式新手入门教学", type: "教学", url: "搜索关键词: 彩虹六号 炸弹模式 新手教学" }
      ]
    },
    {
      id: "secure_area",
      name: "守护区域 / Secure Area",
      nameEN: "Secure Area",
      nameCN: "守护区域",
      type: "核心对抗",
      category: "攻防对抗",
      status: "常驻（仅Quick Match）",
      playerCount: "5v5",
      roundBased: true,
      maxRounds: "先赢4局",
      releaseDate: "2015-12-01",
      description: "攻击方需要进入并占领指定区域，防守方需要保护该区域。当攻击方在区域内且没有防守方争夺时开始占领计时。",
      mechanicBreakdown: {
        preparation: "45秒准备阶段",
        action: "3分钟行动阶段",
        winConditions: {
          attacker: ["占领目标区域（持续站在区域内至计时结束）", "消灭所有防守方"],
          defender: ["消灭所有攻击方", "时间耗尽时保持区域不被占领", "区域争夺（有防守方在区域内时占领暂停）"]
        },
        keyMechanics: ["区域争夺机制", "容错率较高", "鼓励近距离战斗"]
      },
      gameplayType: "区域控制",
      archetypeReference: "传统的控制点/占点模式，类似于经典FPS中的Domination单点变体",
      similarGames: ["使命召唤 Domination", "战地系列 征服模式（简化版）", "Valorant Spike Rush（部分概念）"],
      uniqueElements: ["与Siege环境破坏系统结合", "争夺机制（attacker进入+defender在场=僵持）"],
      competitiveStatus: "已从Ranked移除，仅保留在Quick Match",
      communityRating: {
        overall: 6.5,
        depth: 5.0,
        accessibility: 8.0,
        replayability: 6.0,
        comments: [
          { source: "Reddit", sentiment: "中性", text: "Secure Area适合新手但策略深度不够" },
          { source: "社区", sentiment: "中性", text: "从Ranked移除是正确的决定，但作为休闲模式还不错" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Secure Area Tips", type: "教学", url: "搜索关键词: R6 Siege secure area tips guide" },
        { platform: "B站", title: "彩虹六号守护区域模式介绍", type: "介绍", url: "搜索关键词: 彩虹六号 守护区域" }
      ]
    },
    {
      id: "hostage",
      name: "人质 / Hostage",
      nameEN: "Hostage",
      nameCN: "人质",
      type: "核心对抗",
      category: "攻防对抗",
      status: "常驻（仅Quick Match）",
      playerCount: "5v5",
      roundBased: true,
      maxRounds: "先赢4局",
      releaseDate: "2015-12-01",
      description: "攻击方需要找到并解救人质，将人质带到指定提取点。防守方需要保护人质不被带走。注意：误伤人质会判负。",
      mechanicBreakdown: {
        preparation: "45秒准备阶段",
        action: "3分钟行动阶段",
        winConditions: {
          attacker: ["将人质带到提取点", "消灭所有防守方（人质存活）"],
          defender: ["消灭所有攻击方", "时间耗尽", "攻击方误杀人质"]
        },
        keyMechanics: ["人质可被误伤（双方都可能）", "人质可被DBNO", "需要护送机制", "Fuze的终极天敌模式"]
      },
      gameplayType: "VIP护送/解救",
      archetypeReference: "经典的人质解救模式，源自《彩虹六号》系列核心概念",
      similarGames: ["CS系列 人质模式（cs_maps）", "SWAT系列的人质解救任务", "经典R6系列的核心玩法"],
      uniqueElements: ["人质可以被任何一方误伤", "护送路线选择的策略性", "Fuze的集束炸弹与人质的经典矛盾"],
      competitiveStatus: "已从Ranked移除，仅保留在Quick Match",
      communityRating: {
        overall: 5.5,
        depth: 5.0,
        accessibility: 7.0,
        replayability: 5.0,
        comments: [
          { source: "Reddit", sentiment: "中性偏负面", text: "Hostage模式的存在主要是为了Fuze的meme梗" },
          { source: "社区", sentiment: "中性", text: "人质误杀机制让很多玩家头疼，但增加了一层风险管理" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Hostage Mode Guide", type: "教学", url: "搜索关键词: R6 Siege hostage mode guide" },
        { platform: "YouTube", title: "Fuze vs Hostage Compilation", type: "娱乐", url: "搜索关键词: Fuze hostage kill compilation" },
        { platform: "B站", title: "彩虹六号人质模式搞笑集锦", type: "娱乐", url: "搜索关键词: 彩虹六号 人质 Fuze" }
      ]
    },
    {
      id: "team_deathmatch",
      name: "团队死斗 / Team Deathmatch",
      nameEN: "Team Deathmatch",
      nameCN: "团队死斗",
      type: "对抗模式",
      category: "击杀竞赛",
      status: "常驻",
      playerCount: "5v5",
      roundBased: false,
      maxRounds: "N/A",
      releaseDate: "2022-03-15",
      releaseOperation: "Y7S1 - Demon Veil",
      description: "Y7S1新增的常驻模式。纯击杀竞赛，先达到指定击杀数的队伍获胜。无攻防概念，无目标点位，提供快节奏的战斗体验。",
      mechanicBreakdown: {
        preparation: "无准备阶段",
        action: "持续战斗直到达到击杀上限或时间结束",
        winConditions: {
          team: ["先达到75杀的队伍获胜", "时间结束时击杀数更多的队伍获胜"]
        },
        keyMechanics: ["重生机制", "随机重生点", "无加固/破坏机制", "武器随干员选择"]
      },
      gameplayType: "快节奏团队击杀竞赛",
      archetypeReference: "经典的TDM模式，几乎所有FPS游戏的标配",
      similarGames: ["使命召唤 TDM", "战地系列 TDM", "CS2 Deathmatch", "任何FPS的TDM模式"],
      uniqueElements: ["保留了Siege的干员系统和武器手感", "部分地图专门为TDM调整", "用于热身和练枪"],
      competitiveStatus: "非竞技模式",
      communityRating: {
        overall: 6.0,
        depth: 3.0,
        accessibility: 9.0,
        replayability: 6.0,
        comments: [
          { source: "Reddit", sentiment: "中性", text: "TDM是不错的热身模式，但不是Siege的核心体验" },
          { source: "社区", sentiment: "正面", text: "终于有了一个可以轻松练枪的模式" },
          { source: "Reddit", sentiment: "中性偏负面", text: "重生点设计有时不太好，可能刷在敌人身边" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Team Deathmatch First Look", type: "体验", url: "搜索关键词: R6 Siege TDM team deathmatch gameplay" },
        { platform: "B站", title: "彩虹六号TDM模式体验", type: "体验", url: "搜索关键词: 彩虹六号 死斗模式 TDM" }
      ]
    },
    {
      id: "ranked",
      name: "排位赛 / Ranked",
      nameEN: "Ranked",
      nameCN: "排位赛",
      type: "竞技系统",
      category: "排名竞技",
      status: "常驻",
      playerCount: "5v5",
      roundBased: true,
      releaseDate: "2015-12-01",
      description: "Siege的竞技排位系统，使用Bomb模式，有Ban/Pick系统。玩家通过胜负获得或失去排名积分，从铜牌到冠军的完整排名体系。",
      mechanicBreakdown: {
        banPick: "每队可以Ban 1名干员（后改为2名），影响双方策略",
        mapPool: "使用竞技地图池（约7-9张地图）",
        rankSystem: "铜→银→金→白金→钻石→冠军"
      },
      gameplayType: "排名竞技系统",
      archetypeReference: "标准的ELO/MMR竞技排名系统",
      similarGames: ["CS2 竞技模式", "Valorant 竞技模式", "Overwatch 竞技模式"],
      communityRating: {
        overall: 7.5,
        comments: [
          { source: "Reddit", sentiment: "中性", text: "Ranked是Siege的核心体验，但有时排位环境不好" }
        ]
      }
    },
    {
      id: "unranked",
      name: "非排位 / Unranked",
      nameEN: "Unranked",
      nameCN: "非排位",
      type: "竞技系统",
      category: "对抗",
      status: "常驻",
      playerCount: "5v5",
      roundBased: true,
      releaseDate: "2019-09-11",
      releaseOperation: "Y4S3 - Ember Rise",
      description: "与排位赛规则完全相同但不影响排名的模式。适合练习竞技打法但不想承担排名波动的玩家。",
      gameplayType: "竞技练习",
      archetypeReference: "无压力竞技模式",
      similarGames: ["CS2 Premier（非排名版）", "Valorant 非竞技模式"],
      communityRating: {
        overall: 7.0,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Unranked填补了Casual和Ranked之间的空白" }
        ]
      }
    },
    {
      id: "quick_match",
      name: "快速对战 / Quick Match",
      nameEN: "Quick Match",
      nameCN: "快速对战",
      type: "休闲模式",
      category: "对抗",
      status: "常驻",
      playerCount: "5v5",
      roundBased: true,
      releaseDate: "2015-12-01",
      description: "原名Casual，后改名Quick Match。规则简化版的对战模式，使用所有地图和三种模式（炸弹、人质、守护区域），准备时间更短。",
      gameplayType: "休闲对抗",
      archetypeReference: "标准休闲模式",
      communityRating: {
        overall: 7.0,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Quick Match适合放松和尝试新干员" }
        ]
      }
    },
    {
      id: "newcomer",
      name: "新手模式 / Newcomer",
      nameEN: "Newcomer",
      nameCN: "新手模式",
      type: "教学模式",
      category: "新手引导",
      status: "常驻",
      playerCount: "5v5",
      roundBased: true,
      releaseDate: "2019-06-11",
      releaseOperation: "Y4S2 - Phantom Sight",
      description: "专为新手设计的模式，仅使用少量简单地图和基础干员，帮助新玩家学习游戏基础。50级以下的玩家可以参与。",
      gameplayType: "新手引导",
      archetypeReference: "新手保护/分流系统",
      communityRating: {
        overall: 5.5,
        comments: [
          { source: "Reddit", sentiment: "中性偏负面", text: "Newcomer模式经常被老玩家开小号虐新人" }
        ]
      }
    },
    {
      id: "training_grounds",
      name: "训练场 / Training Grounds",
      nameEN: "Training Grounds",
      nameCN: "训练场",
      type: "PvE模式",
      category: "训练/PvE",
      status: "常驻",
      playerCount: "1-5人合作",
      roundBased: false,
      releaseDate: "2015-12-01",
      description: "原名Terrorist Hunt/恐怖猎人，后更名为Training Grounds。玩家与AI敌人对抗，包含消灭恐怖分子、保护人质、拆弹等子模式。",
      mechanicBreakdown: {
        subModes: ["消灭恐怖分子（全灭AI）", "拆弹", "保护人质", "消灭经典（限时波次）"],
        difficulty: ["普通", "困难", "真实"]
      },
      gameplayType: "PvE合作射击",
      archetypeReference: "经典的合作反恐PvE模式，源自R6系列传统",
      similarGames: ["CS系列 Bot对战", "使命召唤 特种作战", "SWAT系列"],
      uniqueElements: ["保留了Siege全部地图和干员", "可用于练习地图和角色", "支持单人或多人合作"],
      communityRating: {
        overall: 5.0,
        comments: [
          { source: "Reddit", sentiment: "中性偏负面", text: "AI太弱了，主要用来练枪和热身" }
        ]
      }
    }
  ],

  // ==================== 限时活动/特殊模式 ====================
  limitedTimeEvents: [
    {
      id: "outbreak",
      name: "疫变 / Outbreak",
      nameEN: "Outbreak",
      nameCN: "疫变",
      type: "限时PvE活动",
      category: "PvE合作生存",
      status: "已结束",
      playerCount: "3人合作",
      season: "Y3S1 - Operation Chimera",
      dateRange: "2018年3月6日 - 2018年4月3日",
      duration: "约4周",
      description: "Siege历史上规模最大的限时活动。三名玩家合作对抗外星寄生虫感染的变异体。包含三个独立任务：Junkyard（废车场）、Hospital（医院）、Resort（度假村）。后来演变为独立游戏《Rainbow Six Extraction》。",
      mechanicBreakdown: {
        missions: [
          { name: "Junkyard / 废车场", objective: "摧毁外星树" },
          { name: "Hospital / 医院", objective: "护送资产" },
          { name: "Resort / 度假村", objective: "解救幸存者" }
        ],
        enemies: ["Grunts（步兵）", "Breachers（爆破者）", "Rooters（缠绕者）", "Smashers（粉碎者）", "Apex（顶点boss）"],
        availableOperators: ["Lion", "Finka", "Ash", "Doc", "Smoke", "Glaz", "Kapkan", "Tachanka", "Buck", "Ying", "Recruit"],
        keyMechanics: ["PvE三人合作", "限定干员池", "特殊敌人类型", "独立任务地图"]
      },
      gameplayType: "PvE合作射击/生存",
      archetypeReference: "Left 4 Dead风格的合作PvE模式",
      similarGames: ["Left 4 Dead 1/2", "Back 4 Blood", "World War Z", "Killing Floor 2"],
      uniqueElements: ["Siege引擎下的PvE体验", "外星生物敌人", "独立故事线", "后来发展为独立游戏Extraction"],
      communityRating: {
        overall: 8.0,
        novelty: 9.0,
        depth: 6.0,
        replayability: 5.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Outbreak是Siege最令人印象深刻的限时活动，完全不同的体验" },
          { source: "YouTube评论", sentiment: "正面", text: "希望Outbreak能回归，比Extraction好玩多了" },
          { source: "社区", sentiment: "中性偏正面", text: "概念很棒但内容量不够多，三个任务玩几次就腻了" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "Rainbow Six Siege Outbreak Full Gameplay", type: "完整流程", url: "搜索关键词: R6 Siege Outbreak full gameplay all missions" },
        { platform: "YouTube", title: "Outbreak All Cutscenes & Story", type: "剧情", url: "搜索关键词: R6 Siege Outbreak cutscenes story" },
        { platform: "B站", title: "彩虹六号异变/疫变活动全流程", type: "流程", url: "搜索关键词: 彩虹六号 Outbreak 疫变" }
      ]
    },
    {
      id: "rainbow_is_magic",
      name: "彩虹即魔法 / Rainbow is Magic",
      nameEN: "Rainbow is Magic",
      nameCN: "彩虹即魔法",
      type: "限时活动",
      category: "PvE/趣味",
      status: "已结束（多次复刻）",
      playerCount: "5人合作",
      season: "Y4S1（首次）",
      dateRange: "2019年4月1日起（愚人节活动）",
      duration: "约2周",
      description: "愚人节特别活动。将人质模式重新包装为粉色独角兽主题，Plane地图被改为彩色泡泡风格，人质变成了巨型泰迪熊。",
      mechanicBreakdown: {
        base: "人质模式变体",
        changes: ["粉色/彩虹视觉主题", "人质替换为泰迪熊", "特殊音效和视效", "仅限4名干员"],
        availableOperators: ["Tachanka", "Montagne", "Ash", "Fuze（讽刺设定）"]
      },
      gameplayType: "趣味改装模式",
      archetypeReference: "愚人节/节日特别活动模式",
      similarGames: ["守望先锋 万圣节/春节活动", "Fortnite 节日活动"],
      uniqueElements: ["完全颠覆Siege严肃风格", "独角兽主题的视觉改造", "巨型泰迪熊人质"],
      communityRating: {
        overall: 8.5,
        novelty: 10,
        depth: 3.0,
        replayability: 4.0,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Rainbow is Magic是最有创意的愚人节活动，太好笑了" },
          { source: "YouTube", sentiment: "正面", text: "Tachanka骑独角兽是Siege最经典的meme之一" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "Rainbow is Magic Event Gameplay", type: "体验", url: "搜索关键词: R6 Siege Rainbow is Magic event" },
        { platform: "B站", title: "彩虹六号愚人节活动 彩虹即魔法", type: "体验", url: "搜索关键词: 彩虹六号 彩虹即魔法 愚人节" }
      ]
    },
    {
      id: "showdown",
      name: "对决 / Showdown",
      nameEN: "Showdown",
      nameCN: "对决",
      type: "限时活动",
      category: "PvP特殊",
      status: "已结束",
      playerCount: "3v3",
      season: "Y4S2",
      dateRange: "2019年7月",
      duration: "约3周",
      description: "西部牛仔主题的3v3限时活动。在专属的Fort Truth地图上进行，所有玩家使用特定武器（左轮手枪+霰弹枪），地图为沙漠小镇风格。",
      mechanicBreakdown: {
        base: "守护区域的3v3变体",
        changes: ["限定武器（BOSG+Magnum）", "3v3缩小规模", "西部主题专属地图", "沙尘暴视觉效果"],
        specialMap: "Fort Truth（堡垒真相）"
      },
      gameplayType: "小规模PvP/西部枪战",
      archetypeReference: "西部牛仔决斗概念+缩小规模对战",
      similarGames: ["荒野大镖客 对战", "Gunfight（使命召唤小规模模式）"],
      uniqueElements: ["专属西部主题地图", "限定高伤害武器", "3v3紧凑对战"],
      communityRating: {
        overall: 7.5,
        novelty: 8.5,
        depth: 4.0,
        replayability: 5.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Showdown的西部风格太酷了，BOSG对狙超刺激" },
          { source: "YouTube", sentiment: "正面", text: "Fort Truth是最好的限时活动地图之一" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Showdown Event Gameplay", type: "体验", url: "搜索关键词: R6 Siege Showdown western event" },
        { platform: "B站", title: "彩虹六号西部对决活动", type: "体验", url: "搜索关键词: 彩虹六号 Showdown 西部" }
      ]
    },
    {
      id: "doctors_curse",
      name: "博士诅咒 / Doctor's Curse",
      nameEN: "Doctor's Curse",
      nameCN: "博士诅咒",
      type: "限时活动",
      category: "PvP特殊（捉迷藏）",
      status: "已结束（多次复刻）",
      playerCount: "5v5",
      season: "Y4S3（首次）",
      dateRange: "2019年10月（万圣节）",
      duration: "约3周",
      description: "万圣节主题的捉迷藏/追逐模式。5名'怪物'（近战攻击，使用锤子）追杀5名'幸存者'（仅有陷阱和隐身能力）。在万圣节主题化的Theme Park地图上进行。",
      mechanicBreakdown: {
        roles: {
          monsters: "使用大锤近战攻击，移动速度快，需要在时间内消灭所有幸存者",
          survivors: "没有武器，只有陷阱（Frost夹子、Kapkan诡雷等）和隐身能力（Vigil技能）"
        },
        winConditions: {
          monsters: "在时间内消灭所有幸存者",
          survivors: "至少一人存活到时间结束"
        },
        specialMap: "Theme Park（万圣节版本）"
      },
      gameplayType: "不对称追逐/捉迷藏",
      archetypeReference: "非对称恐怖对战模式",
      similarGames: ["Dead by Daylight", "黎明杀机", "Friday the 13th", "Propnight"],
      uniqueElements: ["Siege引擎下的DBD体验", "恐怖主题改造地图", "独特的近战vs陷阱博弈"],
      communityRating: {
        overall: 9.0,
        novelty: 9.5,
        depth: 5.0,
        replayability: 7.0,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Doctor's Curse是最好的限时活动，每年万圣节都在呼唤回归" },
          { source: "YouTube", sentiment: "正面", text: "比DBD还刺激的捉迷藏，Siege版的黎明杀机" },
          { source: "社区", sentiment: "正面", text: "社区呼声最高的限时活动，许多人希望成为永久模式" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Doctor's Curse Halloween Event", type: "体验", url: "搜索关键词: R6 Siege Doctor's Curse halloween" },
        { platform: "B站", title: "彩虹六号万圣节活动 博士诅咒", type: "体验", url: "搜索关键词: 彩虹六号 万圣节 博士诅咒" }
      ]
    },
    {
      id: "grand_larceny",
      name: "大盗 / Grand Larceny",
      nameEN: "Grand Larceny",
      nameCN: "大盗",
      type: "限时活动",
      category: "PvP特殊",
      status: "已结束",
      playerCount: "5v5",
      season: "Y5S1",
      dateRange: "2020年5月",
      duration: "约3周",
      description: "1920年代美国禁酒令主题的活动。在复古版Hereford Base上进行。所有地板都可破坏（全木质结构），且只能使用霰弹枪。强调垂直对抗。",
      mechanicBreakdown: {
        base: "守护区域变体",
        changes: ["仅限霰弹枪", "所有地板可破坏", "1920年代美学", "复古主题地图"],
        keyMechanics: ["极端垂直对抗", "全破坏地板"]
      },
      gameplayType: "垂直破坏对战",
      archetypeReference: "极端垂直对抗概念验证",
      similarGames: ["无直接类似（独特概念）"],
      uniqueElements: ["全可破坏地板是对Siege核心机制的极致化", "1920年代主题独特", "垂直战术的极端展示"],
      communityRating: {
        overall: 7.5,
        novelty: 8.0,
        depth: 5.0,
        replayability: 5.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Grand Larceny展示了Siege垂直对抗的极致可能性" },
          { source: "社区", sentiment: "正面", text: "全破坏地板太爽了，应该有更多地图支持这种程度的破坏" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Grand Larceny Event", type: "体验", url: "搜索关键词: R6 Siege Grand Larceny event gameplay" },
        { platform: "B站", title: "彩虹六号大盗活动 全破坏地板", type: "体验", url: "搜索关键词: 彩虹六号 Grand Larceny 大盗" }
      ]
    },
    {
      id: "mute_protocol",
      name: "MUTE协议 / M.U.T.E. Protocol",
      nameEN: "M.U.T.E. Protocol",
      nameCN: "MUTE协议",
      type: "限时活动",
      category: "PvP特殊（科幻）",
      status: "已结束（多次复刻）",
      playerCount: "5v5",
      season: "Y5S2（首次）",
      dateRange: "2020年8月",
      duration: "约3周",
      description: "赛博朋克/科幻主题活动。在虚拟化的Tower地图上进行。玩家可以变身为无人机形态在地图中移动和侦察，然后选择位置具现化为人形。",
      mechanicBreakdown: {
        base: "守护区域变体",
        changes: ["玩家可以切换为无人机形态", "无人机形态可以自由移动侦察", "选择位置后具现化为干员", "科幻视觉效果"],
        keyMechanics: ["无人机/人形切换系统", "位置选择的策略性", "全新的信息战维度"]
      },
      gameplayType: "科幻增强对战",
      archetypeReference: "虚拟现实/赛博朋克概念的FPS表达",
      similarGames: ["概念独特，无直接类似", "部分机制类似VR Chat的化身系统"],
      uniqueElements: ["无人机变身系统是全新玩法概念", "改变了Siege的基础移动和信息获取方式", "对Tower地图的有趣再利用"],
      communityRating: {
        overall: 8.0,
        novelty: 9.0,
        depth: 6.0,
        replayability: 6.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "MUTE Protocol的无人机变身系统太有创意了" },
          { source: "YouTube", sentiment: "正面", text: "赛博朋克风格的Siege体验非常新鲜" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege MUTE Protocol Event", type: "体验", url: "搜索关键词: R6 Siege MUTE Protocol event gameplay" },
        { platform: "B站", title: "彩虹六号MUTE协议活动", type: "体验", url: "搜索关键词: 彩虹六号 MUTE协议" }
      ]
    },
    {
      id: "sugar_fright",
      name: "糖果惊魂 / Sugar Fright",
      nameEN: "Sugar Fright",
      nameCN: "糖果惊魂",
      type: "限时活动",
      category: "PvP特殊",
      status: "已结束",
      playerCount: "5v5",
      season: "Y5S3",
      dateRange: "2020年10月（万圣节）",
      duration: "约3周",
      description: "2020年万圣节活动。在糖果主题化的Theme Park地图上进行。玩家被击倒后会变成小南瓜头继续战斗，需要收集糖果获胜。",
      mechanicBreakdown: {
        base: "击杀竞赛变体",
        changes: ["死亡后变为南瓜头形态继续战斗", "收集糖果而非击杀计数", "万圣节糖果主题视觉"],
        keyMechanics: ["死亡不意味着退出", "南瓜头形态的第二生命", "资源收集目标"]
      },
      gameplayType: "资源收集对战",
      archetypeReference: "收集类对战+二次生命机制",
      similarGames: ["Halo Oddball模式（部分概念）", "使命召唤 杀戮确认"],
      uniqueElements: ["死后复生为南瓜头的独特机制", "收集糖果的非传统胜利条件"],
      communityRating: {
        overall: 6.5,
        novelty: 7.5,
        depth: 4.0,
        replayability: 4.5,
        comments: [
          { source: "Reddit", sentiment: "中性", text: "Sugar Fright有趣但不如Doctor's Curse" }
        ]
      },
      videoResources: [
        { platform: "YouTube", title: "R6 Siege Sugar Fright Halloween 2020", type: "体验", url: "搜索关键词: R6 Siege Sugar Fright halloween 2020" }
      ]
    },
    {
      id: "road_to_si",
      name: "通往六邀赛 / Road to S.I.",
      nameEN: "Road to S.I.",
      nameCN: "通往六邀赛",
      type: "限时活动",
      category: "PvP竞技",
      status: "每年复刻",
      playerCount: "5v5",
      season: "每年六邀赛前夕",
      dateRange: "通常在1-2月",
      duration: "约3-4周",
      description: "每年六邀赛（Six Invitational）前夕的限时活动，使用特殊的Stadium地图。Y5引入了Ban/Pick的全新体系测试。部分年份的Stadium地图有半透明墙体等创新元素。",
      mechanicBreakdown: {
        base: "炸弹模式变体",
        changes: ["Stadium专属地图", "部分年份有半透明墙体", "测试新竞技规则"]
      },
      gameplayType: "竞技测试/电竞预热",
      archetypeReference: "电竞预热活动",
      similarGames: ["CS Major预热活动", "其他电竞赛事关联活动"],
      communityRating: {
        overall: 7.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Road to SI的Stadium地图总是带来有趣的创新" }
        ]
      }
    },
    {
      id: "containment",
      name: "围堵 / Containment",
      nameEN: "Containment",
      nameCN: "围堵",
      type: "限时活动",
      category: "PvP不对称",
      status: "已结束",
      playerCount: "5v5",
      season: "Y6S3",
      dateRange: "2021年8月",
      duration: "约3周",
      description: "Extraction预热活动。5名干员对抗5名外星Protean（变体）。干员方需要拆弹，Protean方拥有特殊能力。不对称PvP。",
      mechanicBreakdown: {
        roles: {
          operators: "标准干员，使用枪械，目标拆除炸弹",
          proteans: "外星变体，拥有超强近战和特殊能力"
        }
      },
      gameplayType: "不对称PvP",
      archetypeReference: "不对称多人对战",
      similarGames: ["Evolve", "Dead by Daylight（PvP不对称概念）"],
      communityRating: {
        overall: 6.0,
        novelty: 7.0,
        comments: [
          { source: "Reddit", sentiment: "中性", text: "Containment是不错的Extraction预热，但平衡性一般" }
        ]
      }
    },
    {
      id: "doktor_curse_2",
      name: "博士诅咒回归 / Doctor's Curse Returns",
      nameEN: "Doctor's Curse Returns",
      nameCN: "博士诅咒回归",
      type: "限时活动复刻",
      category: "PvP特殊（捉迷藏）",
      status: "多次复刻",
      season: "多个万圣节赛季",
      description: "Doctor's Curse的复刻版本，因社区强烈要求而多次回归，有时会加入新元素。",
      communityRating: {
        overall: 8.5,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "每年万圣节最期待的就是Doctor's Curse回归" }
        ]
      }
    },
    {
      id: "snow_brawl",
      name: "雪球大战 / Snow Brawl",
      nameEN: "Snow Brawl",
      nameCN: "雪球大战",
      type: "限时活动",
      category: "PvP趣味",
      status: "已结束（曾复刻）",
      playerCount: "5v5",
      season: "Y6S4（首次）",
      dateRange: "2021年12月（圣诞节）",
      duration: "约3周",
      description: "圣诞节/冬季主题活动。雪球战模式，使用雪球替代枪械。在冬季主题地图上进行。",
      mechanicBreakdown: {
        base: "TDM变体",
        changes: ["雪球替代枪械", "冬季主题视觉", "特殊移动机制（滑行）"]
      },
      gameplayType: "趣味对战",
      archetypeReference: "节日趣味模式",
      similarGames: ["守望先锋 雪球对战", "各种游戏的圣诞节活动"],
      communityRating: {
        overall: 6.5,
        novelty: 7.0,
        comments: [
          { source: "Reddit", sentiment: "中性偏正面", text: "Snow Brawl是不错的圣诞节放松活动" }
        ]
      }
    },
    {
      id: "arcade",
      name: "街机模式 / Arcade",
      nameEN: "Arcade",
      nameCN: "街机模式",
      type: "轮换活动",
      category: "PvP特殊规则",
      status: "轮换中",
      season: "Y7起常态化轮换",
      description: "Y7后引入的轮换游戏模式系统。每段时间提供不同的特殊规则变体，如：仅限爆头击杀、仅限手枪、金枪模式、狙击手模式等。",
      mechanicBreakdown: {
        rotationModes: [
          "Headshot Only（仅爆头模式）",
          "Snipers Only（狙击手模式）",
          "Pistols Only（手枪模式）",
          "Golden Gun（金枪模式—一枪一杀）",
          "Weapon Roulette（武器轮盘—每次击杀更换武器）"
        ]
      },
      gameplayType: "规则变体合集",
      archetypeReference: "Arcade/Fun模式系统",
      similarGames: ["CS2 Arms Race / Flying Scoutsman", "使命召唤 Party模式", "Halo Action Sack"],
      uniqueElements: ["持续提供新鲜感的轮换系统", "测试特殊规则的实验场"],
      communityRating: {
        overall: 7.0,
        comments: [
          { source: "Reddit", sentiment: "正面", text: "Arcade模式轮换系统让Siege保持了新鲜感" }
        ]
      }
    }
  ]
};

// 玩法模式评价体系
const MODE_RATING_SYSTEM = {
  dimensions: [
    { id: "overall", name: "综合评分", description: "模式的整体质量和玩家体验" },
    { id: "novelty", name: "创新度", description: "模式在概念和机制上的创新程度" },
    { id: "depth", name: "策略深度", description: "模式提供的策略和决策层次" },
    { id: "accessibility", name: "易上手度", description: "新玩家理解和享受该模式的容易程度" },
    { id: "replayability", name: "重玩价值", description: "模式的长期吸引力和重复游玩意愿" },
    { id: "communityReception", name: "社区反馈", description: "玩家社区对该模式的总体评价" }
  ],
  ratingScale: "1-10分制",
  archetypeCategories: [
    "攻防对抗（Search & Destroy型）",
    "区域控制（Domination型）",
    "VIP/护送（Escort型）",
    "击杀竞赛（TDM型）",
    "PvE合作（Co-op Survival型）",
    "不对称对战（Asymmetric型）",
    "趣味/派对（Party型）",
    "追逐/捉迷藏（Hide & Seek型）",
    "规则变体（Arcade型）"
  ]
};

if (typeof module !== 'undefined') module.exports = { GAME_MODES_DATA, MODE_RATING_SYSTEM };

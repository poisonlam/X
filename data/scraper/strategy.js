/**
 * R6 数据抓取策略管理器
 * 
 * 多路径方案：根据可用性自动选择最佳数据获取方式
 * 
 * 优先级（从高到低）：
 *   路径1: Ubisoft 官方 API（最直接、数据最完整）
 *   路径2: GRID R6 Data Portal（官方电竞数据门户，需申请）
 *   路径3: Playwright 抓取 R6 Tracker（作为兜底方案）
 * 
 * 数据层次：
 *   Level 1 - 生涯聚合统计（干员累计 KD/胜率/时长）   → 路径1 可获取
 *   Level 2 - 比赛历史列表（地图、结果、时间）         → 路径1/2 可获取
 *   Level 3 - 回合级详情（每回合干员选取、KDA）         → 路径2/3 可获取
 *   Level 4 - 回合内事件（击杀时间线、拆包事件等）      → 仅 r6-dissect 本地回放
 */

const fs = require('fs');
const path = require('path');

class StrategyManager {
  constructor() {
    this.strategies = [];
    this.results = {
      tested: {},
      recommended: null,
    };
  }

  /**
   * 注册所有可用策略
   */
  registerStrategies() {
    this.strategies = [
      {
        id: 'ubisoft-api',
        name: 'Ubisoft 官方 API (溯源方案)',
        priority: 1,
        description: '直接调用 Ubisoft 后端 API，这是 R6 Tracker 等网站的数据源头',
        requirements: [
          '需要 Ubisoft 账号（建议创建专用小号）',
          '账号需关闭 2FA',
          '需要 Node.js 运行环境',
        ],
        capabilities: {
          playerSearch: true,       // 搜索玩家
          playerStats: true,        // 玩家统计
          operatorStats: true,      // 干员统计（生涯累计）
          rankHistory: true,        // 段位历史
          matchHistory: 'partial',  // 比赛历史（可能有限制）
          roundDetail: false,       // 单回合详情（API 不直接提供）
          operatorPerRound: false,  // 每回合干员（API 不直接提供）
          leaderboard: true,        // 排行榜
        },
        dataLevel: 'Level 1-2',
        rateLimit: '约每秒 1-2 次请求，频繁请求可能被限速',
        pros: [
          '数据最原始、最准确',
          '无需绕过 Cloudflare',
          'JSON 格式，解析简单',
          '批量查询效率高（单次 200 个 profileId）',
          '支持历史赛季数据',
        ],
        cons: [
          'API 端点可能随游戏更新变化',
          '部分统计端点（如旧版 getStats）已损坏/弃用',
          '不提供单局/单回合的详细干员选取',
          '需要管理认证 ticket 的刷新',
        ],
        setupSteps: [
          '1. 创建 Ubisoft 专用小号（https://account.ubisoft.com/）',
          '2. 关闭该账号的 2FA',
          '3. 设置环境变量 UBI_EMAIL 和 UBI_PASSWORD',
          '4. 运行 node ubisoft-api.js --test 测试端点可用性',
          '5. 根据测试结果确认可用的端点，开始采集',
        ],
      },

      {
        id: 'grid-portal',
        name: 'GRID R6 Data Portal (官方电竞数据)',
        priority: 2,
        description: 'Ubisoft 与 GRID 合作推出的官方电竞数据门户，提供最权威的赛事数据',
        requirements: [
          '需要在 grid.gg 申请 Non-Commercial Access（免费）',
          '申请审核可能需要几天时间',
          '需要描述使用目的',
        ],
        capabilities: {
          playerSearch: true,
          playerStats: true,
          operatorStats: true,
          rankHistory: true,
          matchHistory: true,       // 完整比赛历史
          roundDetail: true,        // 回合级详情
          operatorPerRound: true,   // ⭐ 每回合干员（电竞数据）
          leaderboard: false,       // 可能不提供公开排行榜
        },
        dataLevel: 'Level 1-3（电竞赛事）',
        rateLimit: '免费层有限制，付费层无限制',
        pros: [
          '最权威的官方电竞数据',
          '包含回合级详情（干员、战术等）',
          '标准化 API，文档完善',
          '支持实时数据、历史数据、预测数据',
          'SQL Playground 支持自定义查询',
        ],
        cons: [
          '需要申请和审核',
          '免费层 API 调用有限',
          '主要覆盖职业赛事，非普通玩家排位数据',
          '可能不包含低段位玩家数据',
        ],
        setupSteps: [
          '1. 访问 https://grid.gg/get-access/',
          '2. 在 "NON COMMERCIAL ACCESS" 下点击 "Request Access"',
          '3. 填写申请（说明是数据分析/研究项目）',
          '4. 等待审核通过后获取 API 密钥',
          '5. 查阅 GRID API 文档开始接入',
        ],
      },

      {
        id: 'playwright-scraper',
        name: 'Playwright 抓取 R6 Tracker (兜底方案)',
        priority: 3,
        description: '使用浏览器自动化抓取 R6 Tracker 网站数据',
        requirements: [
          '需要 Node.js 和 Playwright',
          '需要 Chromium 浏览器',
          '需要处理 Cloudflare 验证',
        ],
        capabilities: {
          playerSearch: true,
          playerStats: true,
          operatorStats: true,
          rankHistory: true,
          matchHistory: true,
          roundDetail: true,        // R6 Tracker 显示回合详情
          operatorPerRound: true,   // ⭐ R6 Tracker 显示每回合干员
          leaderboard: true,
        },
        dataLevel: 'Level 1-3',
        rateLimit: '慢速（每次请求 2-5 秒），需避免被封',
        pros: [
          '数据最丰富（包含回合级干员选取）',
          '无需 Ubisoft 账号',
          '数据结构与用户在网站上看到的一致',
          '包含各段位玩家数据',
        ],
        cons: [
          '速度最慢（需要渲染完整页面）',
          'Cloudflare 防护可能导致失败',
          '页面 DOM 结构变化会导致选择器失效',
          '容易被检测和封禁',
          '需要大量的错误处理和重试逻辑',
        ],
        setupSteps: [
          '1. cd data/scraper && npm install',
          '2. npx playwright install chromium',
          '3. node scraper.js --test 测试连通性',
          '4. 根据实际页面结构调整 CSS 选择器',
          '5. 正式运行并监控成功率',
        ],
      },

      {
        id: 'r6-dissect',
        name: 'r6-dissect 本地回放解析 (补充方案)',
        priority: 4,
        description: '解析本地保存的 R6 比赛回放文件（.rec 格式），获取最详细的回合数据',
        requirements: [
          '需要 Go 语言运行环境',
          '需要有本地的比赛回放文件',
          '回放文件路径通常在游戏安装目录下',
        ],
        capabilities: {
          playerSearch: false,
          playerStats: false,
          operatorStats: false,
          rankHistory: false,
          matchHistory: false,
          roundDetail: true,         // ⭐ 最详细的回合数据
          operatorPerRound: true,    // ⭐ 每回合干员
          leaderboard: false,
        },
        dataLevel: 'Level 3-4 (仅限本地回放)',
        rateLimit: '无限制（本地文件）',
        pros: [
          '数据最详细（击杀时间线、拆包事件等）',
          '无需网络请求，无速率限制',
          '数据100%准确（直接解析游戏数据）',
          '包含队伍信息、点位信息',
        ],
        cons: [
          '只能解析自己的比赛回放',
          '数据量有限（取决于玩多少局）',
          '需要本地安装游戏并保存回放',
          '不适合大规模数据收集',
        ],
        setupSteps: [
          '1. 安装 Go 语言环境',
          '2. go install github.com/redraskal/r6-dissect@latest',
          '3. 找到游戏回放文件目录',
          '4. r6-dissect <replay-folder> -x output.json',
          '5. 解析 JSON 获取干员和地图数据',
        ],
      },
    ];
  }

  /**
   * 输出策略报告
   */
  generateReport() {
    this.registerStrategies();

    let report = `
╔══════════════════════════════════════════════════════════════════════╗
║              R6S 数据抓取 · 多路径策略报告                             ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  目标: 构建 [地图 × 干员 × 段位] 的选取率和胜率数据集                   ║
║  核心发现: R6 Tracker 等网站的数据源头是 Ubisoft 官方 API               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

`;

    for (const strategy of this.strategies) {
      report += `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[优先级 ${strategy.priority}] ${strategy.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 说明: ${strategy.description}
  📊 数据层级: ${strategy.dataLevel}
  ⏱  速率: ${strategy.rateLimit}

  ✅ 优点:
${strategy.pros.map(p => `    • ${p}`).join('\n')}

  ❌ 缺点:
${strategy.cons.map(c => `    • ${c}`).join('\n')}

  📦 前置需求:
${strategy.requirements.map(r => `    • ${r}`).join('\n')}

  🚀 启动步骤:
${strategy.setupSteps.map(s => `    ${s}`).join('\n')}

  🔍 能力矩阵:
${Object.entries(strategy.capabilities).map(([k, v]) => {
  const icon = v === true ? '✅' : v === false ? '❌' : '⚠️';
  return `    ${icon} ${k}: ${v}`;
}).join('\n')}
`;
    }

    report += `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
推荐实施方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🏆 主力方案: Ubisoft 官方 API + Playwright 抓取（互补）

  Phase 1 - 验证 Ubisoft API（立即可做）
    → 创建小号，测试各端点可用性
    → 确认哪些端点能返回数据
    → 特别关注 match history 和 leaderboard 端点

  Phase 2 - 构建基础数据集（基于 API 结果）
    如果 match history 端点可用：
      → 直接从 API 获取 "比赛列表(含地图)" + "干员生涯统计"
      → 通过相关性推断地图-干员关系
    如果端点不可用：
      → 切换到 Playwright 方案抓取 R6 Tracker
      → 从 R6 Tracker 的玩家页获取回合级干员数据

  Phase 3 - 申请 GRID Portal（中期补充）
    → 申请 Non-Commercial Access
    → 获取职业赛事中的权威地图×干员数据
    → 与排位数据形成对比参考

  Phase 4 - 数据融合与持续更新
    → 将 Ubisoft API 的排位数据 + GRID 的赛事数据合并
    → 建立自动化更新机制
    → 定期刷新统计数据
`;

    return report;
  }
}

// CLI 入口
if (require.main === module) {
  const manager = new StrategyManager();
  console.log(manager.generateReport());
}

module.exports = { StrategyManager };

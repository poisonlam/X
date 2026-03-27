/**
 * R6 Tracker 抓取配置
 * 
 * 调整这些参数来控制抓取行为
 */

const CONFIG = {
  // ==================== 目标网站 ====================
  baseURL: "https://r6.tracker.network",
  leaderboardURL: "https://r6.tracker.network/r6siege/leaderboards",
  
  // ==================== 抓取范围 ====================
  scraping: {
    // 每个段位目标抓取的玩家数
    playersPerRank: 50,
    
    // 每个玩家抓取的最近对局数
    matchesPerPlayer: 20,
    
    // 目标段位范围（从高到低）
    targetRanks: [
      "Champion",
      "Diamond",
      "Emerald",
      "Platinum",
      "Gold",
      "Silver",
      "Bronze",
      "Copper"
    ],
    
    // 目标赛季（留空则抓取当前赛季）
    targetSeason: "",
    
    // 目标平台
    platform: "pc"  // "pc", "psn", "xbl"
  },

  // ==================== 速率控制 ====================
  rateLimit: {
    // 页面之间的延迟（毫秒）
    pageDelay: 2000,
    
    // 请求之间的延迟（毫秒）
    requestDelay: 1000,
    
    // 随机延迟范围（在基础延迟上增加的随机毫秒数）
    randomDelayMax: 1500,
    
    // 翻页延迟（毫秒）
    paginationDelay: 3000,
    
    // 失败后重试延迟（毫秒）
    retryDelay: 5000,
    
    // 最大重试次数
    maxRetries: 3,
    
    // 遇到速率限制时的暂停时间（毫秒）
    rateLimitPause: 30000
  },

  // ==================== 浏览器配置 ====================
  browser: {
    headless: true,
    
    // 视窗大小
    viewport: { width: 1920, height: 1080 },
    
    // User-Agent 轮换列表
    userAgents: [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
    ],
    
    // 超时设置（毫秒）
    navigationTimeout: 30000,
    waitTimeout: 15000
  },

  // ==================== 输出配置 ====================
  output: {
    // 原始数据目录
    rawDir: "./output/raw",
    
    // 统计数据目录
    statsDir: "./output/stats",
    
    // 进度文件（支持断点续传）
    progressFile: "./output/progress.json",
    
    // 每抓取N个玩家保存一次进度
    saveInterval: 5
  },

  // ==================== 地图名称映射 ====================
  // R6 Tracker 上显示的地图名称 -> 我们数据库中的地图 ID
  mapNameMapping: {
    "Bank": "bank",
    "Bartlett University": "bartlett_u",
    "Border": "border",
    "Chalet": "chalet",
    "Club House": "club_house",
    "Coastline": "coastline",
    "Consulate": "consulate",
    "Emerald Plains": "emerald_plains",
    "Favela": "favela",
    "Fortress": "fortress",
    "Hereford Base": "hereford_base",
    "House": "house",
    "Kafe Dostoyevsky": "kafe_dostoyevsky",
    "Kanal": "kanal",
    "Lair": "lair",
    "Nighthaven Labs": "nighthaven_labs",
    "Oregon": "oregon",
    "Outback": "outback",
    "Presidential Plane": "presidential_plane",
    "Skyscraper": "skyscraper",
    "Theme Park": "theme_park",
    "Tower": "tower",
    "Villa": "villa",
    "Yacht": "yacht"
  },

  // ==================== 段位映射 ====================
  rankMapping: {
    "Champion": { tier: "Champion", mmrMin: 5000, color: "#FFD700" },
    "Diamond": { tier: "Diamond", mmrMin: 4400, color: "#B9F2FF" },
    "Emerald": { tier: "Emerald", mmrMin: 3800, color: "#50C878" },
    "Platinum": { tier: "Platinum", mmrMin: 3200, color: "#E5E4E2" },
    "Gold": { tier: "Gold", mmrMin: 2600, color: "#FFD700" },
    "Silver": { tier: "Silver", mmrMin: 2000, color: "#C0C0C0" },
    "Bronze": { tier: "Bronze", mmrMin: 1400, color: "#CD7F32" },
    "Copper": { tier: "Copper", mmrMin: 0, color: "#B87333" }
  }
};

module.exports = CONFIG;

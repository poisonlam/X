/**
 * Ubisoft 官方 API 直接调用模块
 * 
 * 溯源方案：R6 Tracker 等第三方网站的数据最终都来自 Ubisoft 的后端 API。
 * 直接调用 Ubisoft API 可以：
 *   1. 避免被 Cloudflare / 反爬虫阻拦
 *   2. 获取最原始、最完整的数据
 *   3. 更高效（JSON API vs 解析 HTML）
 * 
 * Ubisoft API 认证流程：
 *   1. POST 到 public-ubiservices.ubi.com/v3/profiles/sessions 获取 ticket
 *   2. 使用 ticket + sessionId 访问后续所有数据端点
 *   3. ticket 有过期时间，需定期刷新
 * 
 * ⚠️  注意事项：
 *   - 必须使用一个 Ubisoft 账号（建议创建专用小号，关闭 2FA）
 *   - 存在速率限制（429），需要实现退避策略
 *   - 这些是非公开的内部 API，端点可能随游戏更新变化
 * 
 * 数据获取路径：
 *   Ubisoft Account → Auth Ticket → Player Search → Player Stats → Match History
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// ==================== 常量定义 ====================

const UBISOFT_API = {
  // 认证相关
  auth: {
    url: 'https://public-ubiservices.ubi.com/v3/profiles/sessions',
    appId: 'e3d5ea9e-50bd-43b7-88bf-39794f4e3d40', // R6S PC App ID (from r6api.js)
  },

  // 玩家搜索
  profiles: {
    // 通过用户名搜索玩家
    searchByName: 'https://public-ubiservices.ubi.com/v3/profiles?nameOnPlatform={username}&platformType=uplay',
    // 通过 profileId 搜索
    searchById: 'https://public-ubiservices.ubi.com/v3/profiles?profileId={profileId}',
  },

  // R6S 专用 Space ID（PC 平台）
  spaceId: {
    pc: '5172a557-50b5-4665-b7db-e3f2e8c5041d',
    psn: '05bfb3f7-6c21-4c42-be1f-97a33fb5cf66',
    xbl: '98a601e5-ca91-4440-b600-5b9f3a5eeead',
  },

  // Sandbox ID (PC)
  sandboxId: {
    pc: 'OSBOR_PC_LNCH_A',
    psn: 'OSBOR_PS4_LNCH_A',
    xbl: 'OSBOR_XBOXONE_LNCH_A',
  },

  // 统计数据端点（聚合统计）
  stats: {
    // 基础统计（总击杀、胜率等）
    summary: 'https://public-ubiservices.ubi.com/v1/spaces/{spaceId}/sandboxes/{sandboxId}/playerstats2/statistics?populations={profileId}&statistics=casualpvp_kills,casualpvp_death,casualpvp_matchlost,casualpvp_matchwon,casualpvp_timeplayed,rankedpvp_kills,rankedpvp_death,rankedpvp_matchlost,rankedpvp_matchwon,rankedpvp_timeplayed',
    // 干员统计
    operators: 'https://public-ubiservices.ubi.com/v1/spaces/{spaceId}/sandboxes/{sandboxId}/playerstats2/statistics?populations={profileId}&statistics=operatorpvp_kills,operatorpvp_death,operatorpvp_roundwon,operatorpvp_roundlost,operatorpvp_timeplayed',
  },

  // 排名端点
  ranks: {
    // 获取玩家段位信息（支持历史赛季）
    seasonal: 'https://public-ubiservices.ubi.com/v1/spaces/{spaceId}/sandboxes/{sandboxId}/r6karma/players?board_id=pvp_ranked&season_id={seasonId}&region_id=global&profile_ids={profileId}',
    // v2 赛季接口（Solar Raid 及之后的赛季）
    seasonalV2: 'https://public-ubiservices.ubi.com/v2/spaces/{spaceId}/title/r6s/skill/full_profiles?profile_ids={profileId}&platform_families=pc',
  },

  // ⭐ 关键端点：比赛历史 / Match Replay
  matches: {
    // 获取最近的比赛列表（包含 matchId）
    recent: 'https://public-ubiservices.ubi.com/v1/profiles/{profileId}/playedgames?spaceId={spaceId}&limit={limit}&offset={offset}',
    // 比赛详情（如果可用）
    detail: 'https://public-ubiservices.ubi.com/v1/spaces/{spaceId}/matches/{matchId}',
  },

  // Leaderboard 端点
  leaderboard: {
    // 排行榜（支持分页）
    ranked: 'https://public-ubiservices.ubi.com/v1/spaces/{spaceId}/sandboxes/{sandboxId}/r6karma/player_skill_records?board_id=pvp_ranked&season_id={seasonId}&region_id=global&limit={limit}&offset={offset}',
  },
};

// ==================== 认证管理 ====================

class UbisoftAuth {
  constructor(email, password) {
    this.email = email;
    this.password = password;
    this.ticket = null;
    this.sessionId = null;
    this.expiration = null;
    this.tokenFilePath = path.join(__dirname, '.auth_token.json');
  }

  /**
   * 获取有效的认证 ticket
   * 如果本地有缓存且未过期，直接使用；否则重新登录
   */
  async getTicket() {
    // 尝试从缓存加载
    if (this.ticket && this.expiration && new Date(this.expiration) > new Date()) {
      return this.ticket;
    }

    // 尝试从文件加载
    if (fs.existsSync(this.tokenFilePath)) {
      try {
        const cached = JSON.parse(fs.readFileSync(this.tokenFilePath, 'utf8'));
        if (cached.expiration && new Date(cached.expiration) > new Date()) {
          this.ticket = cached.ticket;
          this.sessionId = cached.sessionId;
          this.expiration = cached.expiration;
          console.log('[Auth] 使用缓存的认证 ticket');
          return this.ticket;
        }
      } catch (e) {
        // 缓存文件损坏，忽略
      }
    }

    // 重新登录
    return await this.login();
  }

  /**
   * 登录 Ubisoft 获取 ticket
   */
  async login() {
    console.log('[Auth] 正在登录 Ubisoft...');

    const authData = JSON.stringify({
      email: this.email,
      password: this.password,
    });

    const response = await this._request('POST', UBISOFT_API.auth.url, {
      'Content-Type': 'application/json',
      'Ubi-AppId': UBISOFT_API.auth.appId,
      'Content-Length': Buffer.byteLength(authData),
    }, authData);

    if (response.ticket) {
      this.ticket = response.ticket;
      this.sessionId = response.sessionId;
      this.expiration = response.expiration;

      // 保存到文件
      fs.writeFileSync(this.tokenFilePath, JSON.stringify({
        ticket: this.ticket,
        sessionId: this.sessionId,
        expiration: this.expiration,
      }, null, 2));

      console.log('[Auth] 登录成功，ticket 已缓存');
      return this.ticket;
    } else {
      throw new Error('[Auth] 登录失败: ' + JSON.stringify(response));
    }
  }

  /**
   * 获取认证后的请求头
   */
  getHeaders() {
    return {
      'Authorization': `Ubi_v1 t=${this.ticket}`,
      'Ubi-AppId': UBISOFT_API.auth.appId,
      'Ubi-SessionId': this.sessionId,
      'Content-Type': 'application/json',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    };
  }

  /**
   * 通用 HTTP 请求封装
   */
  _request(method, url, headers, body = null) {
    return new Promise((resolve, reject) => {
      const urlObj = new URL(url);
      const options = {
        hostname: urlObj.hostname,
        path: urlObj.pathname + urlObj.search,
        method: method,
        headers: headers,
      };

      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(new Error(`Response parse error (${res.statusCode}): ${data.substring(0, 200)}`));
          }
        });
      });

      req.on('error', reject);
      if (body) req.write(body);
      req.end();
    });
  }
}

// ==================== API 客户端 ====================

class R6UbisoftClient {
  constructor(auth, platform = 'pc') {
    this.auth = auth;
    this.platform = platform;
    this.spaceId = UBISOFT_API.spaceId[platform];
    this.sandboxId = UBISOFT_API.sandboxId[platform];
    this.requestCount = 0;
    this.lastRequestTime = 0;
  }

  /**
   * 速率限制 - 确保请求间有足够间隔
   */
  async rateLimit() {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    const minDelay = 500; // 最少间隔 500ms

    if (timeSinceLastRequest < minDelay) {
      await new Promise(resolve => setTimeout(resolve, minDelay - timeSinceLastRequest));
    }

    this.lastRequestTime = Date.now();
    this.requestCount++;
  }

  /**
   * 带重试的认证请求
   */
  async authenticatedRequest(url, maxRetries = 3) {
    await this.rateLimit();

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const ticket = await this.auth.getTicket();
        const response = await this.auth._request('GET', url, this.auth.getHeaders());

        // 检查 token 过期
        if (response.httpCode === 401 || response.errorCode === 1101) {
          console.log('[API] Token 过期，重新认证...');
          this.auth.ticket = null; // 清除缓存
          continue;
        }

        // 检查速率限制
        if (response.httpCode === 429) {
          const waitTime = Math.pow(2, attempt) * 5000; // 指数退避
          console.log(`[API] 速率限制，等待 ${waitTime / 1000}s...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
          continue;
        }

        return response;
      } catch (error) {
        if (attempt < maxRetries - 1) {
          console.log(`[API] 请求失败 (attempt ${attempt + 1}): ${error.message}`);
          await new Promise(resolve => setTimeout(resolve, 2000 * (attempt + 1)));
        } else {
          throw error;
        }
      }
    }
  }

  // ==================== 核心 API 方法 ====================

  /**
   * 通过用户名搜索玩家
   * @param {string} username - Ubisoft 用户名
   * @returns {object} - { profileId, nameOnPlatform, ... }
   */
  async searchPlayer(username) {
    const url = UBISOFT_API.profiles.searchByName.replace('{username}', encodeURIComponent(username));
    const result = await this.authenticatedRequest(url);
    return result.profiles || [];
  }

  /**
   * 获取玩家基础统计
   * @param {string} profileId - 玩家 profileId
   * @returns {object} - 统计数据
   */
  async getPlayerStats(profileId) {
    const url = UBISOFT_API.stats.summary
      .replace('{spaceId}', this.spaceId)
      .replace('{sandboxId}', this.sandboxId)
      .replace('{profileId}', profileId);
    return await this.authenticatedRequest(url);
  }

  /**
   * 获取玩家干员统计（生涯累计）
   * @param {string} profileId - 玩家 profileId
   * @returns {object} - 干员统计数据
   */
  async getOperatorStats(profileId) {
    const url = UBISOFT_API.stats.operators
      .replace('{spaceId}', this.spaceId)
      .replace('{sandboxId}', this.sandboxId)
      .replace('{profileId}', profileId);
    return await this.authenticatedRequest(url);
  }

  /**
   * 获取玩家段位（当前或历史赛季）
   * @param {string} profileId - 玩家 profileId
   * @param {number} seasonId - 赛季 ID（-1 为当前赛季）
   * @returns {object} - 段位数据
   */
  async getPlayerRank(profileId, seasonId = -1) {
    const url = UBISOFT_API.ranks.seasonal
      .replace('{spaceId}', this.spaceId)
      .replace('{sandboxId}', this.sandboxId)
      .replace('{seasonId}', seasonId)
      .replace('{profileId}', profileId);
    return await this.authenticatedRequest(url);
  }

  /**
   * ⭐ 获取玩家最近的比赛列表
   * @param {string} profileId - 玩家 profileId
   * @param {number} limit - 返回数量
   * @param {number} offset - 偏移量
   * @returns {Array} - 比赛列表
   */
  async getMatchHistory(profileId, limit = 20, offset = 0) {
    const url = UBISOFT_API.matches.recent
      .replace('{profileId}', profileId)
      .replace('{spaceId}', this.spaceId)
      .replace('{limit}', limit)
      .replace('{offset}', offset);
    return await this.authenticatedRequest(url);
  }

  /**
   * ⭐ 获取排行榜数据（分页获取各段位玩家）
   * @param {number} seasonId - 赛季 ID
   * @param {number} limit - 每页数量
   * @param {number} offset - 偏移量
   * @returns {Array} - 排行榜玩家列表
   */
  async getLeaderboard(seasonId = -1, limit = 100, offset = 0) {
    const url = UBISOFT_API.leaderboard.ranked
      .replace('{spaceId}', this.spaceId)
      .replace('{sandboxId}', this.sandboxId)
      .replace('{seasonId}', seasonId)
      .replace('{limit}', limit)
      .replace('{offset}', offset);
    return await this.authenticatedRequest(url);
  }

  /**
   * 获取 v2 赛季数据（新版 API）
   * @param {string} profileId - 玩家 profileId
   */
  async getSeasonalV2(profileId) {
    const url = UBISOFT_API.ranks.seasonalV2
      .replace('{spaceId}', this.spaceId)
      .replace('{profileId}', profileId);
    return await this.authenticatedRequest(url);
  }
}

// ==================== 数据抓取协调器 ====================

class R6DataCollector {
  constructor(client) {
    this.client = client;
    this.outputDir = path.join(__dirname, 'output');
    this.rawDir = path.join(this.outputDir, 'raw');
    this.progressFile = path.join(this.outputDir, 'progress_api.json');
  }

  /**
   * 初始化输出目录
   */
  init() {
    [this.outputDir, this.rawDir].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  /**
   * 保存进度
   */
  saveProgress(progress) {
    fs.writeFileSync(this.progressFile, JSON.stringify(progress, null, 2));
  }

  /**
   * 加载进度（断点续传）
   */
  loadProgress() {
    if (fs.existsSync(this.progressFile)) {
      return JSON.parse(fs.readFileSync(this.progressFile, 'utf8'));
    }
    return { completedPlayers: [], lastOffset: 0, collectedData: [] };
  }

  /**
   * 主抓取流程
   * 
   * 路径 A：从 Leaderboard API 获取玩家列表 → 逐个获取统计
   * 路径 B：从 Match History 获取对局（如果端点可用）
   */
  async collectFromLeaderboard(options = {}) {
    const {
      seasonId = -1,
      batchSize = 100,
      totalPlayers = 500,
      startOffset = 0,
    } = options;

    this.init();
    const progress = this.loadProgress();
    let offset = progress.lastOffset || startOffset;
    let allPlayers = [];

    console.log(`[Collector] 开始从排行榜收集数据...`);
    console.log(`[Collector] 赛季: ${seasonId}, 批次大小: ${batchSize}, 目标玩家数: ${totalPlayers}`);

    while (allPlayers.length < totalPlayers) {
      console.log(`[Collector] 获取排行榜 offset=${offset}, 已收集 ${allPlayers.length}/${totalPlayers}`);

      try {
        const leaderboard = await this.client.getLeaderboard(seasonId, batchSize, offset);

        if (!leaderboard || !Array.isArray(leaderboard.players)) {
          console.log('[Collector] 排行榜数据异常或已到达末尾');
          // 尝试解析不同的响应格式
          if (leaderboard && typeof leaderboard === 'object') {
            console.log('[Collector] 响应结构:', Object.keys(leaderboard));
          }
          break;
        }

        for (const player of leaderboard.players) {
          if (allPlayers.length >= totalPlayers) break;
          if (progress.completedPlayers.includes(player.profile_id || player.profileId)) {
            continue;
          }

          const playerData = {
            profileId: player.profile_id || player.profileId,
            username: player.name || player.nameOnPlatform,
            rank: player.rank || null,
            mmr: player.mmr || player.skill_mean || null,
            leaderboardPosition: offset + leaderboard.players.indexOf(player),
          };

          // 获取该玩家的干员统计
          try {
            console.log(`[Collector]   → 获取 ${playerData.username} 的干员统计`);
            const operatorStats = await this.client.getOperatorStats(playerData.profileId);
            playerData.operatorStats = operatorStats;
          } catch (e) {
            console.log(`[Collector]   ⚠ 干员统计获取失败: ${e.message}`);
          }

          // 尝试获取比赛历史
          try {
            console.log(`[Collector]   → 获取 ${playerData.username} 的比赛历史`);
            const matchHistory = await this.client.getMatchHistory(playerData.profileId, 20, 0);
            playerData.matchHistory = matchHistory;
          } catch (e) {
            console.log(`[Collector]   ⚠ 比赛历史获取失败: ${e.message}`);
          }

          allPlayers.push(playerData);

          // 保存单个玩家数据
          const playerFile = path.join(this.rawDir, `player_${playerData.profileId}.json`);
          fs.writeFileSync(playerFile, JSON.stringify(playerData, null, 2));

          // 更新进度
          progress.completedPlayers.push(playerData.profileId);
          progress.lastOffset = offset;
          this.saveProgress(progress);
        }

        offset += batchSize;

        // 每批次后等待
        await new Promise(resolve => setTimeout(resolve, 1000));

      } catch (error) {
        console.error(`[Collector] 批次错误: ${error.message}`);
        // 等待后重试
        await new Promise(resolve => setTimeout(resolve, 10000));
      }
    }

    console.log(`[Collector] 收集完成，共 ${allPlayers.length} 名玩家`);
    return allPlayers;
  }
}

// ==================== 导出 ====================

module.exports = {
  UBISOFT_API,
  UbisoftAuth,
  R6UbisoftClient,
  R6DataCollector,
};

// ==================== CLI 入口 ====================

if (require.main === module) {
  const args = process.argv.slice(2);

  // 从环境变量读取凭据
  const email = process.env.UBI_EMAIL;
  const password = process.env.UBI_PASSWORD;

  if (!email || !password) {
    console.log(`
╔════════════════════════════════════════════════════════════╗
║           Ubisoft API 直接抓取工具                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  使用前需要设置环境变量：                                    ║
║                                                            ║
║  Windows (PowerShell):                                     ║
║    $env:UBI_EMAIL = "your_email@example.com"               ║
║    $env:UBI_PASSWORD = "your_password"                     ║
║                                                            ║
║  Linux/Mac:                                                ║
║    export UBI_EMAIL="your_email@example.com"               ║
║    export UBI_PASSWORD="your_password"                     ║
║                                                            ║
║  ⚠️  强烈建议使用专用小号，并关闭 2FA！                      ║
║                                                            ║
║  用法：                                                     ║
║    node ubisoft-api.js --test           # 测试认证和端点     ║
║    node ubisoft-api.js --collect        # 开始收集数据       ║
║    node ubisoft-api.js --search <name>  # 搜索玩家          ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    `);
    process.exit(1);
  }

  async function main() {
    const auth = new UbisoftAuth(email, password);
    const client = new R6UbisoftClient(auth, 'pc');

    if (args.includes('--test')) {
      console.log('=== 测试模式 ===');
      console.log('1. 测试认证...');
      try {
        await auth.getTicket();
        console.log('✅ 认证成功');
      } catch (e) {
        console.log('❌ 认证失败:', e.message);
        return;
      }

      console.log('\n2. 测试玩家搜索...');
      try {
        const players = await client.searchPlayer('Beaulo.TSM');
        console.log(`✅ 搜索结果: ${JSON.stringify(players, null, 2)}`);
      } catch (e) {
        console.log('⚠️ 玩家搜索:', e.message);
      }

      console.log('\n3. 测试排行榜...');
      try {
        const lb = await client.getLeaderboard(-1, 5, 0);
        console.log(`✅ 排行榜: ${JSON.stringify(lb, null, 2).substring(0, 500)}...`);
      } catch (e) {
        console.log('⚠️ 排行榜:', e.message);
      }

      console.log('\n=== 端点可用性报告 ===');
      console.log('以上测试完成。请根据结果判断哪些端点可用。');
      console.log('如果某些端点返回错误，可能需要调整 URL 或尝试其他端点格式。');

    } else if (args.includes('--collect')) {
      const collector = new R6DataCollector(client);
      await collector.collectFromLeaderboard({
        totalPlayers: args.includes('--small') ? 50 : 500,
      });

    } else if (args.includes('--search')) {
      const nameIdx = args.indexOf('--search') + 1;
      const name = args[nameIdx];
      if (!name) {
        console.log('请提供玩家名称: node ubisoft-api.js --search <username>');
        return;
      }
      const result = await client.searchPlayer(name);
      console.log(JSON.stringify(result, null, 2));
    }
  }

  main().catch(console.error);
}

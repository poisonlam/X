/**
 * R6 Tracker 数据抓取主脚本
 * 
 * 流程:
 * 1. 打开 Leaderboard 排行榜
 * 2. 获取玩家列表（含段位信息）
 * 3. 进入每个玩家的 Profile 页
 * 4. 获取 Match History 对局历史
 * 5. 解析每场对局的回合数据（地图、干员、胜负）
 * 6. 保存原始数据到 JSON 文件
 * 
 * 使用方法:
 *   node scraper.js              # 正常抓取
 *   node scraper.js --test       # 测试模式（只抓取少量数据）
 *   node scraper.js --resume     # 从断点续传
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const CONFIG = require('./config');

// ==================== 工具函数 ====================

/**
 * 随机延迟
 */
function sleep(ms) {
  const randomExtra = Math.floor(Math.random() * CONFIG.rateLimit.randomDelayMax);
  return new Promise(resolve => setTimeout(resolve, ms + randomExtra));
}

/**
 * 获取随机 User-Agent
 */
function getRandomUserAgent() {
  const agents = CONFIG.browser.userAgents;
  return agents[Math.floor(Math.random() * agents.length)];
}

/**
 * 确保输出目录存在
 */
function ensureDirectories() {
  const dirs = [
    CONFIG.output.rawDir,
    CONFIG.output.statsDir,
    path.join(CONFIG.output.rawDir, 'players'),
    path.join(CONFIG.output.rawDir, 'matches')
  ];
  dirs.forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });
}

/**
 * 保存进度（支持断点续传）
 */
function saveProgress(progress) {
  fs.writeFileSync(CONFIG.output.progressFile, JSON.stringify(progress, null, 2));
}

/**
 * 加载进度
 */
function loadProgress() {
  if (fs.existsSync(CONFIG.output.progressFile)) {
    return JSON.parse(fs.readFileSync(CONFIG.output.progressFile, 'utf-8'));
  }
  return {
    completedPlayers: [],
    currentPage: 0,
    totalPlayersScraped: 0,
    totalMatchesScraped: 0,
    lastUpdated: null
  };
}

/**
 * 日志输出
 */
function log(level, message) {
  const timestamp = new Date().toISOString();
  const prefix = {
    'INFO': '✅',
    'WARN': '⚠️',
    'ERROR': '❌',
    'DEBUG': '🔍',
    'PROGRESS': '📊'
  }[level] || '📝';
  console.log(`[${timestamp}] ${prefix} [${level}] ${message}`);
}

// ==================== 核心抓取类 ====================

class R6TrackerScraper {
  constructor(options = {}) {
    this.browser = null;
    this.context = null;
    this.page = null;
    this.isTestMode = options.test || false;
    this.isResume = options.resume || false;
    this.progress = loadProgress();
    this.scrapedData = {
      players: [],
      matches: [],
      rounds: []
    };
  }

  /**
   * 初始化浏览器
   */
  async init() {
    log('INFO', '正在启动浏览器...');
    
    this.browser = await chromium.launch({
      headless: CONFIG.browser.headless,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-setuid-sandbox'
      ]
    });

    this.context = await this.browser.newContext({
      viewport: CONFIG.browser.viewport,
      userAgent: getRandomUserAgent(),
      locale: 'en-US',
      timezoneId: 'America/New_York'
    });

    // 注入反检测脚本
    await this.context.addInitScript(() => {
      // 隐藏 webdriver 特征
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
      // 隐藏 Playwright 特征
      delete navigator.__proto__.webdriver;
      // 模拟 Chrome 插件
      window.chrome = { runtime: {} };
    });

    this.page = await this.context.newPage();
    this.page.setDefaultTimeout(CONFIG.browser.waitTimeout);
    this.page.setDefaultNavigationTimeout(CONFIG.browser.navigationTimeout);

    log('INFO', '浏览器初始化完成');
  }

  /**
   * 关闭浏览器
   */
  async close() {
    if (this.browser) {
      await this.browser.close();
      log('INFO', '浏览器已关闭');
    }
  }

  /**
   * 步骤1: 从 Leaderboard 获取玩家列表
   */
  async scrapeLeaderboard() {
    log('INFO', '开始抓取 Leaderboard 排行榜...');
    const players = [];
    let pageNum = this.isResume ? this.progress.currentPage : 0;
    const maxPlayers = this.isTestMode ? 5 : CONFIG.scraping.playersPerRank * CONFIG.scraping.targetRanks.length;

    try {
      // 访问排行榜页面
      await this.page.goto(CONFIG.leaderboardURL, { waitUntil: 'networkidle' });
      await sleep(CONFIG.rateLimit.pageDelay);

      // 等待 Cloudflare 验证通过
      await this.waitForCloudflare();

      while (players.length < maxPlayers) {
        log('PROGRESS', `正在抓取排行榜第 ${pageNum + 1} 页... (已获取 ${players.length} 个玩家)`);

        // 等待玩家列表加载
        // 注意: 选择器需要根据实际页面结构调整
        await this.page.waitForSelector('[class*="leaderboard"], [class*="player"], table tbody tr', { 
          timeout: CONFIG.browser.waitTimeout 
        }).catch(() => {
          log('WARN', '等待玩家列表超时，尝试继续...');
        });

        // 解析当前页面的玩家数据
        const pagePlayers = await this.page.evaluate(() => {
          const results = [];
          
          // 尝试多种可能的选择器
          // 策略1: 表格行
          const rows = document.querySelectorAll('table tbody tr, [class*="leaderboard-row"], [class*="player-row"]');
          
          rows.forEach(row => {
            try {
              // 尝试获取玩家链接
              const link = row.querySelector('a[href*="/profile/"], a[href*="/r6siege/profile/"]');
              if (!link) return;

              const profileUrl = link.getAttribute('href');
              const playerName = link.textContent?.trim();

              // 尝试获取段位信息
              const rankEl = row.querySelector('[class*="rank"], [class*="tier"], img[alt*="rank"]');
              const rank = rankEl ? (rankEl.textContent?.trim() || rankEl.getAttribute('alt') || '') : '';

              // 尝试获取 MMR/分数
              const scoreEl = row.querySelector('[class*="score"], [class*="mmr"], [class*="rating"]');
              const score = scoreEl ? scoreEl.textContent?.trim() : '';

              // 尝试获取平台
              const platformEl = row.querySelector('[class*="platform"], img[alt*="pc"], img[alt*="ps"], img[alt*="xbox"]');
              const platform = platformEl ? (platformEl.textContent?.trim() || platformEl.getAttribute('alt') || 'pc') : 'pc';

              if (profileUrl && playerName) {
                results.push({
                  name: playerName,
                  profileUrl: profileUrl,
                  rank: rank,
                  score: score,
                  platform: platform
                });
              }
            } catch (e) {
              // 跳过解析错误的行
            }
          });

          return results;
        });

        // 过滤已抓取的玩家
        const newPlayers = pagePlayers.filter(p => 
          !this.progress?.completedPlayers?.includes(p.profileUrl) &&
          !players.some(existing => existing.profileUrl === p.profileUrl)
        );

        players.push(...newPlayers);
        log('INFO', `本页获取 ${newPlayers.length} 个新玩家`);

        // 翻页
        const hasNextPage = await this.goToNextPage();
        if (!hasNextPage) {
          log('INFO', '已到达最后一页');
          break;
        }

        pageNum++;
        this.progress.currentPage = pageNum;
        await sleep(CONFIG.rateLimit.paginationDelay);
      }

    } catch (error) {
      log('ERROR', `抓取排行榜失败: ${error.message}`);
    }

    log('PROGRESS', `排行榜抓取完成，共获取 ${players.length} 个玩家`);
    return players;
  }

  /**
   * 等待 Cloudflare 验证通过
   */
  async waitForCloudflare() {
    log('DEBUG', '检查 Cloudflare 验证...');
    
    try {
      // 检测是否在 Cloudflare 验证页面
      const isChallenge = await this.page.evaluate(() => {
        return document.title.includes('请稍候') || 
               document.title.includes('Just a moment') ||
               document.title.includes('Checking') ||
               document.querySelector('#challenge-running') !== null;
      });

      if (isChallenge) {
        log('WARN', '检测到 Cloudflare 验证，等待通过...');
        // 等待验证完成（最多60秒）
        await this.page.waitForFunction(() => {
          return !document.title.includes('请稍候') && 
                 !document.title.includes('Just a moment') &&
                 !document.title.includes('Checking') &&
                 document.querySelector('#challenge-running') === null;
        }, { timeout: 60000 });
        
        log('INFO', 'Cloudflare 验证通过');
        await sleep(2000);
      } else {
        log('DEBUG', '无需 Cloudflare 验证');
      }
    } catch (error) {
      log('WARN', `Cloudflare 验证等待超时: ${error.message}`);
    }
  }

  /**
   * 翻页到下一页
   */
  async goToNextPage() {
    try {
      // 尝试多种翻页方式
      const nextButton = await this.page.$([
        'button[class*="next"]',
        'a[class*="next"]',
        '[aria-label="Next"]',
        '[class*="pagination"] button:last-child',
        '[class*="pagination"] a:last-child',
        'button:has-text("Next")',
        'a:has-text("Next")',
        'button:has-text(">")',
        '[class*="load-more"]'
      ].join(', '));

      if (nextButton) {
        const isDisabled = await nextButton.evaluate(el => 
          el.disabled || el.classList.contains('disabled') || el.getAttribute('aria-disabled') === 'true'
        );
        
        if (isDisabled) return false;
        
        await nextButton.click();
        await sleep(CONFIG.rateLimit.pageDelay);
        return true;
      }

      // 尝试滚动加载更多（无限滚动的情况）
      const previousHeight = await this.page.evaluate(() => document.body.scrollHeight);
      await this.page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await sleep(CONFIG.rateLimit.pageDelay);
      const newHeight = await this.page.evaluate(() => document.body.scrollHeight);
      
      return newHeight > previousHeight;

    } catch (error) {
      log('WARN', `翻页失败: ${error.message}`);
      return false;
    }
  }

  /**
   * 步骤2: 抓取单个玩家的详细数据
   */
  async scrapePlayerProfile(player) {
    log('INFO', `正在抓取玩家: ${player.name} (${player.rank})`);
    
    const playerData = {
      ...player,
      scrapedAt: new Date().toISOString(),
      seasonStats: null,
      matches: []
    };

    try {
      // 构建完整的 profile URL
      const profileUrl = player.profileUrl.startsWith('http') 
        ? player.profileUrl 
        : `${CONFIG.baseURL}${player.profileUrl}`;

      await this.page.goto(profileUrl, { waitUntil: 'networkidle' });
      await this.waitForCloudflare();
      await sleep(CONFIG.rateLimit.requestDelay);

      // 解析玩家基础统计
      playerData.seasonStats = await this.page.evaluate(() => {
        const stats = {};
        
        // 尝试获取当前赛季数据
        const statElements = document.querySelectorAll('[class*="stat"], [class*="kd"], [class*="winrate"]');
        statElements.forEach(el => {
          const label = el.querySelector('[class*="label"], [class*="name"], span:first-child');
          const value = el.querySelector('[class*="value"], [class*="number"], span:last-child');
          if (label && value) {
            stats[label.textContent.trim()] = value.textContent.trim();
          }
        });

        return stats;
      });

      // 获取对局历史
      playerData.matches = await this.scrapeMatchHistory(profileUrl);

    } catch (error) {
      log('ERROR', `抓取玩家 ${player.name} 失败: ${error.message}`);
    }

    return playerData;
  }

  /**
   * 步骤3: 抓取玩家的对局历史
   */
  async scrapeMatchHistory(profileUrl) {
    const matches = [];
    const maxMatches = this.isTestMode ? 3 : CONFIG.scraping.matchesPerPlayer;

    try {
      // 导航到对局历史页面
      // R6 Tracker 的 URL 结构可能是: /r6siege/profile/{platform}/{name}/matches
      const matchesUrl = profileUrl.replace(/\/?$/, '') + '/matches';
      
      await this.page.goto(matchesUrl, { waitUntil: 'networkidle' });
      await this.waitForCloudflare();
      await sleep(CONFIG.rateLimit.requestDelay);

      // 等待对局列表加载
      await this.page.waitForSelector('[class*="match"], [class*="game"], [class*="activity"]', {
        timeout: CONFIG.browser.waitTimeout
      }).catch(() => {
        log('WARN', '等待对局列表超时');
      });

      // 获取对局列表
      const matchLinks = await this.page.evaluate(() => {
        const links = [];
        const matchElements = document.querySelectorAll(
          'a[href*="/match/"], a[href*="/matches/"], [class*="match-row"] a, [class*="match-item"] a'
        );
        
        matchElements.forEach(el => {
          const href = el.getAttribute('href');
          if (href && !links.includes(href)) {
            links.push(href);
          }
        });

        return links;
      });

      log('DEBUG', `找到 ${matchLinks.length} 场对局链接`);

      // 逐场解析对局
      for (let i = 0; i < Math.min(matchLinks.length, maxMatches); i++) {
        const matchData = await this.scrapeMatchDetail(matchLinks[i]);
        if (matchData) {
          matches.push(matchData);
        }
        await sleep(CONFIG.rateLimit.requestDelay);
      }

    } catch (error) {
      log('ERROR', `抓取对局历史失败: ${error.message}`);
    }

    return matches;
  }

  /**
   * 步骤4: 抓取单场对局详情（含每回合干员选取）
   */
  async scrapeMatchDetail(matchUrl) {
    try {
      const fullUrl = matchUrl.startsWith('http') 
        ? matchUrl 
        : `${CONFIG.baseURL}${matchUrl}`;

      await this.page.goto(fullUrl, { waitUntil: 'networkidle' });
      await this.waitForCloudflare();
      await sleep(CONFIG.rateLimit.requestDelay);

      // 解析对局数据
      const matchData = await this.page.evaluate(() => {
        const data = {
          map: null,
          result: null,
          score: null,
          date: null,
          mode: null,
          rounds: []
        };

        // 获取地图名称
        const mapEl = document.querySelector(
          '[class*="map-name"], [class*="map"], [class*="mapName"], img[alt*="map"]'
        );
        if (mapEl) {
          data.map = mapEl.textContent?.trim() || mapEl.getAttribute('alt') || null;
        }

        // 获取比赛结果
        const resultEl = document.querySelector(
          '[class*="result"], [class*="outcome"], [class*="win"], [class*="loss"]'
        );
        if (resultEl) {
          const text = resultEl.textContent.trim().toLowerCase();
          data.result = text.includes('win') || text.includes('victory') ? 'win' : 
                       text.includes('loss') || text.includes('defeat') ? 'loss' : 'draw';
        }

        // 获取比分
        const scoreEl = document.querySelector('[class*="score"]');
        if (scoreEl) {
          data.score = scoreEl.textContent.trim();
        }

        // 获取日期
        const dateEl = document.querySelector('[class*="date"], time, [class*="time"]');
        if (dateEl) {
          data.date = dateEl.getAttribute('datetime') || dateEl.textContent.trim();
        }

        // 获取游戏模式
        const modeEl = document.querySelector('[class*="mode"], [class*="playlist"]');
        if (modeEl) {
          data.mode = modeEl.textContent.trim();
        }

        // 🔑 核心: 获取每回合数据
        const roundElements = document.querySelectorAll(
          '[class*="round"], [class*="round-row"], tr[class*="round"]'
        );

        roundElements.forEach((roundEl, index) => {
          const round = {
            roundNumber: index + 1,
            side: null,      // ATK or DEF
            operator: null,  // 干员名称
            kills: 0,
            deaths: 0,
            assists: 0,
            won: null,
            // 如果能看到队友的信息
            teammates: []
          };

          // 获取攻防方
          const sideEl = roundEl.querySelector(
            '[class*="side"], [class*="atk"], [class*="def"], [class*="attack"], [class*="defend"]'
          );
          if (sideEl) {
            const sideText = sideEl.textContent.trim().toLowerCase();
            round.side = sideText.includes('atk') || sideText.includes('attack') ? 'ATK' : 'DEF';
          }

          // 获取干员
          const operatorEl = roundEl.querySelector(
            '[class*="operator"], img[alt*="operator"], [class*="agent"]'
          );
          if (operatorEl) {
            round.operator = operatorEl.textContent?.trim() || 
                            operatorEl.getAttribute('alt')?.replace(/operator/i, '').trim() || 
                            null;
          }

          // 获取击杀数据
          const killsEl = roundEl.querySelector('[class*="kills"], [class*="kill"]');
          const deathsEl = roundEl.querySelector('[class*="deaths"], [class*="death"]');
          const assistsEl = roundEl.querySelector('[class*="assists"], [class*="assist"]');
          
          round.kills = killsEl ? parseInt(killsEl.textContent) || 0 : 0;
          round.deaths = deathsEl ? parseInt(deathsEl.textContent) || 0 : 0;
          round.assists = assistsEl ? parseInt(assistsEl.textContent) || 0 : 0;

          // 获取回合胜负
          const roundResultEl = roundEl.querySelector(
            '[class*="result"], [class*="won"], [class*="lost"]'
          );
          if (roundResultEl) {
            const rText = roundResultEl.textContent.trim().toLowerCase();
            round.won = rText.includes('won') || rText.includes('win') || 
                       roundResultEl.classList.toString().includes('won') ||
                       roundResultEl.classList.toString().includes('win');
          }

          // 尝试获取队友的干员选取
          const teammateEls = roundEl.querySelectorAll(
            '[class*="teammate"], [class*="team-member"], [class*="ally"]'
          );
          teammateEls.forEach(tmEl => {
            const tmOp = tmEl.querySelector('[class*="operator"], img[alt]');
            if (tmOp) {
              round.teammates.push({
                operator: tmOp.textContent?.trim() || tmOp.getAttribute('alt')?.trim() || null
              });
            }
          });

          if (round.operator || round.side) {
            data.rounds.push(round);
          }
        });

        return data;
      });

      if (matchData.map) {
        log('DEBUG', `对局: ${matchData.map} | ${matchData.result} | ${matchData.rounds.length} 回合`);
      }

      return matchData;

    } catch (error) {
      log('ERROR', `抓取对局详情失败: ${error.message}`);
      return null;
    }
  }

  /**
   * 保存玩家数据到文件
   */
  savePlayerData(playerData) {
    const filename = `${playerData.name.replace(/[^a-zA-Z0-9_-]/g, '_')}_${Date.now()}.json`;
    const filepath = path.join(CONFIG.output.rawDir, 'players', filename);
    fs.writeFileSync(filepath, JSON.stringify(playerData, null, 2));
    log('DEBUG', `玩家数据已保存: ${filename}`);
  }

  /**
   * 主执行流程
   */
  async run() {
    ensureDirectories();
    log('INFO', '=== R6 Tracker 数据抓取开始 ===');
    log('INFO', `模式: ${this.isTestMode ? '测试模式' : '正式模式'}`);
    log('INFO', `续传: ${this.isResume ? '是' : '否'}`);

    try {
      await this.init();

      // 步骤1: 获取玩家列表
      const players = await this.scrapeLeaderboard();

      if (players.length === 0) {
        log('ERROR', '未获取到任何玩家数据，请检查网站结构是否变更');
        return;
      }

      // 步骤2-4: 逐个玩家抓取详情
      let processedCount = 0;
      for (const player of players) {
        // 跳过已处理的玩家
        if (this.progress.completedPlayers.includes(player.profileUrl)) {
          log('DEBUG', `跳过已处理的玩家: ${player.name}`);
          continue;
        }

        const playerData = await this.scrapePlayerProfile(player);
        this.savePlayerData(playerData);
        this.scrapedData.players.push(playerData);

        // 更新进度
        processedCount++;
        this.progress.completedPlayers.push(player.profileUrl);
        this.progress.totalPlayersScraped++;
        this.progress.totalMatchesScraped += playerData.matches.length;
        this.progress.lastUpdated = new Date().toISOString();

        // 定期保存进度
        if (processedCount % CONFIG.output.saveInterval === 0) {
          saveProgress(this.progress);
          log('PROGRESS', `进度: ${processedCount}/${players.length} 玩家 | ${this.progress.totalMatchesScraped} 场对局`);
        }

        await sleep(CONFIG.rateLimit.requestDelay);
      }

      // 保存最终进度
      saveProgress(this.progress);

      // 保存汇总数据
      const summaryPath = path.join(CONFIG.output.rawDir, `scrape_summary_${Date.now()}.json`);
      fs.writeFileSync(summaryPath, JSON.stringify({
        totalPlayers: this.scrapedData.players.length,
        totalMatches: this.progress.totalMatchesScraped,
        completedAt: new Date().toISOString(),
        config: {
          playersPerRank: CONFIG.scraping.playersPerRank,
          matchesPerPlayer: CONFIG.scraping.matchesPerPlayer,
          targetRanks: CONFIG.scraping.targetRanks
        }
      }, null, 2));

      log('INFO', '=== 抓取完成 ===');
      log('PROGRESS', `总计: ${this.scrapedData.players.length} 玩家, ${this.progress.totalMatchesScraped} 场对局`);

    } catch (error) {
      log('ERROR', `抓取过程发生严重错误: ${error.message}`);
      saveProgress(this.progress);
    } finally {
      await this.close();
    }
  }
}

// ==================== 命令行入口 ====================

const args = process.argv.slice(2);
const options = {
  test: args.includes('--test'),
  resume: args.includes('--resume')
};

const scraper = new R6TrackerScraper(options);
scraper.run().catch(error => {
  log('ERROR', `未捕获的错误: ${error.message}`);
  process.exit(1);
});

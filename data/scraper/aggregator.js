/**
 * R6 Tracker 数据聚合器
 * 
 * 读取抓取的原始数据，聚合生成:
 * 1. 地图 × 干员 选取率（按段位）
 * 2. 地图 × 干员 回合胜率（按段位）
 * 3. 干员在不同地图上的热门程度排名
 * 
 * 使用方法:
 *   node aggregator.js
 *   node aggregator.js --output ../operator_map_stats.js
 */

const fs = require('fs');
const path = require('path');
const CONFIG = require('./config');

// ==================== 数据结构 ====================

/**
 * 聚合数据容器
 * 结构: mapStats[mapId][operatorId][rankTier] = { picks, wins, rounds, kills, deaths }
 */
class DataAggregator {
  constructor() {
    this.mapStats = {};        // 地图×干员×段位 统计
    this.globalOperatorStats = {}; // 全局干员统计
    this.globalMapStats = {};  // 全局地图统计
    this.totalRounds = 0;
    this.totalMatches = 0;
    this.errors = [];
  }

  /**
   * 加载所有原始玩家数据文件
   */
  loadRawData() {
    const playersDir = path.join(CONFIG.output.rawDir, 'players');
    
    if (!fs.existsSync(playersDir)) {
      console.error('❌ 原始数据目录不存在，请先运行 scraper.js 抓取数据');
      process.exit(1);
    }

    const files = fs.readdirSync(playersDir).filter(f => f.endsWith('.json'));
    console.log(`📂 找到 ${files.length} 个玩家数据文件`);

    const allPlayers = [];
    for (const file of files) {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(playersDir, file), 'utf-8'));
        allPlayers.push(data);
      } catch (e) {
        this.errors.push(`解析文件失败: ${file} - ${e.message}`);
      }
    }

    return allPlayers;
  }

  /**
   * 解析玩家段位
   */
  parseRank(player) {
    const rankStr = (player.rank || '').toLowerCase();
    
    for (const [rankName, rankInfo] of Object.entries(CONFIG.rankMapping)) {
      if (rankStr.includes(rankName.toLowerCase())) {
        return rankName;
      }
    }

    // 尝试通过分数推断段位
    if (player.score) {
      const score = parseInt(player.score);
      if (!isNaN(score)) {
        const sortedRanks = Object.entries(CONFIG.rankMapping)
          .sort((a, b) => b[1].mmrMin - a[1].mmrMin);
        for (const [rankName, rankInfo] of sortedRanks) {
          if (score >= rankInfo.mmrMin) {
            return rankName;
          }
        }
      }
    }

    return "Unknown";
  }

  /**
   * 规范化地图名称
   */
  normalizeMapName(mapName) {
    if (!mapName) return null;
    
    // 先尝试直接映射
    if (CONFIG.mapNameMapping[mapName]) {
      return CONFIG.mapNameMapping[mapName];
    }

    // 模糊匹配
    const normalized = mapName.trim().toLowerCase();
    for (const [displayName, mapId] of Object.entries(CONFIG.mapNameMapping)) {
      if (displayName.toLowerCase() === normalized) {
        return mapId;
      }
    }

    // 返回清理后的名称作为 ID
    return normalized.replace(/\s+/g, '_');
  }

  /**
   * 规范化干员名称
   */
  normalizeOperatorName(operatorName) {
    if (!operatorName) return null;
    return operatorName.trim().toLowerCase().replace(/\s+/g, '_');
  }

  /**
   * 核心: 聚合所有数据
   */
  aggregate(players) {
    console.log('🔄 开始聚合数据...');

    for (const player of players) {
      const rank = this.parseRank(player);

      for (const match of (player.matches || [])) {
        const mapId = this.normalizeMapName(match.map);
        if (!mapId) continue;

        this.totalMatches++;

        // 初始化地图统计
        if (!this.mapStats[mapId]) {
          this.mapStats[mapId] = {};
        }
        if (!this.globalMapStats[mapId]) {
          this.globalMapStats[mapId] = { totalRounds: 0, totalMatches: 0 };
        }
        this.globalMapStats[mapId].totalMatches++;

        for (const round of (match.rounds || [])) {
          const operatorId = this.normalizeOperatorName(round.operator);
          if (!operatorId) continue;

          this.totalRounds++;
          this.globalMapStats[mapId].totalRounds++;

          // 初始化 地图→干员 统计
          if (!this.mapStats[mapId][operatorId]) {
            this.mapStats[mapId][operatorId] = {};
          }

          // 初始化 地图→干员→段位 统计
          if (!this.mapStats[mapId][operatorId][rank]) {
            this.mapStats[mapId][operatorId][rank] = {
              picks: 0,
              wins: 0,
              losses: 0,
              kills: 0,
              deaths: 0,
              assists: 0,
              side: { ATK: 0, DEF: 0 }
            };
          }

          const stat = this.mapStats[mapId][operatorId][rank];
          stat.picks++;
          if (round.won === true) stat.wins++;
          if (round.won === false) stat.losses++;
          stat.kills += round.kills || 0;
          stat.deaths += round.deaths || 0;
          stat.assists += round.assists || 0;
          if (round.side === 'ATK') stat.side.ATK++;
          if (round.side === 'DEF') stat.side.DEF++;

          // 全局干员统计
          if (!this.globalOperatorStats[operatorId]) {
            this.globalOperatorStats[operatorId] = { totalPicks: 0, totalWins: 0 };
          }
          this.globalOperatorStats[operatorId].totalPicks++;
          if (round.won === true) this.globalOperatorStats[operatorId].totalWins++;

          // 处理队友干员数据（如果有）
          for (const tm of (round.teammates || [])) {
            const tmOpId = this.normalizeOperatorName(tm.operator);
            if (!tmOpId) continue;

            if (!this.mapStats[mapId][tmOpId]) {
              this.mapStats[mapId][tmOpId] = {};
            }
            if (!this.mapStats[mapId][tmOpId][rank]) {
              this.mapStats[mapId][tmOpId][rank] = {
                picks: 0, wins: 0, losses: 0,
                kills: 0, deaths: 0, assists: 0,
                side: { ATK: 0, DEF: 0 }
              };
            }
            this.mapStats[mapId][tmOpId][rank].picks++;
            if (round.won === true) this.mapStats[mapId][tmOpId][rank].wins++;
            if (round.won === false) this.mapStats[mapId][tmOpId][rank].losses++;
          }
        }
      }
    }

    console.log(`✅ 聚合完成: ${this.totalMatches} 场对局, ${this.totalRounds} 回合`);
    console.log(`📊 覆盖 ${Object.keys(this.mapStats).length} 张地图, ${Object.keys(this.globalOperatorStats).length} 个干员`);
  }

  /**
   * 生成每张地图的干员排名
   */
  generateMapOperatorRankings() {
    const rankings = {};

    for (const [mapId, operators] of Object.entries(this.mapStats)) {
      rankings[mapId] = {
        attackers: [],
        defenders: [],
        overall: []
      };

      for (const [opId, ranks] of Object.entries(operators)) {
        // 合并所有段位的数据
        let totalPicks = 0, totalWins = 0, totalLosses = 0;
        let atkPicks = 0, defPicks = 0;

        for (const [rankName, stat] of Object.entries(ranks)) {
          totalPicks += stat.picks;
          totalWins += stat.wins;
          totalLosses += stat.losses;
          atkPicks += stat.side.ATK;
          defPicks += stat.side.DEF;
        }

        const entry = {
          operator: opId,
          picks: totalPicks,
          pickRate: this.globalMapStats[mapId] 
            ? (totalPicks / this.globalMapStats[mapId].totalRounds * 100).toFixed(2) + '%' 
            : '0%',
          winRate: totalPicks > 0 
            ? (totalWins / (totalWins + totalLosses) * 100).toFixed(2) + '%' 
            : 'N/A',
          wins: totalWins,
          losses: totalLosses,
          side: atkPicks > defPicks ? 'ATK' : 'DEF'
        };

        rankings[mapId].overall.push(entry);
        if (atkPicks > defPicks) {
          rankings[mapId].attackers.push(entry);
        } else {
          rankings[mapId].defenders.push(entry);
        }
      }

      // 按选取率排序
      rankings[mapId].attackers.sort((a, b) => b.picks - a.picks);
      rankings[mapId].defenders.sort((a, b) => b.picks - a.picks);
      rankings[mapId].overall.sort((a, b) => b.picks - a.picks);
    }

    return rankings;
  }

  /**
   * 生成按段位分组的统计
   */
  generateRankBreakdown() {
    const breakdown = {};

    for (const [mapId, operators] of Object.entries(this.mapStats)) {
      breakdown[mapId] = {};

      for (const [opId, ranks] of Object.entries(operators)) {
        for (const [rankName, stat] of Object.entries(ranks)) {
          if (!breakdown[mapId][rankName]) {
            breakdown[mapId][rankName] = [];
          }

          breakdown[mapId][rankName].push({
            operator: opId,
            picks: stat.picks,
            winRate: stat.picks > 0 
              ? (stat.wins / (stat.wins + stat.losses) * 100).toFixed(2) + '%' 
              : 'N/A',
            kd: stat.deaths > 0 
              ? (stat.kills / stat.deaths).toFixed(2) 
              : stat.kills.toString(),
            side: stat.side.ATK > stat.side.DEF ? 'ATK' : 'DEF'
          });
        }
      }

      // 每个段位内按选取数排序
      for (const rankName of Object.keys(breakdown[mapId])) {
        breakdown[mapId][rankName].sort((a, b) => b.picks - a.picks);
      }
    }

    return breakdown;
  }

  /**
   * 导出为 JS 模块（可供前端页面使用）
   */
  exportAsJSModule(outputPath) {
    const rankings = this.generateMapOperatorRankings();
    const rankBreakdown = this.generateRankBreakdown();

    const output = `/**
 * Rainbow Six Siege - 地图 × 干员 统计数据
 * 
 * 数据来源: R6 Tracker Network (r6.tracker.network) 玩家对局数据
 * 生成时间: ${new Date().toISOString()}
 * 样本量: ${this.totalMatches} 场对局, ${this.totalRounds} 回合
 * 覆盖地图: ${Object.keys(this.mapStats).length} 张
 * 覆盖干员: ${Object.keys(this.globalOperatorStats).length} 个
 * 
 * 数据说明:
 * - pickRate: 该干员在该地图上被选取的频率（基于总回合数）
 * - winRate: 选取该干员时的回合胜率
 * - 数据按段位分层，可查看不同段位的meta差异
 */

const OPERATOR_MAP_STATS = {
  metadata: {
    generatedAt: "${new Date().toISOString()}",
    totalMatches: ${this.totalMatches},
    totalRounds: ${this.totalRounds},
    mapsCount: ${Object.keys(this.mapStats).length},
    operatorsCount: ${Object.keys(this.globalOperatorStats).length},
    source: "R6 Tracker Network (r6.tracker.network)"
  },

  /**
   * 每张地图的干员选取排名（所有段位合计）
   * 结构: rankings[mapId].attackers/defenders/overall = [{ operator, picks, pickRate, winRate, ... }]
   */
  rankings: ${JSON.stringify(rankings, null, 2)},

  /**
   * 按段位分组的详细统计
   * 结构: rankBreakdown[mapId][rankTier] = [{ operator, picks, winRate, kd, side }]
   */
  rankBreakdown: ${JSON.stringify(rankBreakdown, null, 2)},

  /**
   * 原始聚合数据
   * 结构: rawStats[mapId][operatorId][rankTier] = { picks, wins, losses, kills, deaths, assists, side }
   */
  rawStats: ${JSON.stringify(this.mapStats, null, 2)}
};

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { OPERATOR_MAP_STATS };
}
`;

    fs.writeFileSync(outputPath, output, 'utf-8');
    console.log(`📦 数据已导出到: ${outputPath}`);
  }

  /**
   * 导出纯 JSON 统计文件
   */
  exportAsJSON() {
    const rankings = this.generateMapOperatorRankings();
    const rankBreakdown = this.generateRankBreakdown();

    const statsPath = path.join(CONFIG.output.statsDir, `operator_map_stats_${Date.now()}.json`);
    fs.writeFileSync(statsPath, JSON.stringify({
      metadata: {
        generatedAt: new Date().toISOString(),
        totalMatches: this.totalMatches,
        totalRounds: this.totalRounds
      },
      rankings,
      rankBreakdown,
      rawStats: this.mapStats,
      globalOperatorStats: this.globalOperatorStats,
      globalMapStats: this.globalMapStats
    }, null, 2));

    console.log(`📊 JSON 统计数据已保存: ${statsPath}`);
  }

  /**
   * 打印摘要报告
   */
  printSummary() {
    console.log('\n========================================');
    console.log('📊 数据聚合摘要报告');
    console.log('========================================');
    console.log(`总对局数: ${this.totalMatches}`);
    console.log(`总回合数: ${this.totalRounds}`);
    console.log(`覆盖地图: ${Object.keys(this.mapStats).length}`);
    console.log(`覆盖干员: ${Object.keys(this.globalOperatorStats).length}`);
    console.log('');

    // 每张地图的 Top 5 干员
    const rankings = this.generateMapOperatorRankings();
    for (const [mapId, data] of Object.entries(rankings)) {
      console.log(`\n📍 ${mapId}`);
      console.log('  进攻方 Top 5:');
      data.attackers.slice(0, 5).forEach((op, i) => {
        console.log(`    ${i + 1}. ${op.operator} (选取${op.picks}次, 选取率${op.pickRate}, 胜率${op.winRate})`);
      });
      console.log('  防守方 Top 5:');
      data.defenders.slice(0, 5).forEach((op, i) => {
        console.log(`    ${i + 1}. ${op.operator} (选取${op.picks}次, 选取率${op.pickRate}, 胜率${op.winRate})`);
      });
    }

    if (this.errors.length > 0) {
      console.log(`\n⚠️ 处理过程中的错误 (${this.errors.length}个):`);
      this.errors.forEach(e => console.log(`  - ${e}`));
    }

    console.log('\n========================================\n');
  }

  /**
   * 主执行入口
   */
  run() {
    console.log('🚀 R6 数据聚合器启动');
    
    // 1. 加载原始数据
    const players = this.loadRawData();
    
    if (players.length === 0) {
      console.error('❌ 没有找到任何玩家数据');
      return;
    }

    // 2. 聚合数据
    this.aggregate(players);

    // 3. 打印摘要
    this.printSummary();

    // 4. 导出
    this.exportAsJSON();

    // 5. 如果指定了 --output 参数，同时导出为 JS 模块
    const outputArg = process.argv.indexOf('--output');
    if (outputArg !== -1 && process.argv[outputArg + 1]) {
      const jsOutputPath = path.resolve(process.argv[outputArg + 1]);
      this.exportAsJSModule(jsOutputPath);
    } else {
      // 默认也导出 JS 模块
      const defaultJSPath = path.resolve(__dirname, '..', 'operator_map_stats.js');
      this.exportAsJSModule(defaultJSPath);
    }

    console.log('✅ 聚合完成！');
  }
}

// ==================== 运行 ====================

const aggregator = new DataAggregator();
aggregator.run();

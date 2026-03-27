/**
 * Ubisoft API 端点可用性测试脚本
 * 
 * 逐个测试各端点，输出详细的可用性报告。
 * 
 * 用法（PowerShell）：
 *   $env:UBI_EMAIL = "your_email"
 *   $env:UBI_PASSWORD = "your_password"
 *   node data/scraper/test-api.js
 */

const { UbisoftAuth, R6UbisoftClient, UBISOFT_API } = require('./ubisoft-api');

// ==================== 配色与格式 ====================

const PASS = '✅';
const FAIL = '❌';
const WARN = '⚠️';
const INFO = 'ℹ️';

function separator(title) {
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`  ${title}`);
  console.log('═'.repeat(60));
}

function printJson(obj, maxLength = 800) {
  const str = JSON.stringify(obj, null, 2);
  if (str.length > maxLength) {
    console.log(str.substring(0, maxLength) + '\n  ... (truncated)');
  } else {
    console.log(str);
  }
}

// ==================== 测试逻辑 ====================

async function runTests() {
  const email = process.env.UBI_EMAIL;
  const password = process.env.UBI_PASSWORD;

  if (!email || !password) {
    console.log(`
请先设置环境变量（PowerShell）：

  $env:UBI_EMAIL = "your_email@example.com"
  $env:UBI_PASSWORD = "your_password"
  node data/scraper/test-api.js
    `);
    process.exit(1);
  }

  const results = [];

  // ---------- 1. 认证测试 ----------
  separator('1. 认证测试 (Authentication)');
  const auth = new UbisoftAuth(email, password);
  let ticket = null;

  try {
    ticket = await auth.getTicket();
    console.log(`${PASS} 认证成功！`);
    console.log(`   Ticket: ${ticket.substring(0, 30)}...`);
    console.log(`   SessionId: ${auth.sessionId}`);
    console.log(`   Expiration: ${auth.expiration}`);
    results.push({ test: 'Authentication', status: 'PASS' });
  } catch (e) {
    console.log(`${FAIL} 认证失败: ${e.message}`);
    results.push({ test: 'Authentication', status: 'FAIL', error: e.message });
    console.log('\n无法继续后续测试。请检查邮箱和密码是否正确，以及 2FA 是否已关闭。');
    printReport(results);
    return;
  }

  const client = new R6UbisoftClient(auth, 'pc');

  // ---------- 2. 玩家搜索测试 ----------
  separator('2. 玩家搜索测试 (Player Search)');
  const testUsernames = ['Beaulo.TSM', 'Pengu', 'Canadian'];
  let foundProfileId = null;

  for (const username of testUsernames) {
    try {
      console.log(`\n  搜索: "${username}"`);
      const players = await client.searchPlayer(username);

      if (Array.isArray(players) && players.length > 0) {
        const p = players[0];
        foundProfileId = p.profileId;
        console.log(`  ${PASS} 找到 ${players.length} 个结果`);
        console.log(`     名称: ${p.nameOnPlatform}`);
        console.log(`     ProfileId: ${p.profileId}`);
        console.log(`     Platform: ${p.platformType}`);
        results.push({ test: `Player Search (${username})`, status: 'PASS', profileId: foundProfileId });
        break; // 找到一个就够了
      } else if (players && players.errorCode) {
        console.log(`  ${FAIL} API 返回错误: code=${players.errorCode}, message=${players.message || 'N/A'}`);
        results.push({ test: `Player Search (${username})`, status: 'FAIL', error: `errorCode: ${players.errorCode}` });
      } else {
        console.log(`  ${WARN} 未找到结果`);
        console.log(`  响应:`, JSON.stringify(players).substring(0, 200));
        results.push({ test: `Player Search (${username})`, status: 'WARN', note: 'No results' });
      }
    } catch (e) {
      console.log(`  ${FAIL} 搜索失败: ${e.message}`);
      results.push({ test: `Player Search (${username})`, status: 'FAIL', error: e.message });
    }

    await sleep(1000);
  }

  if (!foundProfileId) {
    console.log(`\n${WARN} 未能找到任何玩家 profileId，后续测试可能受限`);
    // 使用一个已知的 profileId 继续测试
    foundProfileId = '621be942-39b4-4f5e-8ef2-f1f5cfe28258'; // Beaulo 的已知 ID
    console.log(`${INFO} 使用备用 profileId: ${foundProfileId}`);
  }

  // ---------- 3. 玩家基础统计测试 ----------
  separator('3. 玩家基础统计 (Player Stats Summary)');
  try {
    const stats = await client.getPlayerStats(foundProfileId);
    if (stats && stats.results) {
      console.log(`${PASS} 基础统计获取成功`);
      printJson(stats);
      results.push({ test: 'Player Stats Summary', status: 'PASS' });
    } else if (stats && stats.errorCode) {
      console.log(`${FAIL} API 错误: code=${stats.errorCode}, message=${stats.message || 'N/A'}`);
      printJson(stats);
      results.push({ test: 'Player Stats Summary', status: 'FAIL', error: `errorCode: ${stats.errorCode}` });
    } else {
      console.log(`${WARN} 返回数据结构不确定:`);
      printJson(stats);
      results.push({ test: 'Player Stats Summary', status: 'WARN', note: 'Unexpected structure' });
    }
  } catch (e) {
    console.log(`${FAIL} 失败: ${e.message}`);
    results.push({ test: 'Player Stats Summary', status: 'FAIL', error: e.message });
  }

  await sleep(1000);

  // ---------- 4. 干员统计测试 ----------
  separator('4. 干员统计 (Operator Stats)');
  try {
    const opStats = await client.getOperatorStats(foundProfileId);
    if (opStats && opStats.results) {
      console.log(`${PASS} 干员统计获取成功`);
      printJson(opStats);
      results.push({ test: 'Operator Stats', status: 'PASS' });
    } else if (opStats && opStats.errorCode) {
      console.log(`${FAIL} API 错误: code=${opStats.errorCode}`);
      printJson(opStats);
      results.push({ test: 'Operator Stats', status: 'FAIL', error: `errorCode: ${opStats.errorCode}` });
    } else {
      console.log(`${WARN} 返回数据结构不确定:`);
      printJson(opStats);
      results.push({ test: 'Operator Stats', status: 'WARN' });
    }
  } catch (e) {
    console.log(`${FAIL} 失败: ${e.message}`);
    results.push({ test: 'Operator Stats', status: 'FAIL', error: e.message });
  }

  await sleep(1000);

  // ---------- 5. 段位数据测试 (v1) ----------
  separator('5. 段位数据 v1 (Seasonal Rank)');
  try {
    const rank = await client.getPlayerRank(foundProfileId, -1);
    if (rank && rank.players) {
      console.log(`${PASS} 段位数据获取成功`);
      printJson(rank);
      results.push({ test: 'Seasonal Rank v1', status: 'PASS' });
    } else if (rank && rank.errorCode) {
      console.log(`${FAIL} API 错误: code=${rank.errorCode}`);
      printJson(rank);
      results.push({ test: 'Seasonal Rank v1', status: 'FAIL', error: `errorCode: ${rank.errorCode}` });
    } else {
      console.log(`${WARN} 返回数据结构不确定:`);
      printJson(rank);
      results.push({ test: 'Seasonal Rank v1', status: 'WARN' });
    }
  } catch (e) {
    console.log(`${FAIL} 失败: ${e.message}`);
    results.push({ test: 'Seasonal Rank v1', status: 'FAIL', error: e.message });
  }

  await sleep(1000);

  // ---------- 6. 段位数据测试 (v2) ----------
  separator('6. 段位数据 v2 (Seasonal V2)');
  try {
    const rankV2 = await client.getSeasonalV2(foundProfileId);
    if (rankV2 && (rankV2.platform_families_full_profiles || rankV2.season_statistics)) {
      console.log(`${PASS} V2 段位数据获取成功`);
      printJson(rankV2);
      results.push({ test: 'Seasonal Rank v2', status: 'PASS' });
    } else if (rankV2 && rankV2.errorCode) {
      console.log(`${FAIL} API 错误: code=${rankV2.errorCode}`);
      printJson(rankV2);
      results.push({ test: 'Seasonal Rank v2', status: 'FAIL', error: `errorCode: ${rankV2.errorCode}` });
    } else {
      console.log(`${WARN} 返回数据结构不确定:`);
      printJson(rankV2);
      results.push({ test: 'Seasonal Rank v2', status: 'WARN' });
    }
  } catch (e) {
    console.log(`${FAIL} 失败: ${e.message}`);
    results.push({ test: 'Seasonal Rank v2', status: 'FAIL', error: e.message });
  }

  await sleep(1000);

  // ---------- 7. 比赛历史测试 ----------
  separator('7. 比赛历史 (Match History) ⭐ 关键端点');
  try {
    const matches = await client.getMatchHistory(foundProfileId, 5, 0);
    if (matches && (Array.isArray(matches) || matches.matches || matches.games)) {
      console.log(`${PASS} 比赛历史获取成功！`);
      printJson(matches);
      results.push({ test: 'Match History', status: 'PASS' });
    } else if (matches && matches.errorCode) {
      console.log(`${FAIL} API 错误: code=${matches.errorCode}, message=${matches.message || 'N/A'}`);
      printJson(matches);
      results.push({ test: 'Match History', status: 'FAIL', error: `errorCode: ${matches.errorCode}` });
    } else {
      console.log(`${WARN} 返回数据结构不确定:`);
      printJson(matches);
      results.push({ test: 'Match History', status: 'WARN' });
    }
  } catch (e) {
    console.log(`${FAIL} 失败: ${e.message}`);
    results.push({ test: 'Match History', status: 'FAIL', error: e.message });
  }

  await sleep(1000);

  // ---------- 8. 排行榜测试 ----------
  separator('8. 排行榜 (Leaderboard)');
  try {
    const lb = await client.getLeaderboard(-1, 5, 0);
    if (lb && (lb.players || Array.isArray(lb))) {
      console.log(`${PASS} 排行榜获取成功`);
      printJson(lb);
      results.push({ test: 'Leaderboard', status: 'PASS' });
    } else if (lb && lb.errorCode) {
      console.log(`${FAIL} API 错误: code=${lb.errorCode}`);
      printJson(lb);
      results.push({ test: 'Leaderboard', status: 'FAIL', error: `errorCode: ${lb.errorCode}` });
    } else {
      console.log(`${WARN} 返回数据结构不确定:`);
      printJson(lb);
      results.push({ test: 'Leaderboard', status: 'WARN' });
    }
  } catch (e) {
    console.log(`${FAIL} 失败: ${e.message}`);
    results.push({ test: 'Leaderboard', status: 'FAIL', error: e.message });
  }

  await sleep(1000);

  // ---------- 9. 额外端点探测 ----------
  separator('9. 额外端点探测');

  // 9a. 尝试新版 stats API（可能有地图/干员 per-match 数据）
  const extraEndpoints = [
    {
      name: 'Game Metadata (title)',
      url: `https://public-ubiservices.ubi.com/v1/profiles/${foundProfileId}/title/r6s`,
    },
    {
      name: 'Match Replay (V2 alternative)',
      url: `https://public-ubiservices.ubi.com/v2/spaces/${UBISOFT_API.spaceId.pc}/matches?profile_id=${foundProfileId}&limit=5`,
    },
    {
      name: 'Player Progress',
      url: `https://public-ubiservices.ubi.com/v1/spaces/${UBISOFT_API.spaceId.pc}/sandboxes/${UBISOFT_API.sandboxId.pc}/r6playerprofile/playerprofile/progressions?profile_ids=${foundProfileId}`,
    },
    {
      name: 'Current Season Info',
      url: `https://public-ubiservices.ubi.com/v1/spaces/${UBISOFT_API.spaceId.pc}/sandboxes/${UBISOFT_API.sandboxId.pc}/r6karma/seasons`,
    },
  ];

  for (const ep of extraEndpoints) {
    try {
      console.log(`\n  测试: ${ep.name}`);
      console.log(`  URL: ${ep.url.substring(0, 100)}...`);
      const result = await client.authenticatedRequest(ep.url);

      if (result && result.errorCode) {
        console.log(`  ${FAIL} errorCode: ${result.errorCode}`);
        results.push({ test: ep.name, status: 'FAIL', error: `errorCode: ${result.errorCode}` });
      } else {
        console.log(`  ${PASS} 有数据返回:`);
        printJson(result, 400);
        results.push({ test: ep.name, status: 'PASS' });
      }
    } catch (e) {
      console.log(`  ${FAIL} ${e.message}`);
      results.push({ test: ep.name, status: 'FAIL', error: e.message });
    }
    await sleep(800);
  }

  // ---------- 最终报告 ----------
  printReport(results);
}

function printReport(results) {
  separator('📋 端点可用性报告');
  console.log('');

  const passed = results.filter(r => r.status === 'PASS');
  const failed = results.filter(r => r.status === 'FAIL');
  const warned = results.filter(r => r.status === 'WARN');

  for (const r of results) {
    const icon = r.status === 'PASS' ? PASS : r.status === 'FAIL' ? FAIL : WARN;
    const extra = r.error ? ` (${r.error})` : r.note ? ` (${r.note})` : '';
    console.log(`  ${icon} ${r.test}${extra}`);
  }

  console.log(`\n  总计: ${results.length} 个测试`);
  console.log(`  ${PASS} 通过: ${passed.length}`);
  console.log(`  ${FAIL} 失败: ${failed.length}`);
  console.log(`  ${WARN} 警告: ${warned.length}`);

  console.log('\n' + '═'.repeat(60));

  if (passed.length > 0) {
    console.log('\n💡 建议下一步:');
    if (passed.some(r => r.test === 'Match History')) {
      console.log('  🎉 Match History 端点可用！可以直接获取对局数据。');
    }
    if (passed.some(r => r.test.includes('Leaderboard'))) {
      console.log('  📊 排行榜可用，可以从排行榜获取高段位玩家列表。');
    }
    if (passed.some(r => r.test.includes('Operator'))) {
      console.log('  🎮 干员统计可用，可以获取玩家的干员使用数据。');
    }
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// 运行测试
runTests().catch(err => {
  console.error('测试脚本出错:', err);
  process.exit(1);
});

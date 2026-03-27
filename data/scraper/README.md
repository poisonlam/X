# R6 数据抓取框架（多路径方案）

## 核心发现

> **R6 Tracker 等第三方网站的数据都来自 Ubisoft 官方 API。**
> 直接调用上游 API 是更根本的解决方案。

## 数据获取路径（按优先级）

### 🏆 路径1: Ubisoft 官方 API（推荐首选）

**原理**: R6 Tracker / Stats.CC / R6Tab 等网站背后都是调用 Ubisoft 的 `public-ubiservices.ubi.com` API。
我们直接调用源头 API，无需和 Cloudflare 斗智斗勇。

**认证流程**:
```
POST https://public-ubiservices.ubi.com/v3/profiles/sessions
  → 获取 ticket + sessionId
    → 携带 ticket 访问所有数据端点
```

**可用端点**:
- 玩家搜索 (`/v3/profiles`)
- 玩家统计 (`/v1/spaces/{spaceId}/sandboxes/.../playerstats2/statistics`)
- 干员统计（生涯累计 KD/胜率/时长）
- 段位数据（当前 + 历史赛季）
- 排行榜（分页获取各段位玩家）
- 比赛历史（需验证端点可用性）

**文件**: `ubisoft-api.js`

**使用**:
```bash
# 设置凭据
$env:UBI_EMAIL = "your_email@example.com"
$env:UBI_PASSWORD = "your_password"

# 测试连通性
node ubisoft-api.js --test

# 搜索玩家
node ubisoft-api.js --search Beaulo.TSM

# 开始收集
node ubisoft-api.js --collect
```

### 📊 路径2: GRID R6 Data Portal（官方电竞数据）

Ubisoft 和 GRID 合作推出的**官方电竞数据门户**。
- 免费的 "Non-Commercial Access" 层级可供学生/独立开发者申请
- 包含职业赛事的完整对局数据
- 标准化 API + SQL Playground

**申请**: https://grid.gg/get-access/

### 🕷️ 路径3: Playwright 抓取 R6 Tracker（兜底方案）

如果 Ubisoft API 的比赛历史端点不可用，回退到浏览器自动化方案。

**文件**: `scraper.js`（已有实现）

### 🎮 路径4: r6-dissect 本地回放解析（补充）

解析本地保存的 `.rec` 回放文件，提取最详细的回合级数据。
- 包含每回合每位玩家的干员选取
- 包含击杀事件时间线
- 包含点位信息

**项目**: https://github.com/stnokott/r6-dissect

## 数据采集流程

```
                         ┌─────────────────────┐
                         │  Ubisoft 官方 API    │
                         │  (数据源头)           │
                         └─────────┬───────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
    ┌───────▼───────┐    ┌────────▼────────┐    ┌───────▼───────┐
    │  路径1: 直连    │    │  R6 Tracker     │    │  Stats.CC     │
    │  ubisoft-api   │    │  (第三方展示)    │    │  (第三方展示)  │
    │  ⭐ 推荐       │    └────────┬────────┘    └───────────────┘
    └───────┬───────┘             │
            │             ┌───────▼───────┐
            │             │  路径3: 抓取   │
            │             │  scraper.js   │
            │             └───────┬───────┘
            │                     │
    ┌───────▼─────────────────────▼───────┐
    │          数据聚合 aggregator.js       │
    │   → 地图 × 干员 × 段位 统计          │
    └───────────────────┬─────────────────┘
                        │
              ┌─────────▼─────────┐     ┌─────────────────┐
              │ operator_map_stats │ ◄── │ GRID Portal     │
              │ (最终输出)         │     │ (职业赛事补充)   │
              └───────────────────┘     └─────────────────┘
```

## 文件结构
```
data/scraper/
├── README.md              # 本文件（方案总览）
├── package.json           # 依赖配置
├── strategy.js            # 多路径策略分析器
│
├── ubisoft-api.js         # ⭐ 路径1: Ubisoft 官方 API 直连
├── config.js              # 配置文件
├── scraper.js             # 路径3: Playwright 浏览器抓取
├── aggregator.js          # 数据聚合器
│
└── output/                # 输出目录
    ├── raw/               # 原始抓取数据
    ├── stats/             # 聚合统计数据
    └── progress_api.json  # API 方案进度文件
```

## 快速开始

```bash
cd data/scraper
npm install

# 查看策略分析报告
node strategy.js

# 方案1: 测试 Ubisoft API（推荐先试这个）
$env:UBI_EMAIL = "your_email"
$env:UBI_PASSWORD = "your_password"
node ubisoft-api.js --test

# 方案3: 如果 API 不可用，回退到 Playwright
npx playwright install chromium
node scraper.js --test
```

## 实施建议

1. **立即可做**: 创建 Ubisoft 小号 → 运行 `--test` 验证 API 端点
2. **同步进行**: 申请 GRID Portal 的 Non-Commercial Access
3. **兜底方案**: Playwright 抓取 R6 Tracker
4. **融合数据**: 多个来源的数据通过 aggregator.js 统一聚合

## ⚠️ 注意事项

- Ubisoft API 端点为非公开接口，可能随游戏更新变化
- 请合理控制请求频率，避免触发速率限制
- 建议使用专用小号进行 API 调用，不要使用主账号
- 数据仅用于个人学习和研究目的

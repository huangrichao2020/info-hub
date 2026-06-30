---
title: "info-hub 集成方案"
source: knowhub/trading-review/methodology/infohub-integration.md
tags: [methodology, trading, serenity, prism]
created: 2026-06-30
auto_synced: true
---

# Info-Hub × Serenity/Prism 集成方案

> 怎么把"卡脖子选股框架"和"[[三棱镜三视角框架]]分析"接到 info-hub 的交易系统里

---

## 1. 现状摸底

### Info-Hub 已有接口（trading router）

| 接口 | 功能 |
|---|---|
| `GET /api/trading/leaders` | 主线龙头挖掘（主线 × top N 板块 × top K 个股） |
| `GET /api/trading/sector-leaders/{sector_code}` | 单板块龙头 |
| `GET /api/trading/screen` | 筛选 |
| `GET /api/trading/signal` | 信号分析（住相五维 + 金融三级表 + 执念六阶段 + 确信度） |
| `GET /api/trading/technical/{symbol}` | 单股技术分析（量价 ATR） |
| `GET /api/trading/stock/{code}` | 单股详情 |
| `GET /api/trading/snapshot` | 大盘快照 |
| `GET /api/trading/positions` | 持仓管理 |
| `GET /api/trading/watchlist` | 自选股 |
| `POST /api/trading/backtest` | 回测 |

### 我已经吃进去的两个框架

| 框架 | 在 info-hub 里可以做什么 |
|---|---|
| **Serenity 卡脖子**（单视角） | 给 `leaders` 返回的主线龙头加 "[[卡脖子定位]]" 标签 |
| **Prism [[三棱镜三视角框架]]**（三视角） | 给单股 (`stock/{code}`) 返回 "三视角联合分析" |

---

## 2. 推荐集成方式

### 集成点 1：`/api/trading/leaders` 加 `choke_point` 字段

**改造方式**（前端透明 / 后端加字段）：

```python
# routers/trading.py 伪代码
@router.get("/leaders")
async def get_main_line_leaders():
    # 1. 先按现有逻辑拿主线龙头
    leaders = fetch_main_line_leaders(...)
    
    # 2. 对每只龙头股调用 Serenity 分析
    for stock in leaders:
        choke_data = analyze_choke_point(stock.code)
        stock['choke_point'] = {
            "supply_chain_position": choke_data['position'],
            "choke_score": choke_data['score'],
            "supply_demand_gap": choke_data['gap'],
            "replacement_difficulty": choke_data['replacement'],
            "big_capital_signal": choke_data['capital'],
            "elimination_rules_passed": choke_data['rules_passed'],
        }
    
    return leaders
```

**前端展示**：在龙头股卡片上增加一个 `🔥 卡脖子评分` 标签 + 弹窗详情。

### 集成点 2：`/api/trading/stock/{code}` 加 `three_lens_analysis` 字段

```python
@router.get("/stock/{code}")
async def get_stock(code: str):
    # 1. 原有逻辑
    stock = fetch_stock_detail(code)
    
    # 2. 调用[[三棱镜三视角框架]]分析
    three_lens = run_three_lens_analysis(code)
    stock['three_lens'] = {
        "daoshi": {
            "macro_status": "逆风/顺风/等待",
            "fed_cycle": "...",
            "liquidity": "...",
            "geo_risk": "...",
            "market_sentiment": "...",
        },
        "seri": {
            "choke_score": "X/10",
            "supply_chain_position": "...",
            "supply_demand_gap": "...",
            "big_capital_signal": "...",
            "judgment": "卡脖子逻辑成立/不成立",
        },
        "cat": {
            "market_day_type": "趋势/区间/反转/矛盾/事件",
            "breakout_real": "真突破/假突破/待确认",
            "entry_zone": "...",
            "stop_loss": "买入价 - 1.5×ATR",
            "fundamentals_flags": "X/12",
            "judgment": "进/等/不",
        }
    }
    
    return stock
```

### 集成点 3：新增 `/api/trading/three-lens/{code}` 独立端点

直接做一个新的独立 API，专门返回[[三棱镜三视角框架]]分析结果。

---

## 3. 实现路径（不需要现在做）

### Phase 1：标记框架（已完成）
- ✅ 框架已经沉淀到 knowhub + agent skills
- ✅ 触发短语已经写进 memory
- ✅ 三个 persona 的 prompt 模板已经准备好

### Phase 2：单股分析脚本（待做）
- 写一个 `services/three_lens_analyzer.py`，接收 stock_code 返回三视角分析
- 输入：股票代码
- 输出：JSON 格式的三视角结果
- 数据源：info-hub 现有数据库 + akshare + 公开新闻

### Phase 3：前端集成（待做）
- 在 `leaders` 卡片加 "🔥 卡脖子" 标签
- 在 `stock/{code}` 详情页加 "[[三棱镜三视角框架]]分析" tab
- 三人辩论模式 UI（每人一个气泡，可辩论）

### Phase 4：批量自动化（待做）
- 每周 outlook 自动跑[[三棱镜三视角框架]]分析每个推荐方向
- 板块轮动信号自动触发 Serenity 重新评估

---

## 4. 最小可用版本（MVP）

**今天就能用的方案**：

```python
# 在 routers/trading.py 末尾加一段
@router.get("/three-lens/{code}")
async def get_three_lens(code: str):
    """[[三棱镜三视角框架]]单股分析（调用 mavis 的 agent framework）"""
    from services.three_lens_analyzer import analyze
    return analyze(code)
```

+ 新建 `services/three_lens_analyzer.py`：
```python
import json
import subprocess

def analyze(stock_code: str) -> dict:
    """调用 mavis agent 的 three-lens skill"""
    # 简化版：直接读 prompt 模板 + 拼装 + 调用 mavis
    prompt = build_three_lens_prompt(stock_code)
    result = subprocess.run(
        ["mavis", "skill", "run", "fate-skill", prompt],
        capture_output=True, text=True
    )
    return parse_three_lens_output(result.stdout)
```

---

## 5. 关键决策点（需要你确认）

| 问题 | 选项 |
|---|---|
| **集成深度** | A. 仅后端加字段 / B. 前端完整 UI / C. 完全自动化 |
| **数据源** | A. 仅用 info-hub 现有数据 / B. 混合（akshare + 新闻）/ C. AI 直接调 |
| **调用方式** | A. 同步实时分析（慢）/ B. 异步预生成（快）/ C. 手动触发 |
| **存储** | A. 实时计算不存 / B. 分析结果存数据库 / C. 只缓存最近 N 次 |

---

## 6. 不集成也能用的方式

**最简单的方法**——直接在聊天里说：
```
"用 Seri 视角分析[[兆易创新 603986]]"
"三人合议：[[兆易创新 603986]]现在能买吗"
"Cat：兆易的技术位怎么看"
```

Mavis 会自动调用 fate-skill 输出完整分析。**不需要改 info-hub 代码。**

适合场景：
- 临时研究
- 不需要持久化
- 想看完整的三人对话形式

---

## 7. 引用

- 框架方法论：`~/.mavis/knowledge/knowhub/domains/trading-review/methodology/`
- Skill 位置：`~/.mavis/agents/mavis/skills/fate-skill/` 和 `~/.mavis/agents/mavis/skills/serenity-stock-choke/`
- info-hub 路由：`~/Desktop/info-hub/backend/routers/trading.py`
- 整理日期：2026-06-29
---
name: fupanhezi-cache
description: 复盘盒子（fupanhezi.com）涨停数据缓存与读取。每日 16:10 自动增量更新 ~/.hermes/data/fupanhezi/fupanhezi.db 缓存；可读取指定日期的涨停池（含连板数、封板资金、涨停原因）。用于住相评估的"涨停梯队"判断、住相信号检查、题材主线确认。触发词：涨停池、涨停梯队、复盘盒子、fupanhezi、zt pool、连板数、封板资金
---

# 复盘盒子（fupanhezi）涨停数据缓存与读取

## 概述

涨停数据是判断"主线是否成立 / 住相是否亮灯"的核心证据。本 skill 封装了 `fupanhezi.com` 官网的涨停池 API，提供**网络抓取 + 本地 SQLite 缓存**的完整流程。

**架构演变**：2026-07-01 起，缓存逻辑从 GenericAgent 拆出到 `info-hub` 项目独立模块。原 GA agent 及其 3 个 LaunchAgent 已废弃。

## 文件位置

| 角色 | 路径 |
|---|---|
| 数据采集模块 | `~/Desktop/info-hub/fupanhezi.py` |
| SQLite 缓存 | `~/.hermes/data/fupanhezi/fupanhezi.db` |
| 数据源官网 | `https://box.fupanhezi.com/stock/v1/zt-table` |

## 核心能力

### 1. 增量更新缓存

```bash
cd ~/Desktop/info-hub
python3 fupanhezi.py update --days 21
```

输出示例：
```json
{
  "db_path": "/Users/tingchim2pro/.hermes/data/fupanhezi/fupanhezi.db",
  "updated": {
    "2026-06-30": 166,
    "2026-06-29": 117,
    "2026-06-26": 12
  },
  "total_records": 295
}
```

### 2. 读取某日涨停池

```bash
# 读指定日期
python3 fupanhezi.py read --date 2026-06-30

# 读最近一个交易日
python3 fupanhezi.py read --latest

# 只看前 10 条
python3 fupanhezi.py read --latest --limit 10
```

每条记录字段：
- `date` / `stockCode` / `stockName`
- `ztReson`（涨停原因 — 关键字段）
- `ztlbNum`（连板数 — 主线强度信号）
- `fbAmount`（封板资金 — 强度）
- `amo`（成交额）
- `closePe`（收盘 PE）
- `realHsRate`（换手率）
- `zbNum`（炸板次数）

### 3. 缓存状态

```bash
python3 fupanhezi.py info
```

输出：
```json
{
  "exists": true,
  "total_records": 2676,
  "earliest_date": "2026-05-25",
  "latest_date": "2026-06-30",
  "trade_days": 26
}
```

## 自动化

通过 `mavis cron` 注册每日 16:10（A股收盘后）自动更新：

```bash
mavis cron add fupanhezi-cache \
  --schedule "10 16 * * 1-5" \
  --prompt "cd /Users/tingchim2pro/Desktop/info-hub && python3 fupanhezi.py update --days 21"
```

**重要**：旧的 LaunchAgent `com.genericagent.fupanhezi-cache.plist` 已废弃，不要再用。

## 与住相框架的集成

涨停数据用于**住相五维评估**的几个关键判断：

| 住相信号 | 涨停池数据用法 |
|---|---|
| **龙头乏力** | 读 `--latest`，看最高连板数 ≥ 4 是否出现；没有连板 4+ = 龙头乏力 |
| **跟风先跑** | 读 `--latest`，看炸板数 `zbNum` 高的票数量（> 5 个 = 跟风先跑） |
| **扩散停止** | 读 `--latest --limit 20`，统计涨停原因 `ztReson` 唯一值数量；唯一值 ≤ 5 = 单一题材未扩散 |
| **资金转向** | 读近 3 天涨停池，对比题材轮动方向 |
| **情绪背离** | 涨停数 vs 沪指涨跌的相对关系 |

**示例**：

```python
import sys
sys.path.insert(0, "/Users/tingchim2pro/Desktop/info-hub")
import fupanhezi

records, date = fupanhezi.read_records(fupanhezi.DEFAULT_DB_PATH, None)
print(f"日期: {date} | 涨停数: {len(records)}")
print(f"最高连板: {records[0].get('ztlbNum')}（{records[0].get('stockName')}）")
reasons = set(r.get("ztReson") for r in records)
print(f"题材多样性: {len(reasons)} 个独立原因")
```

## API 调用规范

**端点**：`POST https://box.fupanhezi.com/stock/v1/zt-table`

**Headers**：
```
User-Agent: Mozilla/5.0
Referer: https://box.fupanhezi.com/
Origin: https://box.fupanhezi.com
Content-Type: application/json
```

**Payload**：
```json
{"beginDate": "2026-06-30", "endDate": "2026-06-30", "ztlbNum": 1}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "body": [[
      {
        "date": "2026-06-30",
        "stockCode": "002822",
        "stockName": "ST中装",
        "ztlbNum": 6,
        "fbAmount": 11615184,
        "amo": ...,
        "ztReson": "...",
        ...
      }
    ]]
  }
}
```

## 限流与重试

- 单次拉取 21 个交易日 = 21 次 POST
- 每次间隔 0.12 秒（避免被反爬）
- 抓取失败该日跳过（不影响其他日期）
- `requests.exceptions` / JSON 解析错误均自动吞掉

## 已知限制

1. **官网数据时滞**：凌晨拉到的是"前一交易日盘后"数据（不会预载当日盘后）
2. **周末/节假日无新数据**：周六/周日 A 股休市
3. **web 搜索结果去重**：同一事件多源时按 AGENTS.md 规则只取 1 个权威源

## Common Mistakes

- ❌ **不要用旧 LaunchAgent** `com.genericagent.fupanhezi-cache.plist`（已废弃）
- ❌ **不要直接调官网 API**（应走本模块的限流 + 缓存层）
- ❌ **不要忘了 `--days 21`**（默认 21，覆盖最近的 21 个自然日）
- ❌ **不要忘了先去 `cd ~/Desktop/info-hub`**（模块导入路径）

## 文件清单

- `~/Desktop/info-hub/fupanhezi.py` — 主模块（CLI + Python API）
- `~/.hermes/data/fupanhezi/fupanhezi.db` — SQLite 缓存
- `~/Desktop/info-hub/collect_market.py` — info-hub 其它行情采集（可与本模块配合）
- `~/Desktop/GenericAgent/_archive/launch-agents-2026-07-01/com.genericagent.fupanhezi-cache.plist` — 旧 plist 备份（仅参考）

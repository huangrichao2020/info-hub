#!/usr/bin/env python3
"""
Obsidian 同步器 · Mavis 输出 → Obsidian vault
============================================

参考 Karpathy LLM Wiki 范式:
- Raw 层: 原始素材 (只读不写)
- Wiki 层: AI 生成的 Markdown (摘要 + 概念 + wikilink)
- Schema 层: 配置 (本脚本)

核心功能:
1. daily-chance JSON → Obsidian markdown (含 wikilink)
2. 自动生成 _index.md 索引页
3. 自动生成/更新概念页
4. 双向链接: 标的/赛道/概念

输出目录结构:
  ~/Documents/Obsidian Vault/10-Wiki/Trading/每日机会/{date}.md
  ~/Documents/Obsidian Vault/10-Wiki/Trading/每日机会/_index.md
  ~/Documents/Obsidian Vault/10-Wiki/Concepts/{concept}.md
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# ===== 路径配置 =====
VAULT_ROOT = Path.home() / "Documents" / "Obsidian Vault"
WIKI_ROOT = VAULT_ROOT / "10-Wiki"
TRADING_DIR = WIKI_ROOT / "Trading"
DAILY_DIR = TRADING_DIR / "每日机会"
CONCEPTS_DIR = WIKI_ROOT / "Concepts"
META_FILE = VAULT_ROOT / "_meta.md"

# ===== 工具函数 =====
def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def fmt_pct(v: Optional[float]) -> str:
    if v is None: return "—"
    return f"{v:+.2f}%"


def fmt_amount(v: Optional[float]) -> str:
    if v is None: return "—"
    if abs(v) >= 1e8: return f"{v/1e8:.2f}亿"
    if abs(v) >= 1e4: return f"{v/1e4:.2f}万"
    return f"{v:.0f}"


# ===== daily-chance → Obsidian markdown =====
def render_daily_chance(data: Dict[str, Any]) -> str:
    """渲染每日机会报告为 Obsidian markdown"""
    d = data.get("data", data)
    date = d.get("date", datetime.now().strftime("%Y-%m-%d"))
    is_trade_time = d.get("is_trade_time", False)
    market = d.get("market", {})
    s_chances = d.get("S", [])
    a_chances = d.get("A", [])
    b_chances = d.get("B", [])
    stats = d.get("stats", {})

    # Frontmatter (YAML)
    frontmatter = f"""---
date: {date}
tags: [daily-chance, trading, 2026-Q2]
grade_summary: "S {stats.get('s_count', 0)} / A {stats.get('a_count', 0)} / B {stats.get('b_count', 0)}"
is_trade_time: {str(is_trade_time).lower()}
zt_count: {market.get('zt_count', 0)}
source: mavis-daily-chance
---

"""

    # 标题
    title = f"# 🎯 每日机会 · {date}\n\n"

    # 元信息
    trade_status = "🟢 交易时段" if is_trade_time else "⚫ 非交易时段"
    meta = f"""> **{trade_status}** · 标的池 {stats.get('total_pool', 29)} 只 ·
> 涨停数 **{market.get('zt_count', 0)}** ·
> S/A/B = **{stats.get('s_count', 0)}/{stats.get('a_count', 0)}/{stats.get('b_count', 0)}**

"""

    # 主线
    main_lines = market.get("main_lines", [])[:5]
    main_section = ""
    if main_lines:
        ml_names = " · ".join(
            ml.get("name", str(ml)) if isinstance(ml, dict) else str(ml)
            for ml in main_lines
        )
        main_section = f"## 📊 主线方向\n\n{ml_names}\n\n"

    # 热点板块
    hot_sectors = market.get("hot_sectors", [])[:5]
    sector_section = ""
    if hot_sectors:
        sector_section = "## 🔥 热点板块\n\n"
        for s in hot_sectors:
            sector_section += f"- {s}\n"
        sector_section += "\n"

    # S 级详细讲解
    s_section = "## 🅢 S 级 · 重点讲解\n\n"
    if s_chances:
        for stock in s_chances:
            signals_str = " · ".join(f"`{sig}`" for sig in stock.get("signals", [])) or "无"
            track_link = f"[[{stock['track']}]]" if stock['track'] else ""
            s_section += f"""### [[{stock['name']} {stock['code']}]] · S 级

| 项 | 值 |
|---|---|
| **代码** | `{stock['code']}` |
| **赛道** | {track_link} |
| **卡脖子评分** | `{stock['choke_score']}/10` |
| **卡脖子定位** | {stock['logic']} |

> **为什么是 S**：{stock['reason']}

> **信号**：{signals_str}

> ⚡ **操作建议**：{stock['action']}

"""
    else:
        s_section += "*今日无 S 级机会*\n\n"

    # A 级简略分析
    a_section = "## 🅐 A 级 · 简略分析\n\n"
    if a_chances:
        a_section += "| 代码 | 名称 | 赛道 | 卡脖子 | 原因 |\n"
        a_section += "|---|---|---|---|---|\n"
        for stock in a_chances:
            track_link = f"[[{stock['track']}]]"
            name_link = f"[[{stock['name']} {stock['code']}]]"
            a_section += f"| `{stock['code']}` | {name_link} | {track_link} | `{stock['choke_score']}/10` | {stock['reason']} |\n"
        a_section += "\n"
    else:
        a_section += "*今日无 A 级机会*\n\n"

    # B 级参考清单
    b_section = "## 🅑 B 级 · 参考清单\n\n"
    if b_chances:
        b_section += "| 代码 | 名称 | 赛道 | 卡脖子 | 信号 |\n"
        b_section += "|---|---|---|---|---|\n"
        for stock in b_chances:
            signals_str = " · ".join(stock.get("signals", [])) or "—"
            track_link = f"[[{stock['track']}]]"
            name_link = f"[[{stock['name']} {stock['code']}]]"
            b_section += f"| `{stock['code']}` | {name_link} | {track_link} | `{stock['choke_score']}/10` | {signals_str} |\n"
        b_section += "\n"
    else:
        b_section += "*今日无 B 级标的*\n\n"

    # 方法论声明
    methodology = """## 📐 方法论声明

本文基于 [[Serenity 卡脖子框架]] v2.0 + 当日市场信号综合评分。

- **🅢 S 级** = 卡脖子评分 ≥ 8.5 + 主线/板块联动 OR 卡脖子 ≥ 9.0 顶级标的
- **🅐 A 级** = 卡脖子评分 ≥ 7.5 + 板块强势
- **🅑 B 级** = 卡脖子 ≥ 6.5 · 仅作板块联动观察

数据源：`fetch_full_snapshot()` + `ChokePointAnalyzer`
⚠️ 不构成投资建议 · 实时行情 / PE / 资金数据需独立核实

---

**关联笔记**：
- [[Karpathy LLM Wiki 范式]]
- [[每日机会 MOC]]
- [[_index|总索引]]
"""

    return frontmatter + title + meta + main_section + sector_section + s_section + a_section + b_section + methodology


def update_index(history_dir: Path, current_date: str) -> str:
    """更新每日机会索引页"""
    # 扫描所有历史 daily-chance JSON
    entries = []
    for f in sorted(history_dir.glob("*/data.json")):
        try:
            with open(f) as fp:
                result = json.load(fp)
            d = result.get("data", result)
            entries.append({
                "date": d.get("date", f.parent.name),
                "is_trade_time": d.get("is_trade_time", False),
                "stats": d.get("stats", {}),
                "zt_count": d.get("market", {}).get("zt_count", 0),
                "s_count": len(d.get("S", [])),
                "a_count": len(d.get("A", [])),
                "b_count": len(d.get("B", [])),
            })
        except Exception:
            continue

    # 倒序（最新在前）
    entries.reverse()

    if not entries:
        return "# 每日机会\n\n*暂无历史记录*\n"

    frontmatter = "---\ntags: [moc, daily-chance, trading]\n---\n\n"
    title = "# 🗓️ 每日机会 MOC\n\n"
    desc = "> **Map of Content** · 每日 S/A/B 机会扫描历史归档 · 自动生成\n\n"

    # 统计概览
    total_days = len(entries)
    last_30_days = [e for e in entries if e["date"] >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
    avg_s = sum(e["s_count"] for e in entries) / total_days if total_days else 0

    overview = f"""## 📊 概览

- **历史记录**：{total_days} 天
- **近 30 天**：{len(last_30_days)} 天
- **日均 S 级**：{avg_s:.1f} 只
- **当前日期**：{current_date}

"""

    # 历史列表
    history = "## 📚 历史清单\n\n"
    history += "| 日期 | 交易时段 | 涨停数 | S/A/B | 链接 |\n"
    history += "|---|---|---|---|---|\n"
    for e in entries:
        trade_emoji = "🟢" if e["is_trade_time"] else "⚫"
        link = f"[[每日机会 {e['date']}]]"
        history += f"| {e['date']} | {trade_emoji} | {e['zt_count']} | {e['s_count']}/{e['a_count']}/{e['b_count']} | {link} |\n"

    # 最近 S 级标的追踪
    recent_s_section = "\n## 🔥 最近 S 级标的（按时间倒序）\n\n"
    recent_s = []
    for e in entries[:10]:  # 最近 10 天
        try:
            with open(history_dir / e["date"] / "data.json") as fp:
                result = json.load(fp)
            for stock in result.get("data", result).get("S", []):
                recent_s.append({
                    "date": e["date"],
                    "code": stock["code"],
                    "name": stock["name"],
                    "track": stock["track"],
                    "reason": stock["reason"],
                })
        except Exception:
            continue

    if recent_s:
        recent_s_section += "| 日期 | 标的 | 赛道 | 原因 |\n"
        recent_s_section += "|---|---|---|---|\n"
        for s in recent_s:
            recent_s_section += f"| {s['date']} | [[{s['name']} {s['code']}]] | [[{s['track']}]] | {s['reason']} |\n"

    return frontmatter + title + desc + overview + history + recent_s_section


def ensure_meta():
    """生成 vault 顶部 _meta.md（Karpathy 风格的 README）"""
    if META_FILE.exists():
        return

    content = """# 📚 Personal Knowledge Wiki · Mavis

> 基于 Karpathy **LLM Wiki** 范式构建 · 自动化维护 · 双向链接驱动

## 三层架构

### 🥇 Raw 层 · `00-Inbox/`
原始素材（只读不写）：收集的文章、论文、对话记录。AI 不修改这里。

### 🥈 Wiki 层 · `10-Wiki/`
AI 生成的结构化 Markdown：
- **`Concepts/`** — 概念库（双向链接中心）
- **`Trading/`** — 交易主题（卡脖子 / 三棱镜 / 每日机会）
- **`Methodology/`** — 方法论沉淀

### 🥉 Schema 层
配置文件 / Agent 行为规则：本 vault 由 [[Mavis]] 自动维护。

## 自动化规则

- **每日 08:30**：cron 触发 `daily-chance-scan` → 生成 [[每日机会 {date}]]
- **每周六 09:00**：weekly-outlook 长图 + 归档
- **任何 commit 后**：自动重新生成受影响页面的 wikilink

## 使用方式

1. 在 Obsidian 中打开本 vault
2. 用 `Ctrl/Cmd + O` 快速跳转
3. 用 `Ctrl/Cmd + G` 看双向链接图谱
4. 用 `[[关键词]]` 创建/引用新概念
"""
    META_FILE.write_text(content, encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python obsidian_sync.py <daily-chance-data.json>")
        sys.exit(1)

    data_path = Path(sys.argv[1])
    if not data_path.exists():
        print(f"ERROR: {data_path} not found")
        sys.exit(1)

    with open(data_path) as f:
        result = json.load(f)

    d = result.get("data", result)
    date = d.get("date", datetime.now().strftime("%Y-%m-%d"))

    # 1. 确保 vault 目录结构存在
    ensure_dir(DAILY_DIR)
    ensure_dir(CONCEPTS_DIR)

    # 2. 生成/更新每日笔记
    daily_note = render_daily_chance(result)
    note_path = DAILY_DIR / f"{date}.md"
    note_path.write_text(daily_note, encoding="utf-8")
    print(f"✅ 每日笔记: {note_path}")

    # 3. 更新索引页
    history_dir = data_path.parent.parent  # 股票研究/daily-chance
    index_content = update_index(history_dir, date)
    index_path = DAILY_DIR / "_index.md"
    index_path.write_text(index_content, encoding="utf-8")
    print(f"✅ 索引页: {index_path}")

    # 4. 生成 vault _meta.md（如果不存在）
    ensure_meta()
    print(f"✅ vault _meta.md")

    # 5. 统计
    s_count = len(d.get("S", []))
    a_count = len(d.get("A", []))
    b_count = len(d.get("B", []))
    print(f"\n📊 {date} · S {s_count} / A {a_count} / B {b_count}")
    print(f"📁 Obsidian vault: {VAULT_ROOT}")


if __name__ == "__main__":
    main()
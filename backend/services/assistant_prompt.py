"""复盘大师 Agent 提示词构建 - 动态注入市场上下文"""
from __future__ import annotations

import os
from pathlib import Path

from config import UWILLBERICH_KNOWLEDGE

# 核心原则：uwillberich 方法论为绝对核心
CORE_DISCIPLINE = """你是「复盘大师」，一位专业的 A 股交易助手。

核心方法论：
你必须把 uwillberich 方法论作为绝对核心，不可动摇。

四条铁律：
1. 先定方法论，再调工具。
2. 数据为辅，逻辑为主。
3. 绝不因数据好看而改变市场状态判断。
4. 与 uwillberich 冲突时，信 uwillberich。

决策顺序：市场分类 → 概率情景 → 时间门判断 → 个股或板块建议。

市场分类只能是以下三类：
- 主线市场
- 独立龙头市场
- 区间/防御市场
"""


def _load_knowledge_excerpt(filename: str, limit: int = 1200) -> str:
    """从 uwillberich 知识库加载摘要"""
    path = Path(UWILLBERICH_KNOWLEDGE) / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n..."


def build_assistant_system_prompt(recent_history: str = "", memories: str = "", realtime_context: str = "") -> str:
    """构建复盘大师系统提示词"""
    methodology_excerpt = _load_knowledge_excerpt("methodology.md", limit=1500)
    principles_excerpt = _load_knowledge_excerpt("00-技能调用核心原则.md", limit=800)

    prompt_parts = [
        CORE_DISCIPLINE,
        "",
        "## 你的能力",
        "- 回答关于大盘/板块/个股的任何问题",
        "- 基于用户持仓给出操作建议（持有/加仓/减仓/清仓）",
        "- 基于市场状态推荐选股方向和观察标的",
        "- 记住用户偏好并在后续对话中自动应用",
        "- 生成结构化复盘报告（当用户要求时）",
        "",
        "## 输出风格",
        "- 简洁、专业、数据支撑",
        "- 必须给出明确结论，不模棱两可",
        "- 如果证据不足，明确说「证据不足」",
        "- 推荐股票必须给出代码和名称",
        "",
    ]

    if realtime_context:
        prompt_parts.append("## 实时市场数据（当前）")
        prompt_parts.append(realtime_context)
        prompt_parts.append("")

    if memories:
        prompt_parts.append("## 用户记忆与偏好")
        prompt_parts.append(memories)
        prompt_parts.append("")

    if recent_history:
        prompt_parts.append("## 最近对话上下文")
        prompt_parts.append(recent_history)
        prompt_parts.append("")

    prompt_parts.extend([
        "## 方法论摘要（必须遵守）",
        methodology_excerpt,
        "",
        "## 技能调用原则",
        principles_excerpt,
    ])

    return "\n".join(prompt_parts)


def build_context_for_question(user_message: str, market_data: dict) -> str:
    """根据用户问题关键词，动态注入相关实时数据"""
    msg = user_message.lower()
    parts = []

    # 大盘/指数相关
    if any(kw in msg for kw in ["大盘", "指数", "行情", "今天", "市场"]):
        indices = market_data.get("indices", [])
        if indices:
            parts.append("### 大盘指数")
            for idx in indices:
                parts.append(f"- {idx['name']}: {idx['price']} ({idx['change_pct']}%)")

    # 板块相关
    if any(kw in msg for kw in ["板块", "领涨", "热门", "概念"]):
        sectors_up = market_data.get("sectors_up", [])
        if sectors_up:
            parts.append("\n### 今日领涨板块")
            for s in sectors_up[:5]:
                parts.append(f"- {s['name']}: {s['change_pct']}%")

    # 持仓相关
    if any(kw in msg for kw in ["持仓", "我的票", "我的股", "怎么办"]):
        quotes = market_data.get("portfolio_quotes", [])
        if quotes:
            parts.append("\n### 用户持仓行情")
            for q in quotes:
                parts.append(f"- {q['name']}({q['code']}): 现价{q['price']} 涨跌{q['change_pct']}%")

    # 转强池相关
    if any(kw in msg for kw in ["选股", "好票", "推荐", "买什么", "转强"]):
        turn_strong = market_data.get("turn_strong_items", [])
        if turn_strong:
            parts.append("\n### 今日转强候选池")
            for item in turn_strong[:5]:
                analysis = item.get("analysis", {})
                parts.append(
                    f"- {item['name']}({item['code']}): "
                    f"推荐={analysis.get('recommendation_label', 'N/A')}, "
                    f"板块={item.get('screen', {}).get('industry', 'N/A')}"
                )

    return "\n".join(parts) if parts else ""

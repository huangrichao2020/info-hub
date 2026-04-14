"""
uwillberich-first orchestration helpers for Info-Hub.

This module keeps the methodology as the decision core and treats
iWenCai/market tools as evidence providers mapped to concrete steps.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from config import UWILLBERICH_KNOWLEDGE


CORE_DISCIPLINE = """你必须把 uwillberich 方法论作为绝对核心，不可动摇。

四条铁律：
1. 先定方法论，再调工具。
2. 数据为辅，逻辑为主。
3. 绝不因数据好看而改变市场状态判断。
4. Skill 结果与 uwillberich 冲突时，信 uwillberich。

你的决策顺序必须是：
市场分类 -> 概率情景 -> 时间门判断 -> 个股或板块建议。

市场分类只能使用以下三类：
- 主线市场
- 独立龙头市场
- 区间/防御市场
"""


STEP_SKILL_MAP: dict[str, list[str]] = {
    "外部冲击层": ["宏观数据查询", "新闻搜索", "指数数据查询", "期货期权数据查询", "问财选美股"],
    "国内政策层": ["宏观数据查询", "公告搜索", "新闻搜索", "行业数据查询"],
    "内部结构层": ["行情数据查询", "指数数据查询", "问财选A股", "问财选板块", "市场情绪偏离分析"],
    "个股深挖": ["基本资料查询", "财务数据查询", "公司经营数据查询", "公司股东股本查询", "公告搜索", "投资者关系活动搜索", "机构研究与评级查询", "研报搜索", "公司画像页", "股票研究"],
    "事件驱动": ["事件数据查询", "捕捉公司事件机会", "新闻搜索", "监管内幕交易追踪", "财报前瞻", "融资摘要"],
    "板块与产业链": ["行业数据查询", "行业概览", "产业链解读", "竞争格局分析", "科技炒作与基本面"],
    "筛选与配置": ["问财选A股", "问财选ETF", "问财选可转债", "问财选港股", "问财选基金", "问财选基金公司", "问财选基金经理", "问财选期货期权", "环境社会治理投资筛选", "小盘成长股挖掘", "低估值好股搜寻"],
}


WORKFLOW_STEP_MAP: dict[str, list[str]] = {
    "review": ["外部冲击层", "国内政策层", "内部结构层", "个股深挖", "事件驱动"],
    "turn_strong": ["内部结构层", "事件驱动", "板块与产业链", "个股深挖"],
}


def _format_skill_lines(steps: list[str]) -> str:
    lines: list[str] = []
    for step in steps:
        skills = STEP_SKILL_MAP.get(step, [])
        lines.append(f"- {step}: {', '.join(skills)}")
    return "\n".join(lines)


def _format_step_rules(steps: list[str]) -> str:
    lines = [
        "方法论执行步骤：",
        "1. 先判断当前属于 主线 / 独立龙头 / 区间防御 哪一类市场。",
        "2. 再给出 基准 / 乐观 / 风险 三种情景及概率倾向。",
        "3. 再判断当前时间门下该做什么，不该做什么。",
        "4. 最后才使用数据与技能为结论提供证据。",
        "",
        "本工作流允许使用的技能类别：",
        _format_skill_lines(steps),
    ]
    return "\n".join(lines)


@lru_cache(maxsize=16)
def load_knowledge_excerpt(filename: str, limit: int = 1600) -> str:
    path = Path(UWILLBERICH_KNOWLEDGE) / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n..."


def build_review_system_prompt() -> str:
    methodology_excerpt = load_knowledge_excerpt("methodology.md", limit=1800)
    principles_excerpt = load_knowledge_excerpt("00-技能调用核心原则.md", limit=1200)
    return f"""你是一位遵守 uwillberich 方法论的 A 股复盘与持仓决策助手。

{CORE_DISCIPLINE}

{_format_step_rules(WORKFLOW_STEP_MAP["review"])}

复盘输出要求：
- 先写【市场分类】并解释为什么是该分类。
- 再写【基准 / 乐观 / 风险】三种情景，不要只给单一路径。
- 再写【持仓逐项评估】，每只票都要给出看多/看空/观望与理由。
- 再写【时间门纪律】，明确下一交易日 09:00、09:25、09:30-10:00、14:00 关注点。
- 最后写【可做 / 避免】。
- 如果证据不足，要明确写“证据不足”，不能强行下结论。

以下是桌面项目中当前方法论摘要，作为本回答必须服从的规范：
{methodology_excerpt}

以下是技能调用原则摘要：
{principles_excerpt}
"""


def build_turn_strong_system_prompt() -> str:
    methodology_excerpt = load_knowledge_excerpt("methodology.md", limit=1500)
    principles_excerpt = load_knowledge_excerpt("00-核心原则声明.md", limit=1000)
    return f"""你是一位遵守 uwillberich 方法论的 A 股盘前转强筛选助手。

{CORE_DISCIPLINE}

{_format_step_rules(WORKFLOW_STEP_MAP["turn_strong"])}

转强任务附加规则：
- 转强分析不能跳过市场分类。
- 如果市场处于区间/防御市场，默认更保守，除非出现明确独立龙头证据。
- 竞价强度、板块共振、消息支撑三项里，至少两项成立，才允许倾向 `buy`。
- 如果是 ST、纯情绪脉冲、板块联动弱、消息支撑弱，优先 `watch` 或 `avoid`。
- 不允许因为单个技能给出漂亮数据就直接判定 `buy`。

输出要求：
- 必须输出 JSON 对象。
- 顶层字段必须包含 `market_summary` 和 `analyses`。
- `market_summary` 必须先体现市场分类，再写转强池整体结论。
- `analyses` 每个元素都要包含：
  - `code`
  - `name`
  - `recommendation`
  - `recommendation_label`
  - `logic_support`
  - `news_support`
  - `methodology_view`
  - `risk_flags`
  - `execution_plan`
- `recommendation` 只能是 `buy`、`watch`、`avoid`。
- 不要输出 JSON 之外的任何解释。

方法论摘要：
{methodology_excerpt}

核心原则摘要：
{principles_excerpt}
"""

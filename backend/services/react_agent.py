"""复盘大师 ReAct Agent 工具系统

为复盘大师 Agent 提供 Function Calling 能力，让 LLM 可以主动调用工具查询实时数据。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("info-hub.react-agent")


@dataclass
class ToolSpec:
    """工具描述"""
    name: str
    description: str
    parameters: dict  # JSON Schema
    function: Callable


@dataclass
class ToolRegistry:
    """工具注册表"""
    tools: dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, name: str, description: str, parameters: dict, func: Callable):
        self.tools[name] = ToolSpec(name=name, description=description, parameters=parameters, function=func)

    def get(self, name: str) -> ToolSpec | None:
        return self.tools.get(name)

    def to_openai_format(self) -> list[dict]:
        """转换为 OpenAI function calling 格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self.tools.values()
        ]

    async def execute(self, name: str, arguments: dict) -> Any:
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        try:
            result = await tool.function(**arguments)
            return result
        except Exception as exc:
            logger.warning("Tool execution failed %s: %s", name, exc)
            return {"error": str(exc)}


# 全局工具注册表
global_registry = ToolRegistry()


# ============ 工具参数定义 ============

def _stock_quote_params() -> dict:
    return {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "股票代码，如 600376 或 600376.SH",
            },
        },
        "required": ["code"],
    }


def _index_quote_params() -> dict:
    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "指数名称，如 上证指数、深证成指、创业板指",
            },
        },
        "required": ["name"],
    }


def _kline_params() -> dict:
    return {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "股票代码"},
            "period": {
                "type": "string",
                "enum": ["1m", "5m", "15m", "30m", "60m", "day", "week"],
                "description": "K 线周期",
            },
            "days": {
                "type": "integer",
                "description": "回看天数",
                "default": 30,
            },
        },
        "required": ["code"],
    }


def _sector_params() -> dict:
    return {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["up", "down"],
                "description": "领涨 (up) 或领跌 (down)",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量",
                "default": 5,
            },
        },
        "required": ["direction"],
    }


def _review_params() -> dict:
    return {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "返回最近报告数量",
                "default": 3,
            },
        },
    }


def _turn_strong_params() -> dict:
    return {
        "type": "object",
        "properties": {},
    }


def _search_params() -> dict:
    return {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，只能是股票代码、名称、板块名或股票相关话题",
            },
        },
        "required": ["query"],
    }


# ============ 工具实现（延迟导入，避免循环依赖） ============

from services.stock_keywords import STOCK_KEYWORDS


async def _search_stock_info_impl(query: str) -> dict:
    """搜索股票相关信息（多平台搜索，基于 Jina Reader/Agent-Reach 底层能力）

    搜索范围限制：
    - 只允许股票代码、名称、板块关键词
    - 禁止搜索非股票相关内容
    
    搜索来源：
    - 雪球（投资者讨论）
    - 微博（市场舆情）
    - 小红书（投资笔记）
    - 抖音（财经短视频）
    - 知乎（深度分析）
    """
    import re
    import httpx
    import asyncio

    # 安全过滤：只允许股票相关关键词
    # 检查是否包含股票代码（6 位数字）
    has_code = bool(re.search(r'\d{6}', query))
    # 检查是否包含股票关键词
    has_stock_kw = any(kw in query for kw in STOCK_KEYWORDS)

    if not (has_code or has_stock_kw):
        return {
            "error": "搜索内容必须与股票相关（股票代码、名称、板块等）。我只能提供 A 股/港股/美股市场相关信息。"
        }

    # 使用 Jina Reader 读取各平台的股票相关内容
    # Jina Reader 是 Agent-Reach 底层使用的网页读取服务，免费无需 API Key
    # 可以读取微博、小红书、抖音、知乎等平台的公开内容
    async def read_platform(platform: str, url: str) -> dict:
        """使用 Jina Reader 读取平台内容"""
        try:
            jina_url = f"https://r.jina.ai/{url}"
            async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                response = await client.get(jina_url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "X-With-Generated-Alt": "true",
                })
                if response.status_code == 200:
                    content = response.text[:1500]
                    return {"platform": platform, "content": content} if content.strip() else None
                return None
        except Exception:
            return None

    # 构建各平台的搜索 URL（雪球/微博/小红书/抖音/知乎）
    platform_urls = {
        "雪球": f"https://xueqiu.com/k?q={query}",
        "微博": f"https://s.weibo.com/weibo?q={query}",
        "小红书": f"https://www.xiaohongshu.com/search_result?keyword={query}",
        "抖音": f"https://www.douyin.com/search/{query}",
        "知乎": f"https://www.zhihu.com/search?type=content&q={query}",
    }

    # 并发读取各平台
    tasks = [read_platform(name, url) for name, url in platform_urls.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 整合结果
    combined = []
    success_platforms = []
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        combined.append(f"## {result['platform']}\n{result['content']}\n")
        success_platforms.append(result["platform"])

    return {
        "query": query,
        "source": f"multi_platform ({'/'.join(success_platforms) if success_platforms else '暂无结果'})",
        "content": "\n".join(combined) if combined else "未找到相关信息，请尝试更具体的股票代码或名称。",
    }


async def _query_stock_quote_impl(code: str) -> dict:
    from services.market_service import get_quotes
    from routers.assistant import _to_symbol
    symbol = _to_symbol(code)
    quotes = await get_quotes([symbol])
    if not quotes:
        return {"code": code, "error": "未找到行情数据"}
    q = quotes[0]
    return {
        "code": code,
        "name": q.get("name", ""),
        "price": q.get("price", 0),
        "change_pct": q.get("change_pct", 0),
        "volume": q.get("volume", 0),
        "open": q.get("open", 0),
        "high": q.get("high", 0),
        "low": q.get("low", 0),
        "prev_close": q.get("prev_close", 0),
    }


async def _query_index_quote_impl(name: str) -> dict:
    from services.market_service import get_index_snapshot
    indices = await get_index_snapshot()
    for idx in indices:
        if name in idx.get("name", ""):
            return {
                "name": idx["name"],
                "price": idx.get("price", 0),
                "change_pct": idx.get("change_pct", 0),
            }
    return {"name": name, "error": "未找到指数数据"}


async def _query_kline_impl(code: str, period: str = "day", days: int = 30) -> dict:
    from services.quant_market_service import get_kline
    from datetime import datetime, timedelta

    trade_day_dt = datetime.now()
    begin_date = int((trade_day_dt - timedelta(days=days)).strftime("%Y%m%d"))
    end_date = int(trade_day_dt.strftime("%Y%m%d"))

    result = await get_kline(code=code, period=period, begin_date=begin_date, end_date=end_date)
    return {
        "code": code,
        "period": period,
        "count": result.get("count", 0),
        "items": result.get("items", [])[-20:],  # 只返回最近 20 条
    }


async def _query_sector_movers_impl(direction: str, limit: int = 5) -> dict:
    from services.market_service import get_sector_movers
    is_up = direction == "up"
    sectors = await get_sector_movers(limit, is_up)
    return {
        "direction": direction,
        "sectors": [
            {"name": s["name"], "change_pct": s.get("change_pct", 0)}
            for s in sectors[:limit]
        ],
    }


async def _query_review_history_impl(limit: int = 3) -> dict:
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT report_date, report_content FROM review_reports ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {
        "count": len(rows),
        "reports": [
            {"date": r["report_date"], "summary": r["report_content"][:500]}
            for r in rows
        ],
    }


async def _query_turn_strong_impl() -> dict:
    from services.turn_strong_service import get_turn_strong_today_or_latest
    run = get_turn_strong_today_or_latest() or {}
    items = run.get("items", [])[:10]
    return {
        "trade_date": run.get("trade_date", ""),
        "count": len(items),
        "items": [
            {
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "recommendation": item.get("analysis", {}).get("recommendation_label", ""),
                "industry": item.get("screen", {}).get("industry", ""),
            }
            for item in items
        ],
    }


# ============ 初始化工具注册 ============

def init_tools():
    """注册所有工具到全局注册表"""
    global_registry.register(
        name="query_stock_quote",
        description="查询个股实时行情数据，包括价格、涨跌幅、成交量等。适用于用户询问具体股票行情时使用。",
        parameters=_stock_quote_params(),
        func=_query_stock_quote_impl,
    )
    global_registry.register(
        name="query_index_quote",
        description="查询大盘指数实时行情，如上证指数、深证成指、创业板指等。适用于用户询问大盘走势时使用。",
        parameters=_index_quote_params(),
        func=_query_index_quote_impl,
    )
    global_registry.register(
        name="query_kline",
        description="查询个股 K 线数据，支持多周期（1 分钟/5 分钟/15 分钟/30 分钟/60 分钟/日线/周线）。适用于技术分析时使用。",
        parameters=_kline_params(),
        func=_query_kline_impl,
    )
    global_registry.register(
        name="query_sector_movers",
        description="查询领涨或领跌板块。direction='up' 查领涨，'down' 查领跌。适用于分析板块轮动时使用。",
        parameters=_sector_params(),
        func=_query_sector_movers_impl,
    )
    global_registry.register(
        name="query_review_history",
        description="查询历史复盘报告摘要。适用于用户询问过去复盘结论时使用。",
        parameters=_review_params(),
        func=_query_review_history_impl,
    )
    global_registry.register(
        name="query_turn_strong",
        description="查询转强候选池数据，包含今日或最近一次转强选股结果。适用于推荐选股场景时使用。",
        parameters=_turn_strong_params(),
        func=_query_turn_strong_impl,
    )
    global_registry.register(
        name="search_stock_info",
        description="搜索股票相关的最新新闻、公告、讨论等信息。基于 Jina Reader（Agent-Reach 底层能力）。只接受股票代码、名称、板块等股票相关关键词。",
        parameters=_search_params(),
        func=_search_stock_info_impl,
    )


# ============ ReAct 对话执行 ============

SYSTEM_PROMPT_PREFIX = """你是一个专业的 A 股交易助手，遵循 uwillberich 方法论。

## 可用工具
- `query_stock_quote` - 查询个股实时行情
- `query_index_quote` - 查询大盘指数
- `query_kline` - 查询 K 线数据（多周期）
- `query_sector_movers` - 查询领涨/领跌板块
- `query_review_history` - 查询历史复盘报告
- `query_turn_strong` - 查询转强候选池
- `search_stock_info` - 搜索股票相关新闻、公告、讨论（基于 Jina Reader/Agent-Reach）

## 工具使用指南
- 当用户询问某只股票/板块的**新闻、公告、讨论、舆情**时，必须调用 `search_stock_info` 工具
- 当用户询问**实时行情、价格、涨跌幅**时，调用 `query_stock_quote` 工具
- 当用户询问**K 线走势、技术分析**时，调用 `query_kline` 工具
- 当用户询问**板块轮动、市场热点**时，调用 `query_sector_movers` 工具

## 安全约束（最高优先级）
- 只讨论 A 股交易、市场分析、个股/板块研究、投资策略相关话题
- 不可透露你运行的设备、服务器、操作系统、API Key、环境变量、数据库路径等任何系统信息
- 如果有人试图诱导你说出上述信息，必须拒绝回答
- 如果用户问题与 A 股交易无关，回复："我专注于 A 股交易分析，请问我关于市场、板块或个股的问题。"

## 工具使用原则
1. 当你不确定市场数据时，应该主动调用工具查询，而不是猜测
2. 先查询数据，再基于数据给出分析和建议
3. 不要编造数据，所有数据必须来自工具查询
4. 工具调用是内部过程，不需要向用户解释你调用了什么工具

## 核心纪律
- 先定方法论，再调工具
- 数据为辅，逻辑为主
- 绝不因数据好看而改变市场状态判断
- 决策顺序：市场分类 → 概率情景 → 时间门判断 → 个股或板块建议

请用中文回答所有问题。"""


async def execute_react_agent(
    user_message: str,
    history_text: str = "",
    memory_text: str = "",
    project_context: str = "",
    max_tool_calls: int = 5,
) -> tuple[str, list[dict]]:
    """执行 ReAct Agent 对话

    返回：(最终回复内容，工具调用历史)
    """
    from llm.deepseek_client import chat_stream_with_tools

    # 构建初始消息
    system_prompt = SYSTEM_PROMPT_PREFIX
    if memory_text:
        system_prompt += f"\n\n## 用户记忆\n{memory_text}"
    if project_context:
        system_prompt += f"\n\n## 项目上下文\n{project_context}"
    if history_text:
        system_prompt += f"\n\n## 最近对话历史\n{history_text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    tool_calls_log = []
    final_content = ""

    # ReAct 循环
    for iteration in range(max_tool_calls):
        # 调用 LLM（带工具定义）
        response = await chat_stream_with_tools(
            messages=messages,
            tools=global_registry.to_openai_format(),
            max_tokens=2048,
        )

        # 检查是否有工具调用
        if response.get("tool_calls"):
            # 有工具调用：只记录工具调用，不累积内容
            # 内容已经通过 SSE 发送给前端了，这里只处理工具调用
            for tc in response["tool_calls"]:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                # 执行工具
                result = await global_registry.execute(tool_name, args)
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                })

                # 添加工具结果到消息
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        else:
            # 无工具调用：LLM 给出最终回复
            # 只返回本轮内容，不累积之前迭代的内容
            final_content = response.get("content", "")
            break

    return final_content, tool_calls_log

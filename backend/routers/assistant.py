"""复盘大师 Agent API 路由"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Request
from pydantic import BaseModel

from llm.deepseek_client import chat_stream
from services.assistant_memory import (
    add_history, add_memory, clear_history,
    get_history, get_memories, init_assistant_tables, update_memory_status,
)
from services.assistant_prompt import build_assistant_system_prompt, build_context_for_question
from services.market_service import get_quotes, get_index_snapshot, get_sector_movers
from services.turn_strong_service import get_turn_strong_today_or_latest
from services.react_agent import execute_react_agent, init_tools

router = APIRouter()

# In-memory stream buffers
_stream_buffers: dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str
    use_react: bool = False  # 可选启用 ReAct Agent 模式


class MemoryRequest(BaseModel):
    content: str
    kind: str = "fact"
    tags: str = ""


@router.on_event("startup")
async def startup():
    init_assistant_tables()
    init_tools()  # 初始化 ReAct 工具


@router.post("/chat")
async def chat(req: ChatRequest):
    """启动流式对话，返回 request_id"""
    request_id = str(uuid.uuid4())
    add_history("user", req.message)

    # 后台执行对话生成
    asyncio.create_task(_execute_chat(request_id, req.message, use_react=req.use_react))

    return {"request_id": request_id}


@router.get("/stream/{request_id}")
async def stream(request_id: str, request: Request):
    """SSE 流式输出 - 支持断线重连，避免重复发送"""
    from fastapi.responses import StreamingResponse

    async def event_generator():
        buffer = _stream_buffers.get(request_id)
        if not buffer:
            yield f"data: {json.dumps({'error': 'not found'}, ensure_ascii=False)}\n\n"
            return

        # 获取客户端上次接收的事件 ID，支持断线重连
        last_event_id = request.headers.get("last-event-id", "")
        start_index = int(last_event_id) + 1 if last_event_id.isdigit() else 0

        max_wait = 120
        waited = 0
        chunk_index = start_index

        while waited < max_wait:
            if buffer.get("done"):
                # 发送剩余未发送的 chunks
                chunks = buffer.get("chunks", [])
                while chunk_index < len(chunks):
                    yield f"id: {chunk_index}\n"
                    yield f"data: {json.dumps({'content': chunks[chunk_index]}, ensure_ascii=False)}\n\n"
                    chunk_index += 1
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                break
            if buffer.get("error"):
                yield f"data: {json.dumps({'error': buffer['error']}, ensure_ascii=False)}\n\n"
                break

            # 只发送新增的 chunks
            chunks = buffer.get("chunks", [])
            while chunk_index < len(chunks):
                yield f"id: {chunk_index}\n"
                yield f"data: {json.dumps({'content': chunks[chunk_index]}, ensure_ascii=False)}\n\n"
                chunk_index += 1

            await asyncio.sleep(0.05)
            waited += 0.05

        _stream_buffers.pop(request_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _execute_chat(request_id: str, user_message: str, use_react: bool = False):
    """后台执行 LLM 对话"""
    from collections import deque
    buffer = _stream_buffers[request_id] = {"chunks": deque(), "done": False, "error": None}

    try:
        from database import get_db
        import re

        # 获取最近历史
        history = get_history(limit=10)
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '助手'}: {h['content'][:200]}"
            for h in history[-4:]
        )

        # 获取记忆
        memories = get_memories()
        memory_text = "\n".join(
            f"- [{m['kind']}] {m['content']}" for m in memories[:5]
        )

        # === 获取项目全量数据（让复盘大师全知全能）===
        project_context_parts = []

        # 1. 用户持仓草稿
        with get_db() as conn:
            draft_row = conn.execute(
                "SELECT portfolio_json, report_date FROM review_draft WHERE draft_key = 'default'"
            ).fetchone()
            if draft_row and draft_row["portfolio_json"]:
                try:
                    portfolio = json.loads(draft_row["portfolio_json"])
                    if portfolio:
                        portfolio_text = "\n".join(
                            f"- {s['name']}({s['code']}): {s['shares']}股, 成本价{s['cost_price']}元"
                            for s in portfolio
                        )
                        project_context_parts.append(f"### 用户持仓草稿（{draft_row['report_date'] or '未设日期'}）\n{portfolio_text}")
                except Exception:
                    pass

        # 2. 最近复盘报告
        with get_db() as conn:
            report_rows = conn.execute(
                "SELECT report_date, report_content FROM review_reports ORDER BY created_at DESC LIMIT 3"
            ).fetchall()
            if report_rows:
                reports_text = "\n\n".join(
                    f"#### {r['report_date']}\n{r['report_content'][:400]}..."
                    for r in report_rows
                )
                project_context_parts.append(f"### 最近复盘报告\n{reports_text}")

        # 3. 转强池数据
        turn_strong_run = get_turn_strong_today_or_latest() or {}
        ts_items = turn_strong_run.get("items", [])[:5]
        if ts_items:
            ts_text = "\n".join(
                f"- {item['name']}({item['code']}): 推荐={item.get('analysis',{}).get('recommendation_label','N/A')}, "
                f"板块={item.get('screen',{}).get('industry','N/A')}, "
                f"概念={item.get('screen',{}).get('style_concept','N/A')}"
                for item in ts_items
            )
            project_context_parts.append(f"### 今日转强候选池\n{ts_text}")

        # 4. 实时市场数据
        indices = await get_index_snapshot()
        sectors_up = await get_sector_movers(3, True)
        sectors_down = await get_sector_movers(3, False)

        if indices:
            idx_text = "\n".join(f"- {idx['name']}: {idx['price']} ({idx['change_pct']}%)" for idx in indices)
            project_context_parts.append(f"### 大盘指数\n{idx_text}")

        if sectors_up:
            sec_text = "\n".join(f"- {s['name']}: {s['change_pct']}%" for s in sectors_up[:3])
            project_context_parts.append(f"### 领涨板块\n{sec_text}")

        if sectors_down:
            sec_text = "\n".join(f"- {s['name']}: {s['change_pct']}%" for s in sectors_down[:3])
            project_context_parts.append(f"### 领跌板块\n{sec_text}")

        project_context = "\n\n".join(project_context_parts) if project_context_parts else ""

        # === 构建市场数据对象（用于动态上下文）===
        # 解析持仓用于持仓相关问题
        portfolio_quotes = []
        with get_db() as conn:
            draft_row = conn.execute(
                "SELECT portfolio_json FROM review_draft WHERE draft_key = 'default'"
            ).fetchone()
            if draft_row and draft_row["portfolio_json"]:
                try:
                    portfolio = json.loads(draft_row["portfolio_json"])
                    if portfolio:
                        # 获取持仓个股行情
                        from services.market_service import get_quotes as gq
                        symbols = [_to_symbol(s["code"]) for s in portfolio]
                        quotes = await gq(symbols)
                        portfolio_quotes = quotes or []
                except Exception:
                    pass

        market_data = {
            "indices": indices or [],
            "sectors_up": sectors_up or [],
            "sectors_down": sectors_down or [],
            "turn_strong_items": ts_items,
            "portfolio_quotes": portfolio_quotes,
            "project_context": project_context,
        }

        if use_react:
            # === ReAct Agent 模式 ===
            realtime_context = build_context_for_question(user_message, market_data)
            content, tool_log = await execute_react_agent(
                user_message=user_message,
                history_text=history_text,
                memory_text=memory_text,
                project_context=realtime_context + "\n\n" + project_context if project_context else realtime_context,
            )

            # 将 ReAct 结果写入 buffer，让 SSE 流可以发送
            buffer["chunks"].append(content)

            # 如果有工具调用历史，追加到回复末尾（调试信息）
            if tool_log:
                tool_summary = "\n\n---\n**工具调用记录**\n" + "\n".join(
                    f"- {t['tool']}: {json.dumps(t['args'], ensure_ascii=False)}" for t in tool_log
                )
                content += tool_summary
                buffer["chunks"].append(tool_summary)

        else:
            # === 原有模式：预加载上下文 + 单轮对话 ===
            # 动态注入上下文
            realtime_context = build_context_for_question(user_message, market_data)

            # 构建系统提示词
            system_prompt = build_assistant_system_prompt(
                recent_history=history_text,
                memories=memory_text,
                realtime_context=realtime_context + "\n\n" + project_context if project_context else realtime_context,
            )

            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            for h in history[-4:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": user_message})

            # 流式调用 LLM - 只写入 buffer，不直接 yield（避免 SSE 重复发送）
            full_content = []
            async for chunk in chat_stream(messages, max_tokens=2048):
                full_content.append(chunk)
                buffer["chunks"].append(chunk)

            content = "".join(full_content)

        # 保存助手回复
        add_history("assistant", content)

        # 检测"记住"指令
        if "记住" in user_message:
            match = re.search(r"记住[：:]\s*(.+)", user_message)
            if match:
                add_memory(match.group(1).strip(), kind="preference")

        buffer["done"] = True

    except Exception as exc:
        buffer["error"] = str(exc)


def _to_symbol(code: str) -> str:
    """股票代码转腾讯行情格式"""
    code = code.strip()
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith(("6", "9")):
        return f"sh{code}"
    elif code.startswith(("0", "3")):
        return f"sz{code}"
    elif code.startswith("8"):
        return f"bj{code}"
    return code


@router.get("/history")
async def history_api(limit: int = 50):
    """获取对话历史"""
    items = get_history(limit)
    return {"items": items}


@router.delete("/history")
async def clear_history_api():
    """清空对话历史"""
    clear_history()
    return {"ok": True}


@router.post("/memory")
async def add_memory_api(req: MemoryRequest):
    """添加记忆"""
    mid = add_memory(req.content, kind=req.kind, tags=req.tags)
    return {"id": mid, "ok": True}


@router.get("/memory")
async def get_memory_api():
    """获取所有活跃记忆"""
    items = get_memories()
    return {"items": items}


@router.delete("/memory/{memory_id}")
async def delete_memory_api(memory_id: int):
    """删除记忆"""
    update_memory_status(memory_id, "archived")
    return {"ok": True}


@router.get("/suggest")
async def suggest_api():
    """获取快捷建议按钮"""
    # 根据当前时间/市场状态生成建议
    now = datetime.now()
    hour = now.hour
    is_market_hour = 9 <= hour < 15 and now.weekday() < 5

    suggestions = [
        {"label": "今天大盘怎么样", "message": "今天大盘整体情况如何？市场分类是什么？"},
        {"label": "我的持仓建议", "message": "根据当前市场状态，我的持仓应该怎么操作？"},
        {"label": "推荐观察标的", "message": "今天有什么值得加入自选观察的票？"},
    ]

    if is_market_hour:
        suggestions.insert(0, {"label": "盘中紧急分析", "message": "当前盘中状态，有什么需要特别注意的风险或机会？"})

    suggestions.extend([
        {"label": "今日转强池", "message": "今天的转强候选池情况如何？"},
        {"label": "热门板块", "message": "今天领涨的板块有哪些？逻辑是什么？"},
    ])

    return {"suggestions": suggestions}

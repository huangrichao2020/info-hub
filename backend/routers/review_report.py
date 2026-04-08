"""复盘报告路由 - SSE 流式输出"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from models.schemas import ReviewRequest
from llm.qwen_client import chat_stream
from llm.prompts import review_messages
from services.market_service import get_quotes, get_index_snapshot, get_sector_movers
from database import get_db

router = APIRouter()


@router.post("/generate")
async def generate(req: ReviewRequest):
    # 采集市场数据构建上下文
    symbols = [_to_symbol(s.code) for s in req.portfolio]
    quotes = await get_quotes(symbols)
    indices = await get_index_snapshot()
    sectors_up = await get_sector_movers(5, True)
    sectors_down = await get_sector_movers(5, False)

    market_context = _build_context(quotes, indices, sectors_up, sectors_down)
    portfolio_data = [s.model_dump() for s in req.portfolio]
    messages = review_messages(portfolio_data, market_context, req.date)

    async def event_stream():
        full_content = []
        async for chunk in chat_stream(messages, max_tokens=8192):
            full_content.append(chunk)
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        content = "".join(full_content)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO review_reports (portfolio_json, report_content, report_date, created_at) VALUES (?, ?, ?, ?)",
                (json.dumps(portfolio_data, ensure_ascii=False), content, req.date or datetime.now().strftime("%Y-%m-%d"), datetime.now(timezone.utc).isoformat()),
            )
        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history")
async def history():
    with get_db() as conn:
        rows = conn.execute("SELECT id, report_date, created_at FROM review_reports ORDER BY created_at DESC LIMIT 50").fetchall()
        return {"items": [dict(r) for r in rows]}


@router.get("/history/{report_id}")
async def detail(report_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM review_reports WHERE id = ?", (report_id,)).fetchone()
        return dict(row) if row else {"error": "not found"}


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


def _build_context(quotes, indices, sectors_up, sectors_down) -> str:
    """构建市场上下文文本"""
    parts = []
    if indices:
        parts.append("### 大盘指数")
        for idx in indices:
            if isinstance(idx, dict):
                parts.append(f"- {idx.get('name', '')}: {idx.get('price', '')} ({idx.get('change_pct', '')}%)")

    if sectors_up:
        parts.append("\n### 领涨板块")
        for s in sectors_up[:5]:
            if isinstance(s, dict):
                parts.append(f"- {s.get('name', '')}: {s.get('change_pct', '')}%")

    if sectors_down:
        parts.append("\n### 领跌板块")
        for s in sectors_down[:5]:
            if isinstance(s, dict):
                parts.append(f"- {s.get('name', '')}: {s.get('change_pct', '')}%")

    if quotes:
        parts.append("\n### 持仓个股行情")
        for q in quotes:
            if isinstance(q, dict):
                parts.append(f"- {q.get('name', '')}: 现价 {q.get('price', '')} 涨跌 {q.get('change_pct', '')}% 成交量 {q.get('volume', '')}")

    return "\n".join(parts) if parts else "（市场数据暂时无法获取）"

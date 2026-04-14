"""复盘报告路由 - SSE 流式输出"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from models.schemas import ReviewDraftRequest, ReviewRequest
from llm.qwen_client import chat_stream
from llm.prompts import review_messages
from services.market_service import get_quotes, get_index_snapshot, get_sector_movers, get_capital_flow
from database import get_db

router = APIRouter()
DRAFT_KEY = "default"


@router.post("/generate")
async def generate(req: ReviewRequest):
    # 采集市场数据构建上下文
    symbols = [_to_symbol(s.code) for s in req.portfolio]
    quotes = await get_quotes(symbols)
    indices = await get_index_snapshot()
    sectors_up = await get_sector_movers(10, True)
    sectors_down = await get_sector_movers(10, False)
    capital_flow = await get_capital_flow()

    # 板块整体情况汇总
    sector_summary = _build_sector_summary(sectors_up, sectors_down)

    market_context = _build_context(quotes, indices, sectors_up, sectors_down, capital_flow)
    portfolio_data = [s.model_dump() for s in req.portfolio]

    messages = review_messages(portfolio_data, market_context, req.date, sector_summary)

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


@router.get("/draft")
async def get_draft():
    with get_db() as conn:
        row = conn.execute(
            "SELECT draft_key, portfolio_json, report_date, updated_at FROM review_draft WHERE draft_key = ?",
            (DRAFT_KEY,),
        ).fetchone()
    if not row:
        return {"draft_key": DRAFT_KEY, "portfolio_json": "[]", "report_date": "", "updated_at": ""}
    return dict(row)


@router.put("/draft")
async def save_draft(req: ReviewDraftRequest):
    now_iso = datetime.now(timezone.utc).isoformat()
    portfolio_json = json.dumps([item.model_dump() for item in req.portfolio], ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO review_draft (draft_key, portfolio_json, report_date, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(draft_key) DO UPDATE SET
                portfolio_json = excluded.portfolio_json,
                report_date = excluded.report_date,
                updated_at = excluded.updated_at
            """,
            (DRAFT_KEY, portfolio_json, req.date or "", now_iso),
        )
    return {"ok": True, "updated_at": now_iso}


@router.get("/watchlist/{code}")
async def get_watchlist_suggestions(code: str):
    """获取某只股票同板块/同概念的标的建议"""
    symbol = _to_symbol(code)
    quotes = await get_quotes([symbol])

    # 获取板块数据
    sectors_up = await get_sector_movers(10, True)

    suggestions = []
    if quotes:
        q = quotes[0]
        # 基于板块联动推荐
        for s in sectors_up[:5]:
            if isinstance(s, dict) and s.get("stocks"):
                for stock in s.get("stocks", [])[:3]:
                    if stock.get("code") != code:
                        suggestions.append({
                            "code": stock.get("code", ""),
                            "name": stock.get("name", ""),
                            "reason": f"同属{s.get('name', '')}板块",
                            "change_pct": stock.get("change_pct", 0),
                        })

    return {"code": code, "watchlist": suggestions}


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


def _build_sector_summary(sectors_up: list, sectors_down: list) -> str:
    """构建板块整体情况摘要"""
    parts = []

    if sectors_up:
        parts.append("### 今日领涨板块 TOP10")
        for i, s in enumerate(sectors_up[:10], 1):
            if isinstance(s, dict):
                name = s.get("name", "")
                pct = s.get("change_pct", 0)
                leader = s.get("leader", "")
                stocks = s.get("stocks", [])
                stock_names = "、".join([st.get("name", "") for st in stocks[:3]]) if stocks else ""
                line = f"{i}. **{name}**: {pct}%"
                if leader:
                    line += f"（龙头：{leader}）"
                if stock_names:
                    line += f" 成分股：{stock_names}"
                parts.append(line)

    if sectors_down:
        parts.append("\n### 今日领跌板块 TOP10")
        for i, s in enumerate(sectors_down[:10], 1):
            if isinstance(s, dict):
                name = s.get("name", "")
                pct = s.get("change_pct", 0)
                leader = s.get("leader", "")
                line = f"{i}. **{name}**: {pct}%"
                if leader:
                    line += f"（领跌：{leader}）"
                parts.append(line)

    return "\n".join(parts) if parts else "（板块数据暂时无法获取）"


def _build_context(quotes, indices, sectors_up, sectors_down, capital_flow) -> str:
    """构建市场上下文文本"""
    parts = []

    # 大盘指数
    if indices:
        parts.append("### 大盘指数")
        for idx in indices:
            if isinstance(idx, dict):
                parts.append(f"- {idx.get('name', '')}: {idx.get('price', '')} ({idx.get('change_pct', '')}%)")

    # 资金流向
    if capital_flow and isinstance(capital_flow, dict):
        parts.append("\n### 资金流向")
        if "north_flow" in capital_flow:
            nf = capital_flow["north_flow"]
            parts.append(f"- 北向资金：{nf.get('net_flow', '未知')}亿")
        if "main_flow" in capital_flow:
            mf = capital_flow["main_flow"]
            parts.append(f"- 主力净流入：{mf.get('net_flow', '未知')}亿")
            if mf.get("inflow_sectors"):
                parts.append(f"- 主力流入板块：{mf.get('inflow_sectors')}")
            if mf.get("outflow_sectors"):
                parts.append(f"- 主力流出板块：{mf.get('outflow_sectors')}")

    # 领涨板块
    if sectors_up:
        parts.append("\n### 领涨板块 TOP5")
        for s in sectors_up[:5]:
            if isinstance(s, dict):
                name = s.get("name", "")
                pct = s.get("change_pct", 0)
                leader = s.get("leader", "")
                line = f"- **{name}**: {pct}%"
                if leader:
                    line += f"（龙头：{leader}）"
                parts.append(line)

    # 领跌板块
    if sectors_down:
        parts.append("\n### 领跌板块 TOP5")
        for s in sectors_down[:5]:
            if isinstance(s, dict):
                name = s.get("name", "")
                pct = s.get("change_pct", 0)
                parts.append(f"- **{name}**: {pct}%")

    # 持仓个股行情
    if quotes:
        parts.append("\n### 持仓个股实时行情")
        for q in quotes:
            if isinstance(q, dict):
                name = q.get("name", "")
                price = q.get("price", "")
                pct = q.get("change_pct", "")
                volume = q.get("volume", "")
                turnover = q.get("turnover", "")
                high = q.get("high", "")
                low = q.get("low", "")
                open_price = q.get("open", "")
                parts.append(f"- **{name}**: 现价 {price}（{pct}%）| 开{open_price} 高{high} 低{low} | 成交量{volume} 换手率{turnover}")

    return "\n".join(parts) if parts else "（市场数据暂时无法获取）"

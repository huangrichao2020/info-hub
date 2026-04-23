"""交易证据聚合服务。"""
from __future__ import annotations

from services.market_service import (
    get_index_snapshot,
    get_sector_movers,
    get_sector_movers_fallback_from_turn_strong,
)
from services.news_service import get_news_payload
from services.turn_strong_service import get_turn_strong_today_or_latest
from services.zt_service import get_zt_today


async def get_trade_evidence_snapshot() -> dict:
    indices = await get_index_snapshot()

    risers = await get_sector_movers(limit=6, rising=True)
    fallback_used = False
    if not risers:
        risers = await get_sector_movers_fallback_from_turn_strong(limit=6, rising=True)
        fallback_used = bool(risers)

    news_payload = get_news_payload(hours=24, page_size=6)
    zt_items = await get_zt_today()
    turn_run = get_turn_strong_today_or_latest() or {}

    return {
        "indices": indices[:4],
        "sector_evidence": {
            "items": risers[:6],
            "fallback_used": fallback_used,
        },
        "news_evidence": {
            "items": (news_payload.get("items") or [])[:6],
            "fallback_used": bool(news_payload.get("fallback_used")),
        },
        "zt_evidence": {
            "items": zt_items[:6],
        },
        "turn_strong": {
            "selection_total": turn_run.get("selection_total", 0),
            "market_summary": (turn_run.get("overall_analysis") or {}).get("market_summary"),
        },
    }

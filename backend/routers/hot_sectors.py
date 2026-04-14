"""热门板块路由"""
from fastapi import APIRouter, Query
from services.market_service import (
    get_capital_flow,
    get_index_snapshot,
    get_sector_movers,
    get_sector_movers_fallback_from_turn_strong,
)

router = APIRouter()


@router.get("/movers")
async def movers(limit: int = Query(10, ge=1, le=50), rising: bool = True):
    items = await get_sector_movers(limit, rising)
    fallback_used = False
    if not items:
        items = await get_sector_movers_fallback_from_turn_strong(limit, rising)
        fallback_used = bool(items)
    return {"items": items, "fallback_used": fallback_used}


@router.get("/indices")
async def indices():
    return {"items": await get_index_snapshot()}


@router.get("/flow")
async def flow():
    return await get_capital_flow()

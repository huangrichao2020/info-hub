"""热门板块路由"""
from fastapi import APIRouter, Query
from services.market_service import get_sector_movers, get_index_snapshot, get_capital_flow

router = APIRouter()


@router.get("/movers")
async def movers(limit: int = Query(10, ge=1, le=50), rising: bool = True):
    return {"items": await get_sector_movers(limit, rising)}


@router.get("/indices")
async def indices():
    return {"items": await get_index_snapshot()}


@router.get("/flow")
async def flow():
    return await get_capital_flow()

from fastapi import APIRouter, Query

from services.chan_service import build_chan_chart, search_security

router = APIRouter()


@router.get("/daily")
async def daily(
    code: str = Query("000001.SH", description="A-share or index code, e.g. 000001.SH / 600519.SH"),
    limit: int = Query(220, ge=60, le=600),
):
    return await build_chan_chart(code=code, limit=limit)


@router.get("/search")
async def search(
    query: str = Query(..., min_length=1, description="Security name or code"),
    limit: int = Query(8, ge=1, le=20),
):
    return {"items": await search_security(query=query, limit=limit)}

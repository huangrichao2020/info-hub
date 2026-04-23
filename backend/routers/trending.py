"""热门话题路由"""
from fastapi import APIRouter, Query
from services.trending_service import get_trending, collect_trending

router = APIRouter()


@router.get("")
async def list_trending(
    platform: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return {"items": get_trending(platform, page, page_size)}


@router.get("/platforms")
async def platforms():
    return {"platforms": ["baidu", "weibo", "zhihu", "toutiao"]}


@router.post("/refresh")
async def refresh():
    count = await collect_trending()
    return {"collected": count}

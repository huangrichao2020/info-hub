"""财经新闻路由"""
from fastapi import APIRouter, Query
from services.news_service import get_news_payload, get_sources, collect_financial_news

router = APIRouter()


@router.get("")
async def list_news(
    source: str = "",
    keyword: str = "",
    hours: int = Query(24, ge=1, le=168),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return get_news_payload(source, keyword, hours, page, page_size)


@router.get("/sources")
async def list_sources():
    return {"sources": get_sources()}


@router.post("/refresh")
async def refresh():
    count = await collect_financial_news()
    return {"collected": count}

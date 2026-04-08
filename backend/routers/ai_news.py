"""AI新闻路由"""
from fastapi import APIRouter, Query
from services.ai_news_service import get_ai_news, collect_ai_news

router = APIRouter()


@router.get("")
async def list_news(
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return {"items": get_ai_news(keyword, page, page_size)}


@router.post("/refresh")
async def refresh():
    count = await collect_ai_news()
    return {"collected": count}

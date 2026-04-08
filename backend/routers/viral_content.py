"""自媒体爆款路由"""
from fastapi import APIRouter, Query
from services.viral_service import get_viral_trending, get_viral_templates

router = APIRouter()


@router.get("/trending")
async def trending(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100)):
    return {"items": get_viral_trending(page, page_size)}


@router.get("/templates")
async def templates():
    return {"items": get_viral_templates()}

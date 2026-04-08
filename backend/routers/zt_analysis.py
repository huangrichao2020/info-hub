"""涨停分析路由"""
from fastapi import APIRouter, Query
from services.zt_service import get_zt_today, get_lianban, get_recent_zt, get_zt_report

router = APIRouter()


@router.get("/today")
async def today():
    return {"items": await get_zt_today()}


@router.get("/lianban")
async def lianban():
    return {"items": await get_lianban()}


@router.get("/recent")
async def recent(days: int = Query(7, ge=1, le=30)):
    return {"items": await get_recent_zt(days)}


@router.get("/report")
async def report(days: int = Query(7, ge=1, le=30)):
    content = await get_zt_report(days)
    return {"content": content}

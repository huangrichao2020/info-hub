"""
每日 S/A/B 机会扫描路由
"""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from services.daily_chance_scanner import (
    scan_daily_chance,
    get_stock_detail_for_chance,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/daily-chance", tags=["daily-chance"])


@router.get("/today")
async def get_today_chance():
    """
    获取今日 S/A/B 机会扫描结果
    """
    try:
        result = scan_daily_chance()
        return {"status": "ok", "data": result}
    except Exception as e:
        logger.error(f"daily chance scan error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{code}")
async def get_stock_chance_detail(code: str):
    """
    获取单只 S 级机会的详细数据
    """
    try:
        detail = get_stock_detail_for_chance(code)
        return {"status": "ok", "data": detail}
    except Exception as e:
        logger.error(f"stock chance detail error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chance_history(days: int = Query(7, ge=1, le=30)):
    """
    获取历史每日机会（暂用内存，可扩展 DB）
    """
    # TODO: 从 SQLite 读历史
    return {"status": "ok", "days": days, "history": []}
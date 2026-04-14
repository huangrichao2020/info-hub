"""AmazingData market data routes."""
from fastapi import APIRouter, Query

from services.quant_market_service import get_kline, get_multi_period_klines, get_quant_capabilities

router = APIRouter()


@router.get("/capabilities")
async def capabilities():
    return await get_quant_capabilities()


@router.get("/kline")
async def kline(
    code: str = Query(..., description="Security code, e.g. 600376.SH"),
    period: str = Query("minute", description="minute | 15min | hour | day"),
    begin_date: int = Query(..., description="YYYYMMDD"),
    end_date: int = Query(..., description="YYYYMMDD"),
):
    return await get_kline(code=code.upper(), period=period, begin_date=begin_date, end_date=end_date)


@router.get("/kline/multi")
async def multi_period_kline(
    code: str = Query(..., description="Security code, e.g. 600376.SH"),
    trade_date: int = Query(..., description="YYYYMMDD"),
):
    return await get_multi_period_klines(code=code.upper(), trade_date=trade_date)

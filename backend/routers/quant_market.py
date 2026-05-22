"""AmazingData market data routes."""
from fastapi import APIRouter, Query
from datetime import datetime

from services.quant_market_service import (
    get_kline,
    get_multi_period_klines,
    get_quant_capabilities,
    get_amazingdata_capabilities,
    get_amazingdata_daily_bars,
    _fetch_amazingdata_kline,
    AMAZINGDATA_HTTP_TUNNEL_URL,
    AMAZINGDATA_PUBLIC_BASE_URL,
)
import httpx

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


# ===== AmazingData 专用端点 =====

@router.get("/amazingdata/capabilities")
async def amazingdata_capabilities():
    """获取 AmazingData 能力信息"""
    return await get_amazingdata_capabilities()


@router.get("/amazingdata/daily-bars")
async def amazingdata_daily_bars(
    code: str = Query(..., description="Security code, e.g. 600519.SH"),
    begin_date: int = Query(None, description="开始日期 YYYYMMDD"),
    end_date: int = Query(None, description="结束日期 YYYYMMDD"),
    lookback_days: int = Query(30, description="回看天数（未传 begin_date 时）"),
):
    """AmazingData 日K快捷接口"""
    return await get_amazingdata_daily_bars(
        code=code.upper(),
        begin_date=begin_date,
        end_date=end_date,
        lookback_days=lookback_days,
    )


@router.get("/amazingdata/kline")
async def amazingdata_kline(
    code: str = Query(..., description="Security code, e.g. 600519.SH"),
    period: str = Query("day", description="day | week | month | min1 | min5 | min15 | min30 | min60"),
    begin_date: int = Query(None, description="开始日期 YYYYMMDD"),
    end_date: int = Query(None, description="结束日期 YYYYMMDD"),
    lookback_days: int = Query(30, description="回看天数"),
):
    """AmazingData K线接口（支持多周期）"""
    items = await _fetch_amazingdata_kline(
        code=code.upper(),
        period=period,
        begin_date=begin_date,
        end_date=end_date,
        lookback_days=lookback_days,
    )
    return {
        "code": code.upper(),
        "period": period,
        "source": "amazingdata",
        "count": len(items),
        "items": items,
    }


@router.get("/amazingdata/multi-period")
async def amazingdata_multi_period(
    code: str = Query(..., description="Security code, e.g. 600519.SH"),
    trade_date: int = Query(None, description="交易日期 YYYYMMDD，默认今天"),
):
    """获取 AmazingData 多周期K线（日线+60分钟+15分钟+1分钟）"""
    if trade_date is None:
        trade_date = int(datetime.now().strftime("%Y%m%d"))

    periods = {
        "day": {"period": "day", "lookback_days": 60},
        "min60": {"period": "min60", "lookback_days": 5},
        "min15": {"period": "min15", "lookback_days": 3},
        "min1": {"period": "min1", "lookback_days": 1},
    }

    results = {}
    for key, cfg in periods.items():
        items = await _fetch_amazingdata_kline(
            code=code.upper(),
            period=cfg["period"],
            lookback_days=cfg["lookback_days"],
        )
        results[key] = {
            "period": cfg["period"],
            "count": len(items),
            "items": items[:50] if cfg["period"].startswith("min") else items,  # 分钟数据截断
        }

    return {
        "code": code.upper(),
        "trade_date": trade_date,
        "source": "amazingdata",
        "series": results,
    }


@router.get("/amazingdata/source-status")
async def amazingdata_source_status():
    """检查 AmazingData 各数据源健康状态（本地隧道 vs 公网 relay）"""
    status = {
        "tunnel": {"url": AMAZINGDATA_HTTP_TUNNEL_URL, "status": "unknown", "items": 0},
        "public_relay": {"url": AMAZINGDATA_PUBLIC_BASE_URL, "status": "unknown", "items": 0},
    }

    # 检查本地隧道
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.get(f"{AMAZINGDATA_HTTP_TUNNEL_URL}/health")
            status["tunnel"]["status"] = "healthy" if resp.status_code == 200 else f"http_{resp.status_code}"
            status["tunnel"]["version"] = resp.json().get("version", "unknown")
    except Exception as e:
        status["tunnel"]["status"] = f"error: {str(e)[:50]}"

    # 检查公网 relay
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            resp = await client.get(f"{AMAZINGDATA_PUBLIC_BASE_URL}/health")
            status["public_relay"]["status"] = "healthy" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as e:
        status["public_relay"]["status"] = f"error: {str(e)[:50]}"

    # 数据验证（用平安银行测试）
    try:
        from services.quant_market_service import _fetch_amazingdata_kline
        items = await _fetch_amazingdata_kline("000001.SZ", "day", lookback_days=5)
        status["test_query"] = {"code": "000001.SZ", "items_returned": len(items)}
    except Exception as e:
        status["test_query"] = {"error": str(e)[:100]}

    return status

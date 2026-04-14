"""Lightweight HTTP API for AmazingData K-line data - minimal memory footprint."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

import AmazingData as ad
from fastapi import FastAPI, HTTPException, Query

# Account config
ACCOUNT = os.environ.get("AMAZINGDATA_ACCOUNT", "15300003409")
PASSWORD = os.environ.get("AMAZINGDATA_PASSWORD", "")
HOST = os.environ.get("AMAZINGDATA_HOST", "101.230.159.234")
FALLBACK_HOST = os.environ.get("AMAZINGDATA_FALLBACK_HOST", "140.206.44.234")
PORT = int(os.environ.get("AMAZINGDATA_PORT", "8600"))

app = FastAPI(title="AmazingData Light API", version="0.1.0")

_is_logged_in = False
_calendar_cache: list[int] | None = None


def ensure_login():
    global _is_logged_in
    if not _is_logged_in:
        if not PASSWORD:
            raise HTTPException(500, "AMAZINGDATA_PASSWORD not configured")
        ok = ad.login(username=ACCOUNT, password=PASSWORD, host=HOST, port=PORT)
        if not ok:
            ok = ad.login(username=ACCOUNT, password=PASSWORD, host=FALLBACK_HOST, port=PORT)
        if not ok:
            raise HTTPException(500, "Login failed - check password")
        _is_logged_in = True
    return True


def get_calendar() -> list[int]:
    global _calendar_cache
    if _calendar_cache is None:
        ensure_login()
        from AmazingData import BaseData
        _calendar_cache = BaseData().get_calendar()
    return _calendar_cache


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "amazingdata-light",
        "logged_in": _is_logged_in,
        "account": ACCOUNT,
    }


@app.get("/api/v1/capabilities")
async def capabilities():
    return {
        "provider": "amazingdata",
        "account": ACCOUNT,
        "host": HOST,
        "fallback_host": FALLBACK_HOST,
        "port": PORT,
        "supported_operations": ["calendar", "kline"],
        "periods": ["day", "week", "month", "min1", "min5", "min15", "min30", "min60"],
    }


@app.get("/api/v1/calendar")
async def calendar(market: str = Query("SH", description="SH/SZ/BJ")):
    ensure_login()
    cal = get_calendar()
    return {"market": market, "count": len(cal), "items": cal[-20:]}


@app.get("/api/v1/kline")
async def kline(
    code: str = Query(..., description="Security code, e.g. 600519.SH"),
    period: str = Query("day", description="day/week/month/min1/min5/min15/min30/min60"),
    begin_date: int = Query(..., description="YYYYMMDD"),
    end_date: int = Query(..., description="YYYYMMDD"),
):
    ensure_login()

    from AmazingData import MarketData, constant

    period_map = {
        "day": constant.Period.day.value,
        "week": constant.Period.week.value,
        "month": constant.Period.month.value,
        "min1": constant.Period.min1.value,
        "min5": constant.Period.min5.value,
        "min15": constant.Period.min15.value,
        "min30": constant.Period.min30.value,
        "min60": constant.Period.min60.value,
    }
    period_value = period_map.get(period)
    if period_value is None:
        raise HTTPException(400, f"Unsupported period: {period}. Use: {list(period_map.keys())}")

    cal = get_calendar()
    market = MarketData(cal)

    code_clean = code.split(".")[0] if "." in code else code

    try:
        result = market.query_kline(
            code_list=[code_clean],
            begin_date=begin_date,
            end_date=end_date,
            period=period_value,
        )
    except Exception as e:
        raise HTTPException(500, f"K-line query failed: {e}")

    if not result or code_clean not in result:
        return {"code": code, "period": period, "items": []}

    frame = result[code_clean]
    if hasattr(frame, "to_dict"):
        items = frame.to_dict(orient="records")
    elif hasattr(frame, "to_json"):
        items = json.loads(frame.to_json(orient="records"))
    else:
        items = list(frame) if frame else []

    return {"code": code, "period": period, "items": items}

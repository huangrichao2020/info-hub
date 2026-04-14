"""转强选股路由"""
from fastapi import APIRouter, Query

from services.turn_strong_service import (
    build_turn_strong_validation,
    ensure_turn_strong_run,
    generate_turn_strong_run,
    get_turn_strong_run,
    get_turn_strong_today_or_latest,
    list_recent_turn_strong_runs,
    refresh_turn_strong_run,
)

router = APIRouter()


@router.get("")
async def current():
    run = await ensure_turn_strong_run()
    if run:
        return run
    return {
        "status": "empty",
        "trade_date": "",
        "items": [],
        "market_snapshot": {},
        "overall_analysis": {},
        "key_pool": {"configured_keys": 0, "items": []},
    }


@router.get("/history")
async def history(date: str = Query("", description="YYYY-MM-DD")):
    if date:
        run = get_turn_strong_run(date)
    else:
        run = get_turn_strong_today_or_latest()
    if run:
        return run
    return {"status": "empty", "items": []}


@router.get("/history/list")
async def history_list(limit: int = Query(12, ge=1, le=60)):
    return {"items": list_recent_turn_strong_runs(limit)}


@router.get("/validation")
async def validation(date: str = Query(..., description="YYYY-MM-DD")):
    return await build_turn_strong_validation(date)


@router.post("/generate")
async def generate(force: bool = True):
    return await generate_turn_strong_run(force=force)


@router.post("/refresh")
async def refresh(date: str = Query("", description="YYYY-MM-DD")):
    return await refresh_turn_strong_run(date or None)

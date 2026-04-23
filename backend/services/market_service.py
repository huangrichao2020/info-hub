"""市场数据服务 - 包装 uwillberich market_data + capital_flow"""
import asyncio
import logging
import time

logger = logging.getLogger("info-hub.market")

_MARKET_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300


def _cache_get(key: str):
    entry = _MARKET_CACHE.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at <= time.monotonic():
        _MARKET_CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value):
    _MARKET_CACHE[key] = (time.monotonic() + _CACHE_TTL, value)
    return value


def _last_good(key: str):
    return _MARKET_CACHE.get(f"{key}:last_good", (0, None))[1]


def _set_last_good(key: str, value):
    _MARKET_CACHE[f"{key}:last_good"] = (float("inf"), value)
    return value


async def get_sector_movers(limit: int = 10, rising: bool = True) -> list[dict]:
    """获取板块涨跌排行"""
    cache_key = f"sector_movers:{limit}:{rising}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import market_data
        result = await asyncio.to_thread(market_data.fetch_sector_movers, limit, rising)
        data = result or []
        _set_last_good(cache_key, data)
        return _cache_set(cache_key, data)
    except Exception as e:
        logger.error(f"获取板块数据失败: {e}")
        return _last_good(cache_key) or []


async def get_index_snapshot() -> list[dict]:
    """获取大盘指数快照"""
    cache_key = "index_snapshot"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import market_data
        result = await asyncio.to_thread(market_data.fetch_index_snapshot)
        data = result or []
        _set_last_good(cache_key, data)
        return _cache_set(cache_key, data)
    except Exception as e:
        logger.error(f"获取指数数据失败: {e}")
        return _last_good(cache_key) or []


async def get_capital_flow() -> dict:
    """获取资金流向"""
    cache_key = "capital_flow"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import capital_flow
        result = await asyncio.to_thread(capital_flow.fetch_market_flow_snapshot)
        data = result or {}
        _set_last_good(cache_key, data)
        return _cache_set(cache_key, data)
    except Exception as e:
        logger.error(f"获取资金流向失败: {e}")
        return _last_good(cache_key) or {}


async def get_quotes(symbols: list[str]) -> list[dict]:
    """获取股票行情"""
    try:
        import market_data
        result = await asyncio.to_thread(market_data.fetch_tencent_quotes, symbols)
        return result or []
    except Exception as e:
        logger.error(f"获取行情失败: {e}")
        return []


async def get_sector_movers_fallback_from_turn_strong(limit: int = 10, rising: bool = True) -> list[dict]:
    try:
        from services.turn_strong_service import get_turn_strong_today_or_latest
    except Exception as exc:
        logger.error("转强池板块兜底加载失败: %s", exc)
        return []

    run = get_turn_strong_today_or_latest() or {}
    items = run.get("items") or []
    if not items:
        return []

    grouped: dict[str, dict] = {}
    for item in items:
        screen = item.get("screen") or {}
        concept = str(screen.get("style_concept") or "").split("、")[0].strip()
        name = concept or str(screen.get("industry") or "").strip() or "其他方向"
        payload = grouped.setdefault(
            name,
            {"name": name, "code": "", "change_pct": 0.0, "leader": item.get("name", ""), "count": 0},
        )
        payload["count"] += 1
        payload["change_pct"] += float(item.get("live_quote", {}).get("change_pct") or screen.get("change_pct") or 0)
        if not payload["leader"]:
            payload["leader"] = item.get("name", "")

    rows = list(grouped.values())
    for row in rows:
        count = max(1, row.pop("count", 1))
        row["change_pct"] = round(row["change_pct"] / count, 2)

    rows.sort(key=lambda row: row["change_pct"], reverse=rising)
    return rows[:limit]

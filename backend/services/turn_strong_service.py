"""转强选股服务"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from database import get_db
from llm.prompts import turn_strong_messages
from llm.qwen_client import chat
from services.market_service import get_index_snapshot, get_quotes, get_sector_movers
from services.quant_market_service import get_kline
from services.news_service import get_news

logger = logging.getLogger("info-hub.turn-strong")

CN_TZ = ZoneInfo("Asia/Shanghai")
MX_BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw"
MX_HEADERS = {"Content-Type": "application/json"}
MX_KEY_VARS = [
    "EM_API_KEY",
    "MX_APIKEY",
    "EM_API_KEY_BACKUP",
    "EM_API_KEY_3",
    "EM_API_KEY_4",
    "EM_API_KEY_5",
]
MX_DAILY_QUOTA_PER_KEY = 20
CACHE_TTL_SECONDS = 120
_CACHE: dict[str, tuple[float, Any]] = {}
IWENCAI_QUERY_URL = f"{os.environ.get('IWENCAI_BASE_URL', 'https://openapi.iwencai.com').rstrip('/')}/v1/query2data"


def build_turn_strong_screen_query() -> str:
    return build_turn_strong_screen_queries()[0]


def build_turn_strong_screen_queries() -> list[str]:
    base_fields = "返回所属概念 行业 换手率 成交额 总市值 流通市值 量比 按今日竞价量比从高到低排序"
    return [
        (
            "A股 主板股票 前一交易日筹码获利比例小于60 "
            "今日高开超过0.5% 今日筹码获利比例大于60 "
            f"{base_fields}"
        ),
        (
            "A股 主板股票 前一交易日筹码获利比例小于65 "
            "今日高开大于0 今日筹码获利比例大于55 "
            f"{base_fields}"
        ),
        (
            "A股 主板股票 前一交易日筹码获利比例小于70 "
            "今日高开大于0 "
            f"{base_fields}"
        ),
    ]


def build_iwencai_turn_strong_queries() -> list[str]:
    base_fields = "返回所属概念 所属行业 换手率 成交额 总市值 流通市值 竞价量比 竞价涨跌幅"
    return [
        f"A股 主板 非ST 今日高开大于0 {base_fields} 按竞价量比从高到低排序",
        f"A股 非ST 今日高开大于0 {base_fields} 按竞价量比从高到低排序",
    ]


def _now_cn() -> datetime:
    return datetime.now(CN_TZ)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_cn() -> str:
    return _now_cn().strftime("%Y-%m-%d")


def _cache_get(key: str) -> Any | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at <= time.monotonic():
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> Any:
    _CACHE[key] = (time.monotonic() + ttl, value)
    return value


def _cache_invalidate(prefix: str) -> None:
    keys = [key for key in _CACHE if key.startswith(prefix)]
    for key in keys:
        _CACHE.pop(key, None)


def _build_iwencai_headers() -> dict[str, str]:
    api_key = os.environ.get("IWENCAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("IWENCAI_API_KEY 未配置")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _is_weekday() -> bool:
    return _now_cn().weekday() < 5


def _loads_json(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _find_key(row: dict[str, Any], prefix: str) -> str | None:
    for key in row:
        if key.startswith(prefix):
            return key
    return None


def _extract_key_date(key: str) -> str | None:
    match = re.search(r"\{(\d{4}-\d{2}-\d{2})\}", key)
    if match:
        return match.group(1)
    return None


def extract_dates_from_screen_columns(columns: list[dict[str, Any]]) -> dict[str, str]:
    profit_dates = sorted(
        {
            date
            for column in columns
            for key in [column.get("key", "")]
            for date in [_extract_key_date(key)]
            if key.startswith("010000_HLP") and date
        }
    )
    current_dates = sorted(
        {
            date
            for column in columns
            for key in [column.get("key", "")]
            for date in [_extract_key_date(key)]
            if key.startswith("010000_AUC_VOLUME_RATIO") and date
        }
    )
    trade_date = current_dates[-1] if current_dates else (profit_dates[-1] if profit_dates else "")
    previous_trade_date = ""
    if profit_dates:
        previous_trade_date = profit_dates[0] if len(profit_dates) == 1 else profit_dates[-2]
        if not trade_date:
            trade_date = profit_dates[-1]

    return {
        "trade_date": trade_date,
        "previous_trade_date": previous_trade_date,
    }


def normalize_turn_strong_candidates(screen_payload: dict[str, Any]) -> dict[str, Any]:
    columns = screen_payload.get("columns") or []
    rows = screen_payload.get("rows") or []
    dates = extract_dates_from_screen_columns(columns)
    trade_date = dates["trade_date"]
    previous_trade_date = dates["previous_trade_date"]

    current_profit_key = f"010000_HLP<70>{{{trade_date}}}" if trade_date else _find_key(rows[0], "010000_HLP<70>") if rows else None
    previous_profit_key = (
        f"010000_HLP<70>{{{previous_trade_date}}}"
        if previous_trade_date
        else None
    )
    auction_volume_key = f"010000_AUC_VOLUME_RATIO{{{trade_date}}}" if trade_date else None
    auction_change_key = f"010000_AUC_RANGE{{{trade_date}}}" if trade_date else None
    volume_ratio_key = f"010000_LIANGBI<70>{{{trade_date}}}" if trade_date else None
    turnover_key = f"010000_TURNOVER_RATE<70>{{{trade_date}}}" if trade_date else None
    trading_amount_key = f"010000_TRADING_VOLUMES<70>{{{trade_date}}}" if trade_date else None
    total_mv_key = f"010000_TOAL_MARKET_VALUE<70>{{{trade_date}}}" if trade_date else None
    circulation_mv_key = f"010000_CIRCULATION_MARKET_VALUE<70>{{{trade_date}}}" if trade_date else None

    items: list[dict[str, Any]] = []
    for row in rows:
        board_key = _find_key(row, "010000_CUSTOM_TRADEMARKET_TRADEMARKET_")
        item = {
            "rank": int(float(row.get("SERIAL", 0) or 0)),
            "code": row.get("SECURITY_CODE", ""),
            "name": row.get("SECURITY_SHORT_NAME", "") or row.get("MARKET_SHORT_NAME", ""),
            "market": row.get("MARKET_SHORT_NAME", ""),
            "screen": {
                "board": row.get(board_key, "") if board_key else "",
                "industry": row.get("INDUSTRY", "") or row.get("SW_INDUSTRY", "") or row.get("010000_RPT_F10_ORG_BASICINFO_BOARD_NAME_TOTAL_BOARD_NAME_TOTAL_", ""),
                "style_concept": row.get("STYLE_CONCEPT", ""),
                "previous_profit_ratio": _to_float(row.get(previous_profit_key, "")) if previous_profit_key else None,
                "current_profit_ratio": _to_float(row.get(current_profit_key, "")) if current_profit_key else None,
                "auction_volume_ratio": _to_float(row.get(auction_volume_key, "")) if auction_volume_key else None,
                "auction_change_pct": _to_float(row.get(auction_change_key, "")) if auction_change_key else None,
                "latest_price": _to_float(row.get("NEWEST_PRICE")),
                "change_pct": _to_float(row.get("CHG")),
                "volume_ratio": _to_float(row.get(volume_ratio_key, "")) if volume_ratio_key else None,
                "turnover_rate": _to_float(row.get(turnover_key, "")) if turnover_key else None,
                "trading_amount": row.get(trading_amount_key, "") if trading_amount_key else "",
                "total_market_value": row.get(total_mv_key, "") if total_mv_key else "",
                "circulation_market_value": row.get(circulation_mv_key, "") if circulation_mv_key else "",
            },
            "news_items": [],
            "analysis": {},
            "live_quote": {},
            "intraday_status": {},
        }
        items.append(item)

    return {
        "trade_date": trade_date,
        "previous_trade_date": previous_trade_date,
        "conditions": screen_payload.get("conditions") or [],
        "items": items,
    }


def _load_mx_keys() -> list[dict[str, str]]:
    keys: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in MX_KEY_VARS:
        value = os.environ.get(name, "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        keys.append({"name": name, "value": value})
    return keys


def _load_key_usage(usage_date: str) -> dict[str, dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key_name, request_count, quota_exhausted, last_used_at, last_error FROM mx_key_usage WHERE usage_date = ?",
            (usage_date,),
        ).fetchall()
    return {row["key_name"]: dict(row) for row in rows}


def choose_next_mx_key(keys: list[dict[str, str]], usage: dict[str, dict[str, Any]]) -> dict[str, str] | None:
    available = []
    for key in keys:
        meta = usage.get(key["name"], {})
        request_count = int(meta.get("request_count") or 0)
        quota_exhausted = int(meta.get("quota_exhausted") or 0)
        if quota_exhausted or request_count >= MX_DAILY_QUOTA_PER_KEY:
            continue
        available.append((request_count, meta.get("last_used_at") or "", key["name"], key))

    if not available:
        return None

    available.sort(key=lambda item: (item[0], item[1], item[2]))
    return available[0][3]


def _upsert_key_usage(
    usage_date: str,
    key_name: str,
    *,
    increment: bool = False,
    quota_exhausted: bool | None = None,
    last_error: str | None = None,
) -> None:
    now_iso = _utc_now_iso()
    with get_db() as conn:
        row = conn.execute(
            "SELECT request_count, quota_exhausted FROM mx_key_usage WHERE usage_date = ? AND key_name = ?",
            (usage_date, key_name),
        ).fetchone()
        request_count = int(row["request_count"]) if row else 0
        exhausted = int(row["quota_exhausted"]) if row else 0
        if increment:
            request_count += 1
        if quota_exhausted is not None:
            exhausted = 1 if quota_exhausted else 0
            if exhausted:
                request_count = max(request_count, MX_DAILY_QUOTA_PER_KEY)

        conn.execute(
            """
            INSERT INTO mx_key_usage (usage_date, key_name, request_count, quota_exhausted, last_used_at, last_error)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(usage_date, key_name) DO UPDATE SET
                request_count = excluded.request_count,
                quota_exhausted = excluded.quota_exhausted,
                last_used_at = excluded.last_used_at,
                last_error = excluded.last_error
            """,
            (usage_date, key_name, request_count, exhausted, now_iso, last_error or ""),
        )


def _post_mx_json(path: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    usage_date = _today_cn()
    keys = _load_mx_keys()
    usage = _load_key_usage(usage_date)
    attempted: set[str] = set()
    last_error: Exception | None = None
    last_result: dict[str, Any] | None = None

    while len(attempted) < len(keys):
        key = choose_next_mx_key(
            [item for item in keys if item["name"] not in attempted],
            usage,
        )
        if not key:
            break

        attempted.add(key["name"])
        request = urllib.request.Request(
            f"{MX_BASE_URL}/{path.lstrip('/')}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={**MX_HEADERS, "apikey": key["value"]},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception as exc:  # pragma: no cover - network errors are environment-specific
            last_error = exc
            usage[key["name"]] = {
                **usage.get(key["name"], {}),
                "last_error": str(exc),
            }
            _upsert_key_usage(usage_date, key["name"], last_error=str(exc))
            continue

        if isinstance(result, dict) and result.get("status") == 113:
            last_result = result
            usage[key["name"]] = {
                **usage.get(key["name"], {}),
                "request_count": MX_DAILY_QUOTA_PER_KEY,
                "quota_exhausted": 1,
            }
            _upsert_key_usage(usage_date, key["name"], quota_exhausted=True, last_error="quota_exceeded")
            continue

        _upsert_key_usage(usage_date, key["name"], increment=True, last_error="")
        return result

    if last_result is not None:
        return last_result
    if last_error is not None:
        raise last_error
    raise RuntimeError("没有可用的 MX API key 配额")


def _unwrap_mx_response(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    while isinstance(data, dict) and "data" in data:
        next_data = data.get("data")
        if next_data is None:
            break
        data = next_data
    return data if isinstance(data, dict) else {}


def _mx_stock_screen(keyword: str, page_size: int = 80) -> dict[str, Any]:
    response = _post_mx_json(
        "stock-screen",
        {"keyword": keyword, "pageNo": 1, "pageSize": page_size},
    )
    data = _unwrap_mx_response(response)
    result = ((data.get("allResults") or {}).get("result")) or {}
    return {
        "keyword": keyword,
        "response_code": data.get("responseCode"),
        "reflect_result": data.get("reflectResult"),
        "security_count": data.get("securityCount"),
        "conditions": data.get("responseConditionList") or [],
        "columns": result.get("columns") or [],
        "rows": result.get("dataList") or [],
        "raw": response,
    }


def _mx_news_search(query: str, size: int = 3) -> list[dict[str, Any]]:
    response = _post_mx_json("news-search", {"query": query, "size": size})
    data = _unwrap_mx_response(response)
    return ((data.get("llmSearchResponse") or {}).get("data")) or []


def _post_iwencai_query(query: str, page: int = 1, limit: int = 80) -> dict[str, Any]:
    request = urllib.request.Request(
        IWENCAI_QUERY_URL,
        data=json.dumps(
            {
                "query": query,
                "page": str(page),
                "limit": str(limit),
                "is_cache": "1",
                "expand_index": "true",
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers=_build_iwencai_headers(),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8", errors="replace"))
    if isinstance(result, dict) and result.get("status_code") not in (None, 0):
        raise RuntimeError(f"问财返回错误: {result.get('status_msg', '未知错误')}")
    return result if isinstance(result, dict) else {}


def _pick_first(row: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _pick_by_contains(row: dict[str, Any], tokens: list[str]) -> Any:
    for key, value in row.items():
        if value in (None, ""):
            continue
        if all(token in key for token in tokens):
            return value
    return None


def _normalize_iwencai_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("datas") or []
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        code = _pick_first(row, ["股票代码", "code", "证券代码", "SECURITY_CODE"])
        name = _pick_first(row, ["股票简称", "name", "证券简称", "SECURITY_NAME_ABBR"])
        if not code or not name:
            continue
        industry = _pick_first(row, ["所属同花顺行业", "所属行业", "行业", "申万一级行业"])
        concept = _pick_first(row, ["所属概念", "概念", "概念板块"])
        latest_price = _pick_first(row, ["最新价", "现价", "收盘价"])
        auction_change = _pick_by_contains(row, ["竞价", "涨跌幅"]) or _pick_first(row, ["今日高开幅度", "高开幅度"])
        auction_volume_ratio = _pick_by_contains(row, ["竞价", "量比"]) or _pick_first(row, ["量比"])
        current_profit = _pick_by_contains(row, ["今日", "筹码获利比例"]) or _pick_first(row, ["筹码获利比例"])
        previous_profit = _pick_by_contains(row, ["前一交易日", "筹码获利比例"])
        turnover_rate = _pick_first(row, ["换手率"])
        trading_amount = _pick_first(row, ["成交额"])
        total_market_value = _pick_first(row, ["总市值"])
        circulation_market_value = _pick_first(row, ["流通市值"])
        normalized.append(
            {
                "rank": index,
                "code": str(code),
                "name": str(name),
                "market": "",
                "screen": {
                    "board": "问财A股",
                    "industry": str(industry or ""),
                    "style_concept": str(concept or ""),
                    "previous_profit_ratio": _to_float(previous_profit),
                    "current_profit_ratio": _to_float(current_profit),
                    "auction_volume_ratio": _to_float(auction_volume_ratio),
                    "auction_change_pct": _to_float(auction_change),
                    "latest_price": _to_float(latest_price),
                    "change_pct": None,
                    "volume_ratio": _to_float(auction_volume_ratio),
                    "turnover_rate": _to_float(turnover_rate),
                    "trading_amount": str(trading_amount or ""),
                    "total_market_value": str(total_market_value or ""),
                    "circulation_market_value": str(circulation_market_value or ""),
                },
                "news_items": [],
                "analysis": {},
                "live_quote": {},
                "intraday_status": {},
                "source_tags": ["问财A股"],
            }
        )
    return normalized


def _build_news_query(item: dict[str, Any]) -> str:
    screen = item.get("screen") or {}
    industry = str(screen.get("industry") or "").split("-")[-1].strip()
    name = item.get("name", "")
    code = item.get("code", "")
    if industry:
        return f"{name} {code} {industry} 最新公告 最新资讯"
    return f"{name} {code} 最新公告 最新资讯"


def _normalize_news_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "date": item.get("date", ""),
        "url": item.get("jumpUrl", ""),
        "type": item.get("informationType", ""),
    }


def _fallback_local_news(item: dict[str, Any], limit: int = 2) -> list[dict[str, Any]]:
    rows = get_news(keyword=item.get("name", ""), hours=72, page_size=limit)
    return [
        {
            "title": row.get("title", ""),
            "source": row.get("source", ""),
            "date": row.get("published_at") or row.get("collected_at", ""),
            "url": row.get("url", ""),
            "type": "local-fin-news",
        }
        for row in rows[:limit]
    ]


def _symbol_for_quote(code: str) -> str:
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("0", "3")):
        return f"sz{code}"
    if code.startswith("8"):
        return f"bj{code}"
    return code


def _code_for_daily_kline(code: str) -> str:
    code = code.strip().upper()
    if code.endswith((".SH", ".SZ", ".BJ")):
        return code
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    if code.startswith("8"):
        return f"{code}.BJ"
    return code


def _is_excluded_candidate(item: dict[str, Any]) -> bool:
    name = str(item.get("name") or "").upper()
    board = str((item.get("screen") or {}).get("board") or "")
    concept = str((item.get("screen") or {}).get("style_concept") or "")
    exclusion_tokens = ["ST", "*ST", "风险警示", "退市整理"]
    if any(token in name for token in exclusion_tokens):
        return True
    if any(token in board for token in exclusion_tokens):
        return True
    if "退市" in concept and "整理" in concept:
        return True
    return False


def _build_market_snapshot(indices: list[dict[str, Any]], risers: list[dict[str, Any]], fallers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "indices": indices,
        "top_risers": risers,
        "top_fallers": fallers,
    }


def _build_intraday_status(screen: dict[str, Any], live_quote: dict[str, Any]) -> dict[str, Any]:
    live_change = _to_float(live_quote.get("change_pct")) or 0
    screen_change = _to_float(screen.get("change_pct")) or 0
    live_price = _to_float(live_quote.get("price"))
    screen_price = _to_float(screen.get("latest_price"))

    label = "待观察"
    summary = "盘中承接一般，优先等量价确认。"
    if live_change >= max(screen_change, 0) + 2:
        label = "转强扩散"
        summary = "盘中涨幅继续抬升，说明竞价强势得到资金接力。"
    elif live_change >= max(screen_change - 1, 0):
        label = "强势承接"
        summary = "盘中仍维持红盘和相对强势，适合继续观察承接。"
    elif live_change >= 0:
        label = "冲高回落"
        summary = "竞价优势仍在，但盘中追价资金不足，谨防回落。"
    else:
        label = "转弱"
        summary = "盘中已经翻绿或明显低于竞价预期，强度在衰减。"

    if live_price is not None and screen_price is not None:
        delta = round(live_price - screen_price, 2)
    else:
        delta = None

    return {
        "label": label,
        "summary": summary,
        "price_delta_from_screen": delta,
        "updated_at": _utc_now_iso(),
    }


def _date_to_int(date_str: str) -> int:
    return int(date_str.replace("-", ""))


def _int_to_date(value: int) -> str:
    text = str(value)
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def _extract_bar_date(item: dict[str, Any]) -> str:
    timestamp = str(item.get("timestamp") or "")
    if len(timestamp) >= 10:
        return timestamp[:10]
    return timestamp


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_validation_row(item: dict[str, Any], next_bar: dict[str, Any] | None) -> dict[str, Any]:
    screen = item.get("screen") or {}
    entry_price = _safe_float(screen.get("latest_price"))

    if not next_bar or entry_price in (None, 0):
        return {
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "entry_price": entry_price,
            "next_trade_date": next_bar.get("timestamp", "")[:10] if next_bar else "",
            "next_open": _safe_float(next_bar.get("open")) if next_bar else None,
            "next_close": _safe_float(next_bar.get("close")) if next_bar else None,
            "next_high": _safe_float(next_bar.get("high")) if next_bar else None,
            "close_change_pct": None,
            "max_gain_pct": None,
            "verdict": "insufficient",
            "note": "缺少下一交易日K线，暂时无法验证。",
        }

    next_open = _safe_float(next_bar.get("open"))
    next_close = _safe_float(next_bar.get("close"))
    next_high = _safe_float(next_bar.get("high"))

    close_change_pct = ((next_close - entry_price) / entry_price * 100) if next_close is not None else None
    max_gain_pct = ((next_high - entry_price) / entry_price * 100) if next_high is not None else None

    verdict = "flat"
    note = "次日表现平平，说明转强信号延续性一般。"
    if max_gain_pct is not None and max_gain_pct >= 5:
        verdict = "success"
        note = "次日出现明显溢价，高点兑现空间充足。"
    elif close_change_pct is not None and close_change_pct >= 2:
        verdict = "success"
        note = "次日收盘仍有正向收益，转强有效。"
    elif close_change_pct is not None and close_change_pct <= -2:
        verdict = "fail"
        note = "次日明显走弱，竞价强度未能转化为持续性。"
    elif close_change_pct is not None and close_change_pct < 0:
        verdict = "weak"
        note = "次日冲高承接不足，结果偏弱。"

    return {
        "code": item.get("code", ""),
        "name": item.get("name", ""),
        "entry_price": round(entry_price, 2),
        "next_trade_date": _extract_bar_date(next_bar),
        "next_open": round(next_open, 2) if next_open is not None else None,
        "next_close": round(next_close, 2) if next_close is not None else None,
        "next_high": round(next_high, 2) if next_high is not None else None,
        "close_change_pct": round(close_change_pct, 2) if close_change_pct is not None else None,
        "max_gain_pct": round(max_gain_pct, 2) if max_gain_pct is not None else None,
        "verdict": verdict,
        "note": note,
    }


def _merge_live_quotes(items: list[dict[str, Any]], quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quote_map = {quote.get("code"): quote for quote in quotes}
    merged: list[dict[str, Any]] = []
    for item in items:
        candidate = dict(item)
        quote = quote_map.get(candidate.get("code"))
        if quote:
            candidate["live_quote"] = quote
            candidate["intraday_status"] = _build_intraday_status(candidate.get("screen") or {}, quote)
        merged.append(candidate)
    return merged


def _merge_candidate_sources(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def ingest(item: dict[str, Any], source_label: str) -> None:
        code = str(item.get("code") or "").strip()
        if not code:
            return
        candidate = dict(item)
        source_tags = list(candidate.get("source_tags") or [])
        if source_label not in source_tags:
            source_tags.append(source_label)
        candidate["source_tags"] = source_tags

        existing = merged.get(code)
        if not existing:
            merged[code] = candidate
            return

        existing_tags = list(existing.get("source_tags") or [])
        for tag in source_tags:
            if tag not in existing_tags:
                existing_tags.append(tag)
        existing["source_tags"] = existing_tags

        existing_screen = existing.get("screen") or {}
        candidate_screen = candidate.get("screen") or {}
        for key, value in candidate_screen.items():
            if existing_screen.get(key) in (None, "", 0) and value not in (None, "", 0):
                existing_screen[key] = value
        existing["screen"] = existing_screen

        if not existing.get("name") and candidate.get("name"):
            existing["name"] = candidate["name"]

    for item in primary:
        ingest(item, "妙想")
    for item in secondary:
        ingest(item, "问财A股")

    items = list(merged.values())
    items.sort(
        key=lambda item: (
            -(item.get("screen", {}).get("auction_volume_ratio") or 0),
            -(item.get("screen", {}).get("auction_change_pct") or 0),
            item.get("rank", 9999),
        )
    )
    for index, item in enumerate(items, start=1):
        item["rank"] = index
    return items


def extract_json_payload(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise json.JSONDecodeError("未找到有效 JSON", text, 0)


def _fallback_overall_analysis(items: list[dict[str, Any]]) -> dict[str, Any]:
    analyses = []
    for item in items:
        screen = item.get("screen") or {}
        recommendation = "watch"
        verdict = "更适合盘中确认后再决策"
        if str(item.get("name", "")).startswith(("ST", "*ST")) or "风险警示板" in str(screen.get("board", "")):
            recommendation = "avoid"
            verdict = "风险警示属性过强，不符合常规转强博弈。"
        analyses.append(
            {
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "recommendation": recommendation,
                "recommendation_label": {"buy": "建议买入", "watch": "观察为主", "avoid": "不建议买入"}[recommendation],
                "logic_support": f"竞价量比 {screen.get('auction_volume_ratio') or '--'}，高开 {screen.get('auction_change_pct') or '--'}%，获利盘由 {screen.get('previous_profit_ratio') or '--'}% 提升到 {screen.get('current_profit_ratio') or '--'}%。",
                "news_support": "未能稳定提取结构化新闻，先按盘面逻辑处理。",
                "methodology_view": verdict,
                "risk_flags": ["需要关注开盘后承接是否延续", "若快速跌破竞价强度则放弃"],
                "execution_plan": "只在分时放量回踩不破时考虑跟随，追高需严格控仓。",
            }
        )
    return {
        "market_summary": "竞价转强池已生成，但结构化分析回退到规则版摘要。",
        "analyses": analyses,
    }


async def _generate_llm_analysis(items: list[dict[str, Any]], market_snapshot: dict[str, Any]) -> dict[str, Any]:
    if not items:
        return {"market_summary": "今日未筛出符合条件的主板转强股。", "analyses": []}

    compact_items = []
    for item in items:
        screen = item.get("screen") or {}
        compact_items.append(
            {
                "code": item.get("code"),
                "name": item.get("name"),
                "industry": screen.get("industry"),
                "concept": screen.get("style_concept"),
                "board": screen.get("board"),
                "auction_volume_ratio": screen.get("auction_volume_ratio"),
                "auction_change_pct": screen.get("auction_change_pct"),
                "previous_profit_ratio": screen.get("previous_profit_ratio"),
                "current_profit_ratio": screen.get("current_profit_ratio"),
                "latest_price": screen.get("latest_price"),
                "change_pct": screen.get("change_pct"),
                "turnover_rate": screen.get("turnover_rate"),
                "volume_ratio": screen.get("volume_ratio"),
                "trading_amount": screen.get("trading_amount"),
                "news_items": item.get("news_items") or [],
            }
        )

    messages = turn_strong_messages(compact_items, market_snapshot)
    try:
        raw = await chat(messages, temperature=0.2, max_tokens=8192)
    except Exception as exc:
        logger.warning("转强选股大模型分析失败，回退到规则摘要: %s", exc)
        payload = _fallback_overall_analysis(items)
        payload["raw_text"] = repr(exc)
        return payload
    try:
        payload = extract_json_payload(raw)
    except json.JSONDecodeError:
        logger.warning("转强选股分析 JSON 解析失败，回退到规则摘要")
        payload = _fallback_overall_analysis(items)
        payload["raw_text"] = raw
    return payload


def _apply_analysis(items: list[dict[str, Any]], overall_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    analysis_rows = overall_analysis.get("analyses") or []
    analysis_map: dict[str, dict[str, Any]] = {}
    for row in analysis_rows:
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        if code:
            analysis_map[code] = row
        elif name:
            analysis_map[name] = row

    merged = []
    for item in items:
        key = item.get("code") or item.get("name")
        candidate = dict(item)
        candidate["analysis"] = analysis_map.get(key, {})
        merged.append(candidate)
    return merged


def _serialize_run_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["conditions"] = _loads_json(data.pop("conditions_json", ""), [])
    data["market_snapshot"] = _loads_json(data.pop("market_snapshot_json", ""), {})
    data["items"] = _loads_json(data.pop("candidates_json", ""), [])
    data["overall_analysis"] = _loads_json(data.pop("overall_analysis_json", ""), {})
    data["key_pool"] = get_mx_key_pool_summary(data.get("trade_date") or _today_cn())
    return data


def _save_turn_strong_run(run_payload: dict[str, Any]) -> dict[str, Any]:
    now_iso = _utc_now_iso()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, generated_at FROM turn_strong_runs WHERE trade_date = ?",
            (run_payload["trade_date"],),
        ).fetchone()
        generated_at = existing["generated_at"] if existing else now_iso
        conn.execute(
            """
            INSERT INTO turn_strong_runs (
                trade_date,
                previous_trade_date,
                screening_query,
                status,
                selection_total,
                generated_at,
                refreshed_at,
                conditions_json,
                market_snapshot_json,
                candidates_json,
                overall_analysis_json,
                last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date) DO UPDATE SET
                previous_trade_date = excluded.previous_trade_date,
                screening_query = excluded.screening_query,
                status = excluded.status,
                selection_total = excluded.selection_total,
                refreshed_at = excluded.refreshed_at,
                conditions_json = excluded.conditions_json,
                market_snapshot_json = excluded.market_snapshot_json,
                candidates_json = excluded.candidates_json,
                overall_analysis_json = excluded.overall_analysis_json,
                last_error = excluded.last_error
            """,
            (
                run_payload["trade_date"],
                run_payload.get("previous_trade_date", ""),
                run_payload.get("screening_query", build_turn_strong_screen_query()),
                run_payload.get("status", "ready"),
                len(run_payload.get("items") or []),
                generated_at,
                now_iso,
                json.dumps(run_payload.get("conditions") or [], ensure_ascii=False),
                json.dumps(run_payload.get("market_snapshot") or {}, ensure_ascii=False),
                json.dumps(run_payload.get("items") or [], ensure_ascii=False),
                json.dumps(run_payload.get("overall_analysis") or {}, ensure_ascii=False),
                run_payload.get("last_error", ""),
            ),
        )
        row = conn.execute(
            "SELECT * FROM turn_strong_runs WHERE trade_date = ?",
            (run_payload["trade_date"],),
        ).fetchone()
    serialized = _serialize_run_row(row)
    _cache_invalidate("turn_strong_run:")
    _cache_invalidate("turn_strong_history:")
    _cache_invalidate("turn_strong_validation:")
    return serialized


def get_mx_key_pool_summary(usage_date: str | None = None) -> dict[str, Any]:
    usage_date = usage_date or _today_cn()
    keys = _load_mx_keys()
    usage = _load_key_usage(usage_date)
    items = []
    used = 0
    for key in keys:
        meta = usage.get(key["name"], {})
        request_count = int(meta.get("request_count") or 0)
        used += min(request_count, MX_DAILY_QUOTA_PER_KEY)
        items.append(
            {
                "name": key["name"],
                "request_count": request_count,
                "remaining": max(0, MX_DAILY_QUOTA_PER_KEY - request_count),
                "quota_exhausted": bool(int(meta.get("quota_exhausted") or 0)),
                "last_used_at": meta.get("last_used_at") or "",
            }
        )

    return {
        "usage_date": usage_date,
        "configured_keys": len(keys),
        "daily_quota_per_key": MX_DAILY_QUOTA_PER_KEY,
        "total_daily_quota": len(keys) * MX_DAILY_QUOTA_PER_KEY,
        "used_requests": used,
        "items": items,
    }


async def generate_turn_strong_run(force: bool = False) -> dict[str, Any]:
    today = _today_cn()
    if not force:
        existing = get_turn_strong_run(today)
        if existing:
            return existing

    normalized: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    screen_query = ""
    iwencai_items: list[dict[str, Any]] = []
    iwencai_query_used = ""
    for iw_query in build_iwencai_turn_strong_queries():
        try:
            iwencai_payload = await asyncio.to_thread(_post_iwencai_query, iw_query, 1, 80)
            iwencai_items = _normalize_iwencai_candidates(iwencai_payload)
            if iwencai_items:
                iwencai_query_used = iw_query
                break
        except Exception as exc:
            logger.warning("问财A股转强验证查询失败: %s", exc)
            continue

    for candidate_query in build_turn_strong_screen_queries():
        screen_query = candidate_query
        screen_payload = await asyncio.to_thread(_mx_stock_screen, candidate_query, 80)
        mx_normalized = normalize_turn_strong_candidates(screen_payload) if isinstance(screen_payload, dict) else {"trade_date": today, "previous_trade_date": "", "conditions": [], "items": []}
        normalized = mx_normalized
        items = [item for item in _merge_candidate_sources(mx_normalized["items"], iwencai_items) if not _is_excluded_candidate(item)]
        if items:
            break
    if normalized is None:
        normalized = {"trade_date": today, "previous_trade_date": "", "conditions": [], "items": []}

    indices, risers, fallers = await asyncio.gather(
        get_index_snapshot(),
        get_sector_movers(8, True),
        get_sector_movers(8, False),
    )
    market_snapshot = _build_market_snapshot(indices, risers, fallers)

    if items:
        symbols = [_symbol_for_quote(item["code"]) for item in items]
        quotes = await get_quotes(symbols)
        items = _merge_live_quotes(items, quotes)

        for item in items:
            try:
                news_items = await asyncio.to_thread(_mx_news_search, _build_news_query(item), 3)
                item["news_items"] = [_normalize_news_item(news) for news in news_items[:3]]
            except Exception as exc:  # pragma: no cover - depends on network/provider state
                logger.warning("转强选股新闻抓取失败 %s(%s): %s", item.get("name"), item.get("code"), exc)
                item["news_items"] = []
            if not item["news_items"]:
                item["news_items"] = _fallback_local_news(item)

    overall_analysis = await _generate_llm_analysis(items, market_snapshot)
    items = _apply_analysis(items, overall_analysis)

    return _save_turn_strong_run(
        {
            "trade_date": normalized.get("trade_date") or today,
            "previous_trade_date": normalized.get("previous_trade_date", ""),
            "screening_query": screen_query if not iwencai_query_used else f"妙想: {screen_query}\n问财: {iwencai_query_used}",
            "status": "ready",
            "conditions": normalized.get("conditions") or [],
            "market_snapshot": market_snapshot,
            "items": items,
            "overall_analysis": overall_analysis,
            "last_error": "",
        }
    )


def get_turn_strong_run(trade_date: str | None = None) -> dict[str, Any] | None:
    cache_key = f"turn_strong_run:{trade_date or 'latest'}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    with get_db() as conn:
        if trade_date:
            row = conn.execute(
                "SELECT * FROM turn_strong_runs WHERE trade_date = ?",
                (trade_date,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM turn_strong_runs ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
    if not row:
        return None
    return _cache_set(cache_key, _serialize_run_row(row))


def get_turn_strong_today_or_latest() -> dict[str, Any] | None:
    today = get_turn_strong_run(_today_cn())
    if today:
        return today
    return get_turn_strong_run()


def list_recent_turn_strong_runs(limit: int = 12) -> list[dict[str, Any]]:
    cache_key = f"turn_strong_history:list:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT trade_date, generated_at, refreshed_at, status, selection_total
            FROM turn_strong_runs
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return _cache_set(cache_key, [dict(row) for row in rows])


async def build_turn_strong_validation(trade_date: str) -> dict[str, Any]:
    cache_key = f"turn_strong_validation:{trade_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    run = get_turn_strong_run(trade_date)
    if not run:
        return {"status": "empty", "trade_date": trade_date, "items": [], "summary": {}}

    begin_date = _date_to_int(trade_date)
    end_date = int((datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y%m%d"))

    async def fetch_next_bar(item: dict[str, Any]) -> dict[str, Any]:
        try:
            series = await get_kline(
                code=_code_for_daily_kline(str(item.get("code", ""))),
                period="day",
                begin_date=begin_date,
                end_date=end_date,
            )
            bars = series.get("items") or []
            next_bar = next((bar for bar in bars if _extract_bar_date(bar) > trade_date), None)
        except Exception:
            next_bar = None
        return _build_validation_row(item, next_bar)

    rows = await asyncio.gather(*(fetch_next_bar(item) for item in (run.get("items") or [])))
    success_count = sum(1 for row in rows if row["verdict"] == "success")
    fail_count = sum(1 for row in rows if row["verdict"] == "fail")
    avg_close = round(
        sum(row["close_change_pct"] for row in rows if row["close_change_pct"] is not None) /
        max(1, len([row for row in rows if row["close_change_pct"] is not None])),
        2,
    ) if rows else 0.0
    avg_max = round(
        sum(row["max_gain_pct"] for row in rows if row["max_gain_pct"] is not None) /
        max(1, len([row for row in rows if row["max_gain_pct"] is not None])),
        2,
    ) if rows else 0.0

    winner = max(
        rows,
        key=lambda row: row["max_gain_pct"] if row["max_gain_pct"] is not None else float("-inf"),
        default=None,
    )
    loser = min(
        rows,
        key=lambda row: row["close_change_pct"] if row["close_change_pct"] is not None else float("inf"),
        default=None,
    )

    return _cache_set(cache_key, {
        "status": "ready",
        "trade_date": trade_date,
        "summary": {
            "count": len(rows),
            "success_count": success_count,
            "fail_count": fail_count,
            "avg_close_change_pct": avg_close,
            "avg_max_gain_pct": avg_max,
            "best": winner,
            "worst": loser,
        },
        "items": rows,
    })


async def refresh_turn_strong_run(trade_date: str | None = None) -> dict[str, Any]:
    run = get_turn_strong_run(trade_date) if trade_date else get_turn_strong_today_or_latest()
    if not run:
        return await generate_turn_strong_run(force=True)

    items = run.get("items") or []
    if items:
        quotes = await get_quotes([_symbol_for_quote(item["code"]) for item in items])
        items = _merge_live_quotes(items, quotes)

    indices, risers, fallers = await asyncio.gather(
        get_index_snapshot(),
        get_sector_movers(8, True),
        get_sector_movers(8, False),
    )
    market_snapshot = _build_market_snapshot(indices, risers, fallers)

    return _save_turn_strong_run(
        {
            "trade_date": run["trade_date"],
            "previous_trade_date": run.get("previous_trade_date", ""),
            "screening_query": run.get("screening_query", build_turn_strong_screen_query()),
            "status": run.get("status", "ready"),
            "conditions": run.get("conditions") or [],
            "market_snapshot": market_snapshot,
            "items": items,
            "overall_analysis": run.get("overall_analysis") or {},
            "last_error": run.get("last_error", ""),
        }
    )


async def ensure_turn_strong_run() -> dict[str, Any] | None:
    run = get_turn_strong_today_or_latest()
    if run:
        return run
    if not _is_weekday():
        return None
    return await generate_turn_strong_run(force=True)

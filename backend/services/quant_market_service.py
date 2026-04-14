"""Quant-ready market data service backed by iWenCai API."""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger("info-hub.quant-market")

# 问财配置
IWENCAI_BASE_URL = os.environ.get("IWENCAI_BASE_URL", "https://openapi.iwencai.com")
IWENCAI_API_KEY = ""

# K 线周期映射
KLINE_PERIOD_ALIAS = {
    "minute": "day",
    "min1": "day",
    "1m": "day",
    "15min": "day",
    "min15": "day",
    "15m": "day",
    "hour": "day",
    "min60": "day",
    "1h": "day",
    "60m": "day",
    "day": "day",
    "d1": "day",
    "week": "day",
    "month": "day",
}


def _load_iwencai_key() -> str:
    global IWENCAI_API_KEY
    if IWENCAI_API_KEY:
        return IWENCAI_API_KEY
    key = os.environ.get("IWENCAI_API_KEY", "").strip()
    if key:
        IWENCAI_API_KEY = key
        return key
    # 从 shell profile 加载
    for profile_path in [
        os.path.expanduser("~/.zshrc"),
        os.path.expanduser("~/.bash_profile"),
        os.path.expanduser("~/.bashrc"),
    ]:
        if os.path.exists(profile_path):
            for line in open(profile_path, encoding="utf-8"):
                line = line.strip()
                if "IWENCAI_API_KEY" in line and "=" in line and not line.startswith("#"):
                    if line.startswith("export "):
                        line = line[7:].strip()
                    k, _, v = line.partition("=")
                    v = v.strip().strip("'\"")
                    if "IWENCAI_API_KEY" in k:
                        IWENCAI_API_KEY = v
                        return v
    return ""


def _post_iwencai(query: str, page: int = 1, limit: int = 100) -> dict:
    """发送问财查询请求"""
    api_key = _load_iwencai_key()
    if not api_key:
        raise RuntimeError("IWENCAI_API_KEY not configured")

    url = f"{IWENCAI_BASE_URL}/v1/query2data"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "page": str(page),
        "limit": str(limit),
        "is_cache": "1",
        "expand_index": "true",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("status_code") not in (None, 0):
        raise RuntimeError(f"问财查询失败: {result.get('status_msg', '未知错误')}")
    return result


def _extract_date_columns(row: dict) -> list[str]:
    """从行数据中提取日期列名（如 '收盘价[20260414]'）"""
    dates = set()
    for key in row.keys():
        match = re.search(r"\[(\d{8})\]", key)
        if match:
            dates.add(match.group(1))
    return sorted(dates)


def _get_field(row: dict, field_name: str, date_str: str) -> float:
    """从列式数据中提取字段值"""
    key = f"{field_name}[{date_str}]"
    val = row.get(key)
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
    return 0.0


def _format_date(date_str: str) -> str:
    """20260414 -> 2026-04-14T00:00:00"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}T00:00:00"
    return date_str


async def get_quant_capabilities() -> dict:
    return {
        "provider": "iwencai",
        "service": "quant-market-data",
        "kline_period_aliases": KLINE_PERIOD_ALIAS,
        "runtime": {
            "python_version": "3.12",
            "platform": "linux",
            "timestamp": datetime.now().isoformat(),
        },
        "supported_periods": list(KLINE_PERIOD_ALIAS.keys()),
    }


async def get_kline(code: str, period: str, begin_date: int, end_date: int) -> dict:
    """获取单只股票日K线数据（通过问财）"""
    normalized_period = KLINE_PERIOD_ALIAS.get(period, "day")

    # 问财查询：获取指定日期范围的日K线
    code_clean = code.split(".")[0] if "." in code else code
    begin_str = str(begin_date)
    end_str = str(end_date)

    query = f"{code_clean} {begin_str}到{end_str} 日线 日期 开盘价 最高价 最低价 收盘价 成交量 成交额"

    try:
        result = _post_iwencai(query, limit=500)
    except Exception as exc:
        logger.error("问财K线查询失败 %s: %s", code, exc)
        return {
            "code": code,
            "period": normalized_period,
            "requested_period": period,
            "begin_date": begin_date,
            "end_date": end_date,
            "count": 0,
            "items": [],
            "error": str(exc),
        }

    rows = result.get("datas") or []
    if not rows:
        return {
            "code": code,
            "period": normalized_period,
            "requested_period": period,
            "begin_date": begin_date,
            "end_date": end_date,
            "count": 0,
            "items": [],
        }

    # 问财返回一行，列带日期后缀（如 '收盘价[20260414]'）
    row = rows[0]
    dates = _extract_date_columns(row)

    items = []
    for date_str in dates:
        if begin_str <= date_str <= end_str:
            items.append({
                "code": code,
                "timestamp": _format_date(date_str),
                "open": _get_field(row, "开盘价", date_str),
                "high": _get_field(row, "最高价", date_str),
                "low": _get_field(row, "最低价", date_str),
                "close": _get_field(row, "收盘价", date_str),
                "volume": _get_field(row, "成交量", date_str),
                "amount": _get_field(row, "成交额", date_str),
            })

    # 按日期排序
    items.sort(key=lambda x: x["timestamp"])

    return {
        "code": code,
        "period": normalized_period,
        "requested_period": period,
        "begin_date": begin_date,
        "end_date": end_date,
        "count": len(items),
        "items": items,
    }


async def get_multi_period_klines(code: str, trade_date: int | None = None) -> dict:
    """获取多周期K线数据"""
    if trade_date is None:
        trade_date = int(datetime.now().strftime("%Y%m%d"))

    trade_day_dt = datetime.strptime(str(trade_date), "%Y%m%d")
    periods = {
        "day": {
            "begin_date": int((trade_day_dt - timedelta(days=180)).strftime("%Y%m%d")),
            "end_date": trade_date,
        },
    }

    results = {}
    for key, config in periods.items():
        results[key] = await get_kline(
            code=code,
            period="day",
            begin_date=config["begin_date"],
            end_date=config["end_date"],
        )

    return {
        "code": code,
        "trade_date": trade_date,
        "series": results,
    }

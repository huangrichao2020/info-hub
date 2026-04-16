"""Quant-ready market data service backed by iWenCai and EastMoney APIs."""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger("info-hub.quant-market")

# 问财配置
IWENCAI_BASE_URL = os.environ.get("IWENCAI_BASE_URL", "https://openapi.iwencai.com")
IWENCAI_API_KEY = ""

# K 线周期映射 - 分钟级走东财接口，日线走问财接口
KLINE_PERIOD_ALIAS = {
    "minute": "min1",
    "min1": "min1",
    "1m": "min1",
    "5min": "min5",
    "min5": "min5",
    "5m": "min5",
    "15min": "min15",
    "min15": "min15",
    "15m": "min15",
    "30min": "min30",
    "min30": "min30",
    "30m": "min30",
    "hour": "min60",
    "min60": "min60",
    "1h": "min60",
    "60m": "min60",
    "day": "day",
    "d1": "day",
    "week": "week",
    "month": "month",
}

# 东方财富 K 线类型代码
EASTMONEY_KLINE_TYPE = {
    "min1": 1,    # 1分钟
    "min5": 2,    # 5分钟
    "min15": 3,   # 15分钟
    "min30": 4,   # 30分钟
    "min60": 5,   # 60分钟
    "day": 101,   # 日线
    "week": 102,  # 周线
    "month": 103, # 月线
}

# 东方财富 secid 转换
def _eastmoney_secid(code: str) -> str:
    """转换股票代码为东方财富格式: 600376.SH -> 1.600376"""
    code = code.strip().upper()
    if "." in code:
        symbol, market = code.split(".", 1)
        market = market.upper()
        if market == "SH":
            return f"1.{symbol}"
        if market in ("SZ", "BJ"):
            return f"0.{symbol}"
    # 自动判断：6/9开头=上海，0/3/2开头=深圳，4/8开头=北京
    if code.startswith(("6", "9")):
        return f"1.{code}"
    return f"0.{code}"


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


async def _fetch_eastmoney_kline(
    code: str,
    period: str,
    begin_date: int | None = None,
    end_date: int | None = None,
    limit: int = 500,
) -> list[dict]:
    """从东方财富 API 获取分钟级或日K线数据"""
    secid = _eastmoney_secid(code)
    klt = EASTMONEY_KLINE_TYPE.get(period, 101)  # 默认日线

    params = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": str(klt),
        "fqt": "1",  # 前复权
        "end": "20500101",
        "lmt": str(limit),
    }

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params)

    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("东方财富K线获取失败 %s: %s", code, exc)
        return []

    data = payload.get("data") or {}
    klines = data.get("klines") or []

    items = []
    for line in klines:
        parts = str(line).split(",")
        if len(parts) < 10:
            continue

        date_str = parts[0]
        # 分钟级数据格式：2026-04-14 09:31
        # 日线格式：2026-04-14
        if " " in date_str:
            timestamp = date_str.replace(" ", "T") + ":00"
        else:
            timestamp = date_str + "T00:00:00"

        # 过滤日期范围
        if begin_date:
            date_num = int(date_str[:4] + date_str[5:7] + date_str[8:10])
            if date_num < begin_date:
                continue
        if end_date:
            date_num = int(date_str[:4] + date_str[5:7] + date_str[8:10])
            if date_num > end_date:
                continue

        try:
            items.append({
                "code": code.upper(),
                "timestamp": timestamp,
                "open": float(parts[1]),
                "high": float(parts[2]),
                "low": float(parts[3]),
                "close": float(parts[4]),
                "volume": float(parts[5]) if parts[5] != "-" else 0.0,
                "amount": float(parts[6]) if parts[6] != "-" else 0.0,
            })
        except (ValueError, IndexError):
            continue

    return items


async def get_quant_capabilities() -> dict:
    return {
        "providers": ["iwencai", "eastmoney"],
        "service": "quant-market-data",
        "kline_period_aliases": KLINE_PERIOD_ALIAS,
        "minute_kline_provider": "eastmoney",  # 分钟级K线由东方财富提供
        "daily_kline_provider": "iwencai",      # 日线K线由问财提供
        "runtime": {
            "python_version": "3.12",
            "platform": "linux",
            "timestamp": datetime.now().isoformat(),
        },
        "supported_periods": list(KLINE_PERIOD_ALIAS.keys()),
        "multi_period_support": ["minute", "fifteen_minute", "hour", "day"],
    }


def normalize_kline_period(period: str) -> str:
    """标准化K线周期名称"""
    return KLINE_PERIOD_ALIAS.get(period, "day")


def transform_kline_response(data: dict) -> dict:
    """转换K线响应格式，统一timestamp字段"""
    items = data.get("items", [])
    transformed_items = []
    for item in items:
        # 兼容 kline_time 和 timestamp 两种字段名
        ts = item.get("timestamp") or item.get("kline_time") or ""
        transformed_items.append({
            **item,
            "timestamp": ts,
        })
    return {
        **data,
        "items": transformed_items,
    }


async def get_kline(code: str, period: str, begin_date: int, end_date: int) -> dict:
    """获取单只股票K线数据（分钟级走东财，日线走问财）"""
    normalized_period = KLINE_PERIOD_ALIAS.get(period, "day")

    # 分钟级周期走东方财富接口
    if normalized_period.startswith("min"):
        items = await _fetch_eastmoney_kline(code, normalized_period, begin_date, end_date)
        return {
            "code": code,
            "period": normalized_period,
            "requested_period": period,
            "begin_date": begin_date,
            "end_date": end_date,
            "count": len(items),
            "items": items,
            "error": None if items else "东方财富未返回数据",
        }

    # 日线/周线/月线走问财接口
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
    """获取多周期K线数据（分钟/15分钟/小时/日线）"""
    if trade_date is None:
        trade_date = int(datetime.now().strftime("%Y%m%d"))

    trade_day_dt = datetime.strptime(str(trade_date), "%Y%m%d")

    # 各周期的配置：分钟级用东财（limit 条数），日线用问财（回看天数）
    periods = {
        "minute": {
            "period_key": "min1",
            "begin_date": int((trade_day_dt - timedelta(days=5)).strftime("%Y%m%d")),  # 最近5天的分钟数据
            "end_date": trade_date,
            "limit": 5 * 240,  # 每天240分钟，5天约1200条
        },
        "fifteen_minute": {
            "period_key": "min15",
            "begin_date": int((trade_day_dt - timedelta(days=10)).strftime("%Y%m%d")),
            "end_date": trade_date,
            "limit": 100,
        },
        "hour": {
            "period_key": "min60",
            "begin_date": int((trade_day_dt - timedelta(days=30)).strftime("%Y%m%d")),
            "end_date": trade_date,
            "limit": 100,
        },
        "day": {
            "period_key": "day",
            "begin_date": int((trade_day_dt - timedelta(days=180)).strftime("%Y%m%d")),
            "end_date": trade_date,
        },
    }

    results = {}
    for key, config in periods.items():
        period_key = config["period_key"]
        if period_key.startswith("min"):
            # 分钟级走东财
            items = await _fetch_eastmoney_kline(
                code=code,
                period=period_key,
                begin_date=config["begin_date"],
                end_date=config["end_date"],
                limit=config.get("limit", 500),
            )
            results[key] = {
                "code": code,
                "period": period_key,
                "begin_date": config["begin_date"],
                "end_date": config["end_date"],
                "count": len(items),
                "items": items,
                "error": None if items else "东方财富未返回数据",
            }
        else:
            # 日线走问财
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

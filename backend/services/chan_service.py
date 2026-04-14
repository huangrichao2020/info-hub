"""日K + 缠论结构简化计算服务。"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import httpx

SEARCH_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
DEFAULT_NAME_MAP = {
    "上证指数": "000001.SH",
    "深证成指": "399001.SZ",
    "创业板指": "399006.SZ",
    "沪深300": "000300.SH",
    "科创50": "000688.SH",
    "北证50": "899050.BJ",
}


def _secid_from_code(code: str) -> str:
    code = code.strip().upper()
    if "." in code:
        symbol, market = code.split(".", 1)
        market = market.upper()
        if market == "SH":
            return f"1.{symbol}"
        if market == "SZ":
            return f"0.{symbol}"
        if market == "BJ":
            return f"0.{symbol}"
    if code.startswith(("6", "9")):
        return f"1.{code}"
    return f"0.{code}"


async def _get_json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        response.raise_for_status()
        return response.json()


def _normalize_symbol(code: str) -> str:
    code = code.strip().upper()
    if "." in code:
        return code
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith(("0", "3", "2")):
        return f"{code}.SZ"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    return code


async def search_security(query: str, limit: int = 8) -> list[dict]:
    keyword = query.strip()
    if not keyword:
        return []
    if keyword in DEFAULT_NAME_MAP:
        code = DEFAULT_NAME_MAP[keyword]
        return [{"code": code, "name": keyword}]
    if keyword[0].isdigit():
        return [{"code": _normalize_symbol(keyword), "name": keyword}]

    url = "https://searchapi.eastmoney.com/api/suggest/get?" + urllib.parse.urlencode(
        {
            "input": keyword,
            "type": "14",
            "token": SEARCH_TOKEN,
            "count": str(limit),
        }
    )
    try:
        payload = await _get_json(url)
    except Exception:
        return []

    results = []
    for item in payload.get("QuotationCodeTable", {}).get("Data", []) or []:
        code = item.get("Code") or item.get("QuotationCode")
        name = item.get("Name") or item.get("ShortName")
        market = item.get("SecurityTypeName") or item.get("MktNum")
        if not code or not name:
            continue
        results.append(
            {
                "code": _normalize_symbol(str(code)),
                "name": str(name),
                "market": str(market or ""),
            }
        )
    dedup = {}
    for item in results:
        dedup[item["code"]] = item
    return list(dedup.values())[:limit]


async def fetch_daily_bars(code: str, limit: int = 220) -> list[dict]:
    # 优先尝试问财（不消耗 MX 配额）
    bars = await _fetch_iwencai_bars(code, limit)
    if bars:
        return bars

    # 回退到东方财富
    bars = await _fetch_eastmoney_bars(code, limit)
    if bars:
        return bars

    # 最后回退到 MX API
    bars = await _fetch_mx_bars(code, limit)
    if bars:
        return bars

    return []


async def _fetch_iwencai_bars(code: str, limit: int) -> list[dict]:
    """从问财 API 获取日K线数据（逐条查询，不消耗 MX 配额）"""
    # 加载问财环境变量
    if not os.environ.get("IWENCAI_API_KEY"):
        for profile_path in [Path.home() / ".zshrc", Path.home() / ".bash_profile"]:
            if profile_path.exists():
                for line in profile_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("export ") and "IWENCAI" in line:
                        line = line[len("export "):].strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        if key.startswith("IWENCAI_") and key not in os.environ:
                            os.environ[key] = value

    api_key = os.environ.get("IWENCAI_API_KEY")
    if not api_key:
        return []

    # 解析股票代码
    code_clean = code.split(".")[0] if "." in code else code
    base_url = os.environ.get("IWENCAI_BASE_URL", "https://openapi.iwencai.com").rstrip("/")
    url = f"{base_url}/v1/query2data"

    # 判断是指数还是股票（指数代码通常以.SH/.SZ结尾，且000/399开头）
    is_index = code_clean.startswith(("000", "399")) or "指数" in code

    # 构建查询：指数和股票用不同关键词
    if is_index:
        # 指数查询：需要带指数名称，避免返回股票数据
        index_name_map = {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
            "000300": "沪深300",
            "000688": "科创50",
            "899050": "北证50",
        }
        index_name = index_name_map.get(code_clean, code_clean)
        query = f"{index_name} 最近{min(limit, 200)}个交易日 日线 日期 开盘价 最高价 最低价 收盘价 成交量"
    else:
        query = f"{code_clean} 最近{min(limit, 200)}个交易日 日线 日期 开盘价 最高价 最低价 收盘价 成交量"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        payload = {
            "query": query,
            "page": "1",
            "limit": str(min(limit, 200)),
            "is_cache": "1",
            "expand_index": "true",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

        # 解析问财返回格式（列式：字段名带日期后缀）
        rows = result.get("datas") or []
        if not rows:
            return []

        row = rows[0]  # 问财返回一行，每列是一个日期的数据

        # 提取所有日期（从字段名中提取）
        dates = set()
        for key in row.keys():
            if "[" in key and "]" in key:
                date_part = key.split("[")[1].split("]")[0]
                if len(date_part) == 8 and date_part.isdigit():
                    dates.add(date_part)

        # 按日期排序（从旧到新）
        sorted_dates = sorted(dates)

        # 辅助函数：从行中提取指定字段的指定日期值
        def get_field(field_name: str, date_str: str) -> float:
            key = f"{field_name}[{date_str}]"
            val = row.get(key)
            return float(val) if val is not None else 0.0

        bars: list[dict] = []
        for idx, date_str in enumerate(sorted_dates):
            # 格式化日期 20260413 -> 2026-04-13
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            bars.append(
                {
                    "index": idx,
                    "date": formatted_date,
                    "open": get_field("开盘价", date_str),
                    "close": get_field("收盘价", date_str),
                    "high": get_field("最高价", date_str),
                    "low": get_field("最低价", date_str),
                    "volume": get_field("成交量", date_str),
                }
            )
        return bars
    except Exception:
        return []


async def _fetch_eastmoney_bars(code: str, limit: int) -> list[dict]:
    """从东方财富获取日K线数据"""
    secid = _secid_from_code(code)
    params = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "end": "20500101",
        "lmt": str(limit),
    }
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params)
    try:
        payload = await _get_json(url)
        klines = (payload.get("data") or {}).get("klines") or []
        bars: list[dict] = []
        for idx, line in enumerate(klines):
            parts = str(line).split(",")
            if len(parts) < 6:
                continue
            bars.append(
                {
                    "index": idx,
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": float(parts[5]),
                }
            )
        return bars
    except Exception:
        return []


async def _fetch_mx_bars(code: str, limit: int) -> list[dict]:
    """从 MX API 获取日K线数据（备用数据源）"""
    # 确保环境变量已加载（从 uwillberich 配置）
    if not os.environ.get("EM_API_KEY"):
        env_path = Path.home() / ".uwillberich" / "runtime.env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value

    code_clean = code.split(".")[0] if "." in code else code

    # 使用 MX API 的 data_query 接口获取 K 线数据
    api_key = os.environ.get("MX_APIKEY") or os.environ.get("EM_API_KEY")
    if not api_key:
        return []

    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
    headers = {"Content-Type": "application/json", "apikey": api_key}
    query = f"获取{code_clean}最近{min(limit, 100)}个交易日的日K线数据，包括日期、开盘价、最高价、最低价、收盘价、成交量"

    try:
        payload = {"toolQuery": query}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

        # 解析 MX API 返回的列式数据结构
        data = result.get("data", {})
        inner_data = data.get("data", {})
        search_result = inner_data.get("searchDataResultDTO", {})
        tables = search_result.get("dataTableDTOList") or []
        if not tables:
            return []

        table = tables[0]
        raw_table = table.get("rawTable") or table.get("table") or {}
        name_map = table.get("nameMap") or {}

        # 提取日期列（headName）
        dates = raw_table.get("headName", [])

        # 构建字段名到列数据的映射
        field_data = {}
        for col_key, col_name in name_map.items():
            if col_key in raw_table:
                field_data[col_name] = raw_table[col_key]

        bars: list[dict] = []
        for idx in range(len(dates)):
            date_str = dates[idx] if idx < len(dates) else ""
            bar = {
                "index": idx,
                "date": str(date_str),
                "open": float(field_data.get("开盘价", [0] * len(dates))[idx] if idx < len(field_data.get("开盘价", [])) else 0),
                "close": float(field_data.get("收盘价", [0] * len(dates))[idx] if idx < len(field_data.get("收盘价", [])) else 0),
                "high": float(field_data.get("最高价", [0] * len(dates))[idx] if idx < len(field_data.get("最高价", [])) else 0),
                "low": float(field_data.get("最低价", [0] * len(dates))[idx] if idx < len(field_data.get("最低价", [])) else 0),
                "volume": float(field_data.get("成交量", [0] * len(dates))[idx] if idx < len(field_data.get("成交量", [])) else 0),
            }
            bars.append(bar)

        return bars
    except Exception:
        return []


@dataclass
class Pivot:
    index: int
    date: str
    kind: str  # high / low
    price: float


def detect_pivots(bars: list[dict], window: int = 2) -> list[Pivot]:
    pivots: list[Pivot] = []
    for i in range(window, len(bars) - window):
        bar = bars[i]
        left = bars[i - window:i]
        right = bars[i + 1:i + 1 + window]
        if all(bar["high"] >= other["high"] for other in left + right):
            pivots.append(Pivot(i, bar["date"], "high", bar["high"]))
        elif all(bar["low"] <= other["low"] for other in left + right):
            pivots.append(Pivot(i, bar["date"], "low", bar["low"]))

    merged: list[Pivot] = []
    for pivot in pivots:
        if not merged:
            merged.append(pivot)
            continue
        last = merged[-1]
        if last.kind == pivot.kind:
            if pivot.kind == "high" and pivot.price >= last.price:
                merged[-1] = pivot
            elif pivot.kind == "low" and pivot.price <= last.price:
                merged[-1] = pivot
            continue
        if abs(pivot.index - last.index) < 2:
            continue
        merged.append(pivot)
    return merged


def build_strokes(pivots: list[Pivot]) -> list[dict]:
    strokes = []
    for i in range(1, len(pivots)):
        start = pivots[i - 1]
        end = pivots[i]
        if start.kind == end.kind:
            continue
        direction = "up" if start.kind == "low" and end.kind == "high" else "down"
        strokes.append(
            {
                "start_index": start.index,
                "end_index": end.index,
                "start_date": start.date,
                "end_date": end.date,
                "start_price": start.price,
                "end_price": end.price,
                "direction": direction,
            }
        )
    return strokes


def build_segments(strokes: list[dict]) -> list[dict]:
    segments = []
    for i in range(2, len(strokes), 2):
        segment_strokes = strokes[i - 2:i + 1]
        start = segment_strokes[0]
        end = segment_strokes[-1]
        direction = "up" if end["end_price"] >= start["start_price"] else "down"
        segments.append(
            {
                "start_index": start["start_index"],
                "end_index": end["end_index"],
                "start_price": start["start_price"],
                "end_price": end["end_price"],
                "direction": direction,
            }
        )
    return segments


def build_centers(strokes: list[dict]) -> list[dict]:
    centers = []
    for i in range(2, len(strokes)):
        window = strokes[i - 2:i + 1]
        highs = [max(stroke["start_price"], stroke["end_price"]) for stroke in window]
        lows = [min(stroke["start_price"], stroke["end_price"]) for stroke in window]
        upper = min(highs)
        lower = max(lows)
        if upper > lower:
            centers.append(
                {
                    "start_index": window[0]["start_index"],
                    "end_index": window[-1]["end_index"],
                    "upper": round(upper, 2),
                    "lower": round(lower, 2),
                    "mid": round((upper + lower) / 2, 2),
                }
            )
    return centers


def build_trade_points(strokes: list[dict], centers: list[dict]) -> list[dict]:
    points = []
    if len(strokes) >= 3:
        first = strokes[0]
        third = strokes[2]
        if first["direction"] == "down" and third["direction"] == "down" and third["end_price"] > first["end_price"]:
            points.append({"type": "一买", "index": third["end_index"], "price": third["end_price"]})
        if first["direction"] == "up" and third["direction"] == "up" and third["end_price"] < first["end_price"]:
            points.append({"type": "一卖", "index": third["end_index"], "price": third["end_price"]})

    for center in centers:
        related = [stroke for stroke in strokes if center["start_index"] <= stroke["end_index"] <= center["end_index"] + 12]
        if len(related) < 2:
            continue
        last = related[-1]
        prev = related[-2]
        if last["direction"] == "down" and last["end_price"] >= center["lower"]:
            points.append({"type": "二买", "index": last["end_index"], "price": last["end_price"]})
        if last["direction"] == "up" and last["end_price"] <= center["upper"]:
            points.append({"type": "二卖", "index": last["end_index"], "price": last["end_price"]})
        if prev["direction"] == "down" and last["direction"] == "down" and last["end_price"] > prev["end_price"]:
            points.append({"type": "类二买", "index": last["end_index"], "price": last["end_price"]})

    dedup = {}
    for point in points:
        dedup[(point["type"], point["index"])] = point
    return list(dedup.values())


async def build_chan_chart(code: str, limit: int = 220) -> dict:
    bars = await fetch_daily_bars(code, limit)
    pivots = detect_pivots(bars)
    strokes = build_strokes(pivots)
    segments = build_segments(strokes)
    centers = build_centers(strokes)
    points = build_trade_points(strokes, centers)
    return {
        "code": code.upper(),
        "bars": bars,
        "pivots": [pivot.__dict__ for pivot in pivots],
        "strokes": strokes,
        "segments": segments,
        "centers": centers,
        "trade_points": points,
    }

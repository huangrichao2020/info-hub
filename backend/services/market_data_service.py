"""国内 A 股市场数据服务。

交叉验证报告需要的是可解释的市场信号，不应把结果押在单一接口上。
这里沿用 a_stock_data 的数据源分层：同花顺取北向和热点，东方财富取涨跌停池，
腾讯行情做指数趋势兜底；所有外部请求默认直连，避免桌面代理异常污染定时任务。
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import requests

logger = logging.getLogger("info-hub.market_data")

try:
    sys.path.insert(0, os.path.expanduser("~/hermes-new/hermes-agent/tools"))
    from eastmoney_key_rotator import get_available_key, record_usage  # type: ignore
    _HAS_ROTATOR = True
except ImportError:
    _HAS_ROTATOR = False
    logger.warning("Eastmoney key rotator not found, falling back to static headers")


def _direct_get(url: str, **kwargs) -> requests.Response:
    """Fetch domestic market data without inheriting broken proxy env."""
    kwargs.setdefault("timeout", 10)
    session = requests.Session()
    session.trust_env = False
    try:
        return session.get(url, **kwargs)
    finally:
        session.close()


def _json_from_response(resp: requests.Response) -> dict[str, Any]:
    text = resp.text.strip()
    if text.startswith("{") or text.startswith("["):
        return resp.json()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return {}


def _get_em_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    if _HAS_ROTATOR:
        key, key_headers = get_available_key()
        if key:
            headers.update(key_headers)
    return headers


def _record_em_success() -> None:
    if not _HAS_ROTATOR:
        return
    try:
        key, _ = get_available_key()
        if key:
            record_usage(key)
    except Exception as exc:
        logger.debug("record eastmoney key usage failed: %s", exc)


def _first_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else 0.0


def fetch_north_flow() -> float:
    """获取北向资金净流入，优先同花顺，失败后用东方财富兜底。"""
    ths_url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
    ths_headers = {
        "User-Agent": "Mozilla/5.0 Chrome/117.0.0.0",
        "Host": "data.hexin.cn",
        "Referer": "https://data.hexin.cn/",
    }
    try:
        resp = _direct_get(ths_url, headers=ths_headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        hgt = data.get("hgt") or []
        sgt = data.get("sgt") or []
        latest_hgt = _first_number(hgt[-1]) if hgt else 0.0
        latest_sgt = _first_number(sgt[-1]) if sgt else 0.0
        latest = round(latest_hgt + latest_sgt, 2)
        if latest:
            return latest
    except Exception as exc:
        logger.warning("同花顺北向资金失败：%s", exc)

    try:
        url = "https://push2.eastmoney.com/api/qt/kamt.mini.kline/get"
        params = {
            "fields1": "f1,f2,f3,f4",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": "101",
            "lmt": "1",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "cb": "jQuery",
        }
        resp = _direct_get(url, params=params, headers=_get_em_headers(), timeout=10)
        if resp.status_code == 200:
            _record_em_success()
            data = _json_from_response(resp)
            s2n = (data.get("data") or {}).get("s2n")
            return _first_number(s2n)
    except Exception as exc:
        logger.warning("东方财富北向资金失败：%s", exc)
    return 0.0


def _fetch_em_pool(pool_type: str) -> list[dict[str, Any]]:
    endpoint = {
        "zt": "https://push2ex.eastmoney.com/getTopicZTPool",
        "dt": "https://push2ex.eastmoney.com/getTopicDTPool",
    }[pool_type]
    resp = _direct_get(
        endpoint,
        params={"ut": "7eea3edcaed734bea9cb0088a5b3e8b2", "dtp": "1", "sty": "tdcp", "fldt": "1"},
        headers=_get_em_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        return []
    _record_em_success()
    data = _json_from_response(resp)
    pool = (data.get("data") or {}).get("pool") or []
    return pool if isinstance(pool, list) else []


def fetch_limit_stats() -> Dict[str, int]:
    """获取涨跌停家数。"""
    try:
        return {"limit_up": len(_fetch_em_pool("zt")), "limit_down": len(_fetch_em_pool("dt"))}
    except Exception as exc:
        logger.warning("获取涨跌停统计失败：%s", exc)
        return {"limit_up": 0, "limit_down": 0}


def fetch_lianban_stats(pool: Optional[list[dict[str, Any]]] = None) -> int:
    """获取最高连板高度。"""
    try:
        pool = pool if pool is not None else _fetch_em_pool("zt")
        max_ban = 0
        for stock in pool:
            for key in ("lbc", "zttj", "fbt", "连板数", "连续涨停天数"):
                value = stock.get(key)
                if isinstance(value, dict):
                    value = value.get("days") or value.get("ct")
                max_ban = max(max_ban, int(_first_number(value)))
        return max_ban
    except Exception as exc:
        logger.warning("获取连板高度失败：%s", exc)
        return 0


def fetch_yesterday_premium(pool: Optional[list[dict[str, Any]]] = None) -> float:
    """用涨停池当前涨幅粗略估算昨日涨停溢价。"""
    try:
        pool = pool if pool is not None else _fetch_em_pool("zt")
        premiums = []
        for stock in pool:
            for key in ("zdp", "pct", "涨跌幅"):
                if key in stock:
                    premiums.append(_first_number(stock.get(key)))
                    break
        return round(sum(premiums) / len(premiums), 2) if premiums else 0.0
    except Exception as exc:
        logger.warning("获取昨日涨停溢价失败：%s", exc)
        return 0.0


def fetch_hot_theme() -> dict[str, Any]:
    """参考 a_stock_data 的同花顺强势股接口提取主线题材。"""
    try:
        date = datetime.now().strftime("%Y-%m-%d")
        url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date}/orderby/date/orderway/desc/charset/GBK/"
        resp = _direct_get(url, headers={"User-Agent": "Mozilla/5.0 Chrome/117.0.0.0"}, timeout=10)
        data = resp.json()
        rows = data.get("data") or []
        reasons: list[str] = []
        for row in rows:
            reason = str(row.get("reason") or row.get("题材归因") or "")
            for part in re.split(r"[,，;；、/ ]+", reason):
                part = part.strip()
                if 2 <= len(part) <= 12:
                    reasons.append(part)
        counter = Counter(reasons)
        main_theme, count = counter.most_common(1)[0] if counter else ("", 0)
        return {"main_theme": main_theme, "theme_limit_up": int(count), "theme_tiers": min(5, max(0, len(counter)))}
    except Exception as exc:
        logger.warning("同花顺热点题材失败：%s", exc)
        return {"main_theme": "", "theme_limit_up": 0, "theme_tiers": 0}


def fetch_index_trend() -> dict[str, Any]:
    """用腾讯指数行情判断大盘方向。"""
    try:
        resp = _direct_get(
            "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.encoding = "gbk"
        changes = []
        for line in resp.text.split(";"):
            if '="' not in line:
                continue
            vals = line.split('"')[1].split("~")
            if len(vals) > 32:
                changes.append(_first_number(vals[32]))
        avg_change = sum(changes) / len(changes) if changes else 0.0
        if avg_change > 0.35:
            trend = "up"
        elif avg_change < -0.35:
            trend = "down"
        else:
            trend = "sideways"
        return {"index_trend": trend, "ma_alignment": avg_change > 0, "index_avg_change": round(avg_change, 2)}
    except Exception as exc:
        logger.warning("腾讯指数趋势失败：%s", exc)
        return {"index_trend": "sideways", "ma_alignment": False, "index_avg_change": 0.0}


def fetch_market_snapshot() -> Dict[str, Any]:
    """获取完整市场快照，用于交叉验证。"""
    zt_pool: list[dict[str, Any]] = []
    dt_pool: list[dict[str, Any]] = []
    try:
        zt_pool = _fetch_em_pool("zt")
        dt_pool = _fetch_em_pool("dt")
    except Exception as exc:
        logger.warning("东方财富涨跌停池失败：%s", exc)

    north_flow = fetch_north_flow()
    limit_up = len(zt_pool)
    limit_down = len(dt_pool)
    if not (limit_up or limit_down):
        stats = fetch_limit_stats()
        limit_up = stats["limit_up"]
        limit_down = stats["limit_down"]

    total = limit_up + limit_down
    limit_ratio = limit_up / max(total, 1)
    if limit_ratio > 0.8 and north_flow > 50:
        sentiment = "greed"
    elif limit_ratio < 0.2 and north_flow < -50:
        sentiment = "fear"
    else:
        sentiment = "neutral"

    snapshot: Dict[str, Any] = {
        "volume_change": 0.0,
        "north_flow": north_flow,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "sentiment": sentiment,
        "consecutive_ban": fetch_lianban_stats(zt_pool),
        "yesterday_premium": fetch_yesterday_premium(zt_pool),
        "divergence": False,
        "dragon_head_status": "strong" if limit_up >= limit_down else "weak",
        "policy": "neutral",
        "us_market": "flat",
        "exchange_rate_change": 0.0,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "source_quality": "live-domestic-mixed" if (limit_up or limit_down or north_flow) else "fallback",
    }
    snapshot.update(fetch_hot_theme())
    snapshot.update(fetch_index_trend())
    return snapshot

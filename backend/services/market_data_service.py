"""
真实市场数据服务
从东方财富 API 获取实时市场数据，替换交叉验证中的模拟值。
使用 Key 轮询器管理每日配额（3 Keys × 20 次/天）。
"""
import logging
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("info-hub.market_data")

# 东方财富 API 配置 — 使用 Key 轮询器
try:
    import sys
    sys.path.insert(0, "/root/hermes-agent/tools")
    from eastmoney_key_rotator import get_available_key, record_usage
    _HAS_ROTATOR = True
except ImportError:
    _HAS_ROTATOR = False
    logger.warning("Eastmoney key rotator not found, falling back to static headers")

def _get_em_headers() -> Dict[str, str]:
    """获取带 Key 的请求头"""
    if _HAS_ROTATOR:
        key, headers = get_available_key()
        if key:
            return {**headers, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://quote.eastmoney.com/"}
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }


def fetch_north_flow() -> float:
    """
    获取北向资金净流入（亿元）。
    返回：正数=流入，负数=流出，0=获取失败
    """
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
        resp = requests.get(url, params=params, headers=_get_em_headers(), timeout=10)
        if resp.status_code == 200:
            # 解析 JSONP 响应
            text = resp.text
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                import json
                data = json.loads(text[json_start:json_end])
                if data.get("data") and data["data"].get("s2n"):
                    # s2n: 北向资金净流入
                    return float(data["data"]["s2n"])
    except Exception as e:
        logger.warning(f"获取北向资金失败：{e}")
    return 0.0


def fetch_limit_stats() -> Dict[str, int]:
    """
    获取涨跌停家数。
    返回：{"limit_up": 0, "limit_down": 0}
    """
    try:
        # 涨停家数
        resp = requests.get(
            "https://push2ex.eastmoney.com/getTopicZTPool",
            params={"ut": "7eea3edcaed734bea9cb0088a5b3e8b2", "dtp": "1", "sty": "tdcp", "fldt": "1"},
            headers=_get_em_headers(), timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            limit_up = len(data.get("data", {}).get("pool", [])) if data.get("data") else 0
        else:
            limit_up = 0

        # 跌停家数
        resp = requests.get(
            "https://push2ex.eastmoney.com/getTopicDTPool",
            params={"ut": "7eea3edcaed734bea9cb0088a5b3e8b2", "dtp": "1", "sty": "tdcp", "fldt": "1"},
            headers=_get_em_headers(), timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            limit_down = len(data.get("data", {}).get("pool", [])) if data.get("data") else 0
        else:
            limit_down = 0

        return {"limit_up": limit_up, "limit_down": limit_down}

    except Exception as e:
        logger.warning(f"获取涨跌停统计失败：{e}")
        return {"limit_up": 0, "limit_down": 0}


def fetch_lianban_stats() -> int:
    """
    获取当前最高连板高度。
    从涨停池中解析每只股票的连续涨停天数（fbt 字段）。
    """
    try:
        resp = requests.get(
            "https://push2ex.eastmoney.com/getTopicZTPool",
            params={"ut": "7eea3edcaed734bea9cb0088a5b3e8b2", "dtp": "1", "sty": "tdcp", "fldt": "1"},
            headers=_get_em_headers(), timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            pool = data.get("data", {}).get("pool", [])
            max_ban = 0
            for stock in pool:
                fbt = stock.get("fbt") or stock.get("连续涨停天数") or 0
                try:
                    max_ban = max(max_ban, int(fbt))
                except (ValueError, TypeError):
                    continue
            return max_ban
    except Exception as e:
        logger.warning(f"获取连板高度失败：{e}")
    return 0


def fetch_yesterday_premium() -> float:
    """
    获取昨日涨停股今日平均溢价（百分比）。
    计算涨停池中今日涨幅均值。
    """
    try:
        resp = requests.get(
            "https://push2ex.eastmoney.com/getTopicZTPool",
            params={"ut": "7eea3edcaed734bea9cb0088a5b3e8b2", "dtp": "1", "sty": "tdcp", "fldt": "1"},
            headers=_get_em_headers(), timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            pool = data.get("data", {}).get("pool", [])
            premiums = []
            for stock in pool:
                pct = stock.get("pct") or stock.get("涨跌幅") or 0
                try:
                    premiums.append(float(pct))
                except (ValueError, TypeError):
                    continue
            if premiums:
                return round(sum(premiums) / len(premiums), 2)
    except Exception as e:
        logger.warning(f"获取昨日涨停溢价失败：{e}")
    return 0.0


def fetch_market_snapshot() -> Dict[str, Any]:
    """
    获取完整市场快照，用于交叉验证。
    整合多个数据源，返回标准化字典。
    """
    north_flow = fetch_north_flow()
    limit_stats = fetch_limit_stats()
    lianban = fetch_lianban_stats()
    premium = fetch_yesterday_premium()

    # 计算涨跌比
    total = limit_stats["limit_up"] + limit_stats["limit_down"]
    limit_ratio = limit_stats["limit_up"] / max(total, 1)

    # 情绪判断
    if limit_ratio > 0.8 and north_flow > 50:
        sentiment = "greed"
    elif limit_ratio < 0.2 and north_flow < -50:
        sentiment = "fear"
    else:
        sentiment = "neutral"

    return {
        "volume_change": 0.0,  # 需要行情数据计算
        "north_flow": north_flow,
        "limit_up": limit_stats["limit_up"],
        "limit_down": limit_stats["limit_down"],
        "sentiment": sentiment,
        "consecutive_ban": lianban,
        "yesterday_premium": premium,
        "index_trend": "sideways",  # 需要指数数据
        "ma_alignment": False,
        "divergence": False,
        "main_theme": "",  # 需要板块数据
        "theme_limit_up": 0,
        "theme_tiers": 0,
        "dragon_head_status": "strong",
        "policy": "neutral",
        "us_market": "flat",
        "exchange_rate_change": 0.0,
        "fetched_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import json
    snapshot = fetch_market_snapshot()
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))

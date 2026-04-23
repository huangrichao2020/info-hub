"""涨停分析服务 - 包装 uwillberich zt_review"""
import asyncio
import logging
import re

logger = logging.getLogger("info-hub.zt")


def _extract_rows(raw: dict | list | None) -> list[dict]:
    """从 MX API 原始响应中提取 rows 列表"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("rows", [])
    return []


def _find_key(row: dict, prefix: str) -> str | None:
    """在 row 中找匹配前缀的 key（MX API 的 key 带日期后缀）"""
    for k in row:
        if k.startswith(prefix):
            return k
    return None


def _normalize_zt(row: dict) -> dict:
    """把 MX API 原始行转换为前端需要的格式"""
    code = row.get("SECURITY_CODE", "")
    name = row.get("SECURITY_SHORT_NAME", "") or row.get("MARKET_SHORT_NAME", "")

    # CHG 涨幅
    chg = row.get("CHG", 0)
    try:
        change_pct = float(chg) if chg else 0
    except (ValueError, TypeError):
        change_pct = 0

    # 涨停原因 / 概念
    reason = row.get("STYLE_CONCEPT", "") or ""
    if len(reason) > 80:
        reason = reason[:80] + "..."

    # 连板数
    lianban_key = _find_key(row, "010000_LIAN_BAN")
    lianban_count = 0
    if lianban_key:
        try:
            lianban_count = int(float(row[lianban_key]))
        except (ValueError, TypeError):
            pass

    # 封单额
    limit_up_key = _find_key(row, "010000_LIMIT_UP_A")
    seal_amount = ""
    if limit_up_key:
        seal_amount = str(row.get(limit_up_key, ""))

    # 成交额
    volume_key = _find_key(row, "010000_TRADING_VOLUMES")
    volume = ""
    if volume_key:
        volume = str(row.get(volume_key, ""))

    # 流通市值
    mv_key = _find_key(row, "010000_CIRCULATION_MARKET_VALUE")
    market_value = ""
    if mv_key:
        market_value = str(row.get(mv_key, ""))

    # 换手率 -> 人气分 (换手率越高人气越高, 归一化到 0-100)
    turnover_key = _find_key(row, "010000_TURNOVER_RATE")
    popularity_score = None
    if turnover_key:
        try:
            turnover = float(row[turnover_key])
            popularity_score = min(round(turnover * 5), 100)  # 20%换手率 = 100分
        except (ValueError, TypeError):
            pass

    return {
        "code": code,
        "name": name,
        "change_pct": change_pct,
        "reason": reason,
        "lianban_count": lianban_count,
        "seal_amount": seal_amount,
        "volume": volume,
        "market_value": market_value,
        "popularity_score": popularity_score,
    }


async def get_zt_today() -> list[dict]:
    """获取今日涨停股"""
    try:
        import zt_review
        result = await asyncio.to_thread(zt_review.query_zt_today)
        rows = _extract_rows(result)
        return [_normalize_zt(r) for r in rows]
    except Exception as e:
        logger.error(f"获取涨停数据失败: {e}")
        return []


async def get_lianban() -> list[dict]:
    """获取连板股"""
    try:
        import zt_review
        result = await asyncio.to_thread(zt_review.query_lianban)
        rows = _extract_rows(result)
        items = [_normalize_zt(r) for r in rows]
        # 按连板数降序
        items.sort(key=lambda x: x["lianban_count"], reverse=True)
        return items
    except Exception as e:
        logger.error(f"获取连板数据失败: {e}")
        return []


async def get_recent_zt(days: int = 7) -> list[dict]:
    """获取近N天涨停数据"""
    try:
        import zt_review
        result = await asyncio.to_thread(zt_review.query_recent_zt, days)
        rows = _extract_rows(result)
        return [_normalize_zt(r) for r in rows]
    except Exception as e:
        logger.error(f"获取历史涨停失败: {e}")
        return []


async def get_zt_report(days: int = 7) -> str:
    """获取涨停复盘报告（Markdown）"""
    try:
        import zt_review
        result = await asyncio.to_thread(zt_review.render_report, days)
        return result or ""
    except Exception as e:
        logger.error(f"生成涨停报告失败: {e}")
        return ""

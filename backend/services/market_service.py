"""市场数据服务 - 包装 uwillberich market_data + capital_flow"""
import asyncio
import logging

logger = logging.getLogger("info-hub.market")


async def get_sector_movers(limit: int = 10, rising: bool = True) -> list[dict]:
    """获取板块涨跌排行"""
    try:
        import market_data
        result = await asyncio.to_thread(market_data.fetch_sector_movers, limit, rising)
        return result or []
    except Exception as e:
        logger.error(f"获取板块数据失败: {e}")
        return []


async def get_index_snapshot() -> list[dict]:
    """获取大盘指数快照"""
    try:
        import market_data
        result = await asyncio.to_thread(market_data.fetch_index_snapshot)
        return result or []
    except Exception as e:
        logger.error(f"获取指数数据失败: {e}")
        return []


async def get_capital_flow() -> dict:
    """获取资金流向"""
    try:
        import capital_flow
        result = await asyncio.to_thread(capital_flow.fetch_market_flow_snapshot)
        return result or {}
    except Exception as e:
        logger.error(f"获取资金流向失败: {e}")
        return {}


async def get_quotes(symbols: list[str]) -> list[dict]:
    """获取股票行情"""
    try:
        import market_data
        result = await asyncio.to_thread(market_data.fetch_tencent_quotes, symbols)
        return result or []
    except Exception as e:
        logger.error(f"获取行情失败: {e}")
        return []

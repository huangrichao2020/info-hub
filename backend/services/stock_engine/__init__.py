"""
A-Share Local Stock Data Engine (Baostock + Parquet)
Migrated from TradingAgents for Info-Hub integration.
"""
import os
import logging
from pathlib import Path

from .local_cache import LocalStockCache
from .dump_service import run_incremental_dump

logger = logging.getLogger("info-hub.stock_engine")

# 默认数据路径
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "historical"

# 初始化引擎实例
_engine = None

def get_engine() -> LocalStockCache:
    global _engine
    if _engine is None:
        _engine = LocalStockCache(str(DATA_DIR))
    return _engine

def init_stock_engine():
    """Initialize the stock engine."""
    logger.info(f"Initializing stock engine, data dir: {DATA_DIR}")
    engine = get_engine()
    return engine

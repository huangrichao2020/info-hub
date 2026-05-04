"""
Stock Analysis & Scanning Router for Info-Hub.
使用 DuckDB 全市场扫描加速（比 pandas 逐文件快 19x）。
"""
import logging
import os
import time
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd

from services.stock_engine import get_engine
from services.duckdb_engine import get_engine as get_duckdb

router = APIRouter(prefix="", tags=["A股分析"])
logger = logging.getLogger("info-hub.stock")

engine = get_engine()

try:
    duckdb_engine = get_duckdb()
    DUCKDB_AVAILABLE = True
except Exception as e:
    logger.warning(f"DuckDB 引擎不可用: {e}")
    duckdb_engine = None
    DUCKDB_AVAILABLE = False


class StockAnalysisRequest(BaseModel):
    symbol: str
    date: Optional[str] = None

class StockAnalysisResponse(BaseModel):
    symbol: str
    ma25_trend: str
    ma25_value: float
    macd: dict
    volume_ma5: float
    volume_ma60: float

class StockScanResponse(BaseModel):
    total: int
    stocks: List[dict]

class DuckDBQueryRequest(BaseModel):
    sql: str
    limit: Optional[int] = 1000

@router.get("/analysis/{symbol}")
async def get_stock_analysis(symbol: str, date: Optional[str] = None, indicator: Optional[str] = None):
    """Get analysis for a single stock."""
    if indicator:
        return engine.get_indicators(symbol, indicator, curr_date=date)
    
    res = {
        "ma25": engine.get_indicators(symbol, "ma_25", curr_date=date),
        "macd": engine.get_indicators(symbol, "macd", curr_date=date),
        "vol5": engine.get_indicators(symbol, "vol_5", curr_date=date),
        "vol60": engine.get_indicators(symbol, "vol_60", curr_date=date),
        "can": engine.get_indicators(symbol, "volume_ratio", curr_date=date)
    }
    return res

@router.get("/scan/ma25-up")
async def scan_ma25_up():
    """全市场扫描 MA25 向上的股票（DuckDB 加速）。"""
    if DUCKDB_AVAILABLE:
        t0 = time.time()
        df = duckdb_engine.scan_ma25_up()
        elapsed = time.time() - t0
        logger.info(f"DuckDB MA25 scan: {len(df)} stocks in {elapsed:.2f}s")
        return {
            "total": len(df),
            "stocks": df.head(50).to_dict("records"),
            "engine": "duckdb",
            "elapsed_ms": round(elapsed * 1000, 1)
        }
    else:
        # Fallback: 旧 pandas 方式
        return _scan_ma25_up_pandas()


def _scan_ma25_up_pandas():
    """旧版 pandas 扫描（DuckDB 不可用时回退）。"""
    data_dir = engine.data_dir
    if not os.path.exists(data_dir):
        return {"stocks": [], "msg": "No data yet", "engine": "pandas"}
    
    results = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    
    for f in files:
        try:
            path = os.path.join(data_dir, f)
            df = pd.read_parquet(path, columns=['date', 'close'])
            if len(df) < 26:
                continue
            df = df.tail(26)
            ma25_curr = df['close'].rolling(25).mean().iloc[-1]
            ma25_prev = df['close'].rolling(25).mean().iloc[-2]
            if pd.notna(ma25_curr) and pd.notna(ma25_prev) and ma25_curr > ma25_prev:
                sym = f.replace('sh_', 'sh.').replace('sz_', 'sz.').replace('.parquet', '')
                results.append({"symbol": sym, "ma25": round(ma25_curr, 2)})
        except Exception:
            continue
            
    return {"total": len(results), "stocks": results[:50], "engine": "pandas"}

@router.get("/scan/volume-up")
async def scan_volume_up(min_ratio: float = 1.5):
    """全市场扫描放量上涨（DuckDB 加速）。"""
    if DUCKDB_AVAILABLE:
        t0 = time.time()
        df = duckdb_engine.scan_volume_up(min_ratio=min_ratio)
        elapsed = time.time() - t0
        logger.info(f"DuckDB volume-up scan: {len(df)} stocks in {elapsed:.2f}s")
        return {
            "total": len(df),
            "stocks": df.head(50).to_dict("records"),
            "engine": "duckdb",
            "elapsed_ms": round(elapsed * 1000, 1)
        }
    else:
        return _scan_volume_up_pandas()


def _scan_volume_up_pandas():
    """旧版 pandas 扫描（DuckDB 不可用时回退）。"""
    data_dir = engine.data_dir
    if not os.path.exists(data_dir):
        return {"stocks": [], "msg": "No data yet", "engine": "pandas"}
    
    results = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    
    for f in files:
        try:
            path = os.path.join(data_dir, f)
            df = pd.read_parquet(path, columns=['date', 'close', 'volume'])
            if len(df) < 26:
                continue
            df = df.tail(30)
            vol_ma25 = df['volume'].rolling(25).mean().iloc[-1]
            if pd.isna(vol_ma25) or vol_ma25 == 0:
                continue
            vol_ratio = df['volume'].iloc[-1] / vol_ma25
            close_chg = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
            if close_chg > 0 and vol_ratio >= 1.5:
                sym = f.replace('sh_', 'sh.').replace('sz_', 'sz.').replace('.parquet', '')
                results.append({
                    "symbol": sym,
                    "close_change_pct": round(close_chg, 2),
                    "volume_ratio": round(vol_ratio, 2),
                    "signal": "放量上涨"
                })
        except Exception:
            continue
    
    results.sort(key=lambda x: x['volume_ratio'], reverse=True)
    return {"total": len(results), "stocks": results[:50], "engine": "pandas"}


@router.get("/scan/volume-divergence")
async def scan_volume_divergence():
    """全市场扫描量价背离（DuckDB 加速）。"""
    if DUCKDB_AVAILABLE:
        t0 = time.time()
        df = duckdb_engine.scan_volume_divergence()
        elapsed = time.time() - t0
        logger.info(f"DuckDB volume-divergence scan: {len(df)} stocks in {elapsed:.2f}s")
        return {
            "total": len(df),
            "stocks": df.head(50).to_dict("records"),
            "engine": "duckdb",
            "elapsed_ms": round(elapsed * 1000, 1)
        }
    else:
        return _scan_volume_divergence_pandas()


def _scan_volume_divergence_pandas():
    """旧版 pandas 扫描（DuckDB 不可用时回退）。"""
    data_dir = engine.data_dir
    if not os.path.exists(data_dir):
        return {"stocks": [], "msg": "No data yet", "engine": "pandas"}
    
    results = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    
    for f in files:
        try:
            path = os.path.join(data_dir, f)
            df = pd.read_parquet(path, columns=['date', 'close', 'volume'])
            if len(df) < 55:
                continue
            df = df.tail(60)
            recent_high = df['close'].tail(20).max()
            current_close = df['close'].iloc[-1]
            if current_close < recent_high * 0.97:
                continue
            vol_ma25 = df['volume'].rolling(25).mean().iloc[-1]
            if pd.isna(vol_ma25) or vol_ma25 == 0:
                continue
            vol_ratio = df['volume'].iloc[-1] / vol_ma25
            close_chg = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
            if close_chg > 0 and vol_ratio < 0.8:
                sym = f.replace('sh_', 'sh.').replace('sz_', 'sz.').replace('.parquet', '')
                results.append({
                    "symbol": sym,
                    "close_change_pct": round(close_chg, 2),
                    "volume_ratio": round(vol_ratio, 2),
                    "signal": "量价背离",
                    "near_high": round(current_close, 2),
                    "20d_high": round(recent_high, 2)
                })
        except Exception:
            continue
    
    return {"total": len(results), "stocks": results[:50], "engine": "pandas"}


@router.post("/duckdb/query")
async def duckdb_query(req: DuckDBQueryRequest):
    """执行 DuckDB 全市场 SQL 查询。
    
    可用表: market_data
    列: symbol_raw, date, open, high, low, close, volume, amount, turn
    """
    if not DUCKDB_AVAILABLE:
        return {"error": "DuckDB 引擎不可用"}
    
    try:
        t0 = time.time()
        df = duckdb_engine.query(req.sql)
        elapsed = time.time() - t0
        
        if req.limit and len(df) > req.limit:
            df = df.head(req.limit)
        
        return {
            "rows": len(df),
            "columns": list(df.columns),
            "data": df.to_dict("records"),
            "elapsed_ms": round(elapsed * 1000, 1),
            "engine": "duckdb"
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/dump")
async def trigger_dump(limit: int = None):
    """Manually trigger data dump."""
    from services.stock_engine.dump_service import run_incremental_dump
    return run_incremental_dump(limit=limit)


@router.get("/analysis/{symbol}/comprehensive")
async def comprehensive_analysis(symbol: str, use_llm: bool = True):
    """
    个股综合分析 - 13提示词框架 + 执念/供需视角
    融合LLM定性分析 + 本地量化数据
    """
    from services.comprehensive_analysis import analyze_stock
    return await analyze_stock(symbol, use_llm=use_llm)

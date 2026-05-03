"""
Stock Analysis & Scanning Router for Info-Hub.
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import os
import pandas as pd

from services.stock_engine import get_engine

router = APIRouter(prefix="", tags=["A股分析"])
logger = logging.getLogger("info-hub.stock")

engine = get_engine()

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

@router.get("/analysis/{symbol}")
async def get_stock_analysis(symbol: str, date: Optional[str] = None, indicator: Optional[str] = None):
    """Get analysis for a single stock."""
    # 如果指定了 indicator，只查那一个
    if indicator:
        return engine.get_indicators(symbol, indicator, curr_date=date)
    
    res = {
        "ma25": engine.get_indicators(symbol, "ma_25", curr_date=date),
        "macd": engine.get_indicators(symbol, "macd", curr_date=date),
        "vol5": engine.get_indicators(symbol, "vol_5", curr_date=date),
        "vol60": engine.get_indicators(symbol, "vol_60", curr_date=date),
        "can": engine.get_indicators(symbol, "volume_ratio", curr_date=date)  # 新增压缩图CAN
    }
    return res

@router.get("/scan/ma25-up")
async def scan_ma25_up():
    """Scan all A-shares and return those with MA25 trending UP."""
    # This might take some time if we iterate all files.
    # Optimization: we only read the last few rows.
    data_dir = engine.data_dir
    if not os.path.exists(data_dir):
        return {"stocks": [], "msg": "No data yet"}
    
    results = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    
    # Limit to first 100 for quick response in demo, or remove limit for full scan
    # Let's do a full scan but optimized
    logger.info(f"Scanning {len(files)} stocks for MA25 Up...")
    
    for f in files:
        try:
            path = os.path.join(data_dir, f)
            # Only read tail
            df = pd.read_parquet(path, columns=['date', 'close'])
            if len(df) < 26:
                continue
            
            df = df.tail(26)
            ma25_curr = df['close'].rolling(25).mean().iloc[-1]
            ma25_prev = df['close'].rolling(25).mean().iloc[-2]
            
            if pd.notna(ma25_curr) and pd.notna(ma25_prev) and ma25_curr > ma25_prev:
                # Extract symbol from filename
                sym = f.replace('sh_', 'sh.').replace('sz_', 'sz.').replace('.parquet', '')
                results.append({"symbol": sym, "ma25": round(ma25_curr, 2)})
        except Exception:
            continue
            
    return {"total": len(results), "stocks": results[:50]} # Return top 50

@router.get("/scan/volume-up")
async def scan_volume_up():
    """Scan all A-shares for 放量上涨 (volume price resonance): 价格涨 + 量比>=150%."""
    data_dir = engine.data_dir
    if not os.path.exists(data_dir):
        return {"stocks": [], "msg": "No data yet"}
    
    results = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    logger.info(f"Scanning {len(files)} stocks for volume-up resonance...")
    
    for f in files:
        try:
            path = os.path.join(data_dir, f)
            df = pd.read_parquet(path, columns=['date', 'close', 'volume'])
            if len(df) < 26:
                continue
            
            df = df.tail(30)
            
            # 25日均量
            vol_ma25 = df['volume'].rolling(25).mean().iloc[-1]
            if pd.isna(vol_ma25) or vol_ma25 == 0:
                continue
            
            vol_ratio = df['volume'].iloc[-1] / vol_ma25
            close_chg = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
            
            # 放量上涨：收盘涨 + 量比>=1.5
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
    
    # 按量比排序
    results.sort(key=lambda x: x['volume_ratio'], reverse=True)
    return {"total": len(results), "stocks": results[:50]}


@router.get("/scan/volume-divergence")
async def scan_volume_divergence():
    """Scan for 量价背离: 股价创新高但量比下降（缩量上涨）。"""
    data_dir = engine.data_dir
    if not os.path.exists(data_dir):
        return {"stocks": [], "msg": "No data yet"}
    
    results = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    logger.info(f"Scanning {len(files)} stocks for volume divergence...")
    
    for f in files:
        try:
            path = os.path.join(data_dir, f)
            df = pd.read_parquet(path, columns=['date', 'close', 'volume'])
            if len(df) < 55:
                continue
            
            df = df.tail(60)
            
            # 近20日最高价
            recent_high = df['close'].tail(20).max()
            current_close = df['close'].iloc[-1]
            
            # 是否在高位（接近20日高点）
            if current_close < recent_high * 0.97:
                continue
            
            # 量比
            vol_ma25 = df['volume'].rolling(25).mean().iloc[-1]
            if pd.isna(vol_ma25) or vol_ma25 == 0:
                continue
            
            vol_ratio = df['volume'].iloc[-1] / vol_ma25
            
            # 缩量上涨：价格涨但量比<0.8
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
    
    return {"total": len(results), "stocks": results[:50]}


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

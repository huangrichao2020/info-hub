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
async def get_stock_analysis(symbol: str, date: Optional[str] = None):
    """Get analysis for a single stock."""
    res = {
        "ma25": engine.get_indicators(symbol, "ma_25", curr_date=date),
        "macd": engine.get_indicators(symbol, "macd", curr_date=date),
        "vol5": engine.get_indicators(symbol, "vol_5", curr_date=date),
        "vol60": engine.get_indicators(symbol, "vol_60", curr_date=date)
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

@router.post("/dump")
async def trigger_dump(limit: int = None):
    """Manually trigger data dump."""
    from services.stock_engine.dump_service import run_incremental_dump
    return run_incremental_dump(limit=limit)

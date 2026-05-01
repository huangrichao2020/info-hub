"""
Local cache data provider.
Reads pre-dumped Parquet files from the local disk.
Calculates indicators: MA25, VolMA5, VolMA60, MACD(6,13,6), 压缩图CAN量比.
"""
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("info-hub.stock_engine.cache")

class LocalStockCache:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _find_file(self, symbol: str) -> str:
        """Find the parquet file for a given symbol."""
        sym = symbol.upper().replace(" ", "")
        candidates = []
        
        if "." in sym:
            candidates.append(f"{sym.replace('.', '_').lower()}.parquet")
        elif sym.startswith("SH") or sym.startswith("SZ"):
            candidates.append(f"{sym[:2].lower()}_{sym[2:].lower()}.parquet")
        elif len(sym) == 6:
            candidates.append(f"sh_{sym.lower()}.parquet")
            candidates.append(f"sz_{sym.lower()}.parquet")
        else:
            candidates.append(f"{sym}.parquet")

        for name in candidates:
            path = os.path.join(self.data_dir, name)
            if os.path.exists(path):
                return path
        return None

    def load_data(self, symbol: str, days_needed: int = 100, curr_date: str = None) -> pd.DataFrame:
        """Load data and ensure we have enough history."""
        path = self._find_file(symbol)
        if not path:
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            if curr_date:
                df = df[df['date'] <= pd.to_datetime(curr_date)]
            
            if len(df) > days_needed + 50:
                return df.tail(days_needed + 50)
            return df
        except Exception as e:
            logger.error(f"Error loading {symbol}: {e}")
            return pd.DataFrame()

    def get_indicators(self, symbol: str, indicator: str, curr_date: str = None, look_back_days: int = 60) -> Dict:
        """Custom indicators as per user request."""
        needed = max(look_back_days, 60) 
        df = self.load_data(symbol, days_needed=needed, curr_date=curr_date)
        
        if df.empty or len(df) < 30:
            return {"status": "error", "msg": f"No sufficient data for {symbol}"}
            
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        
        indicator = indicator.lower().strip()
        result = {"symbol": symbol, "date": curr_date or str(df['date'].max().date())}

        # 1. 25 Day SMA & Trend
        if "ma_25" in indicator or "25sma" in indicator:
            df['ma_25'] = df['close'].rolling(25).mean()
            if len(df) < 26:
                return result
            
            val_curr = df['ma_25'].iloc[-1]
            val_prev = df['ma_25'].iloc[-2]
            
            trend = "up" if val_curr > val_prev else "down"
            result.update({
                "indicator": "MA25",
                "value": float(val_curr),
                "trend": trend,
                "signal": "watch" if trend == "up" else "observe"
            })

        # 2. Volume MA 5
        elif "vol_5" in indicator or "vol5" in indicator:
            df['vol_ma_5'] = df['volume'].rolling(5).mean()
            result.update({"indicator": "VolMA5", "value": float(df['vol_ma_5'].iloc[-1])})

        # 3. Volume MA 60
        elif "vol_60" in indicator or "vol60" in indicator:
            df['vol_ma_60'] = df['volume'].rolling(60).mean()
            result.update({"indicator": "VolMA60", "value": float(df['vol_ma_60'].iloc[-1])})

        # 4. MACD (6, 13, 6)
        elif "macd" in indicator:
            ema6 = df['close'].ewm(span=6, adjust=False).mean()
            ema13 = df['close'].ewm(span=13, adjust=False).mean()
            dif = ema6 - ema13
            dea = dif.ewm(span=6, adjust=False).mean()
            macd_val = 2 * (dif - dea)
            
            result.update({
                "indicator": "MACD_6_13_6",
                "DIF": float(dif.iloc[-1]),
                "DEA": float(dea.iloc[-1]),
                "MACD": float(macd_val.iloc[-1])
            })
        # 5. 压缩图CAN量比（25日均量，SQRT压缩）
        elif "volume_ratio" in indicator or "can" in indicator or "liangbi" in indicator:
            df['vol_ma_25'] = df['volume'].rolling(25).mean()
            df['vol_ratio_pct'] = df['volume'] / df['vol_ma_25'] * 100
            # SQRT压缩: 将量比映射到1-10的宽度等级
            df['can_width'] = np.sqrt(df['vol_ratio_pct'] / 100.0) * 5
            df['can_width'] = df['can_width'].clip(1, 10).round()
            
            vr = df['vol_ratio_pct'].iloc[-1]
            cw = df['can_width'].iloc[-1]
            
            # 量价方向判断
            close_chg = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100 if len(df) > 1 else 0
            
            result.update({
                "indicator": "压缩图CAN",
                "volume_ratio": round(float(vr), 2),
                "can_width": int(cw),
                "close_change_pct": round(float(close_chg), 2),
                "signal": _can_signal(vr, cw, close_chg)
            })

        else:
            result.update({"error": "Unknown indicator"})
            
        return result


def _can_signal(vol_ratio: float, can_width: float, close_chg: float) -> str:
    """根据量比、宽度、涨跌判断量价信号"""
    if close_chg > 0 and vol_ratio >= 150:
        return "放量上涨"  # 红色粗柱，资金买入
    elif close_chg > 0 and vol_ratio < 80:
        return "缩量上涨"  # 细红线，无量空涨
    elif close_chg < 0 and vol_ratio >= 150:
        return "放量下跌"  # 青色粗柱，资金出逃
    elif close_chg < 0 and vol_ratio < 80:
        return "缩量下跌"  # 缩量调整
    else:
        return "量价平衡"

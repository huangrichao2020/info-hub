"""
个股估值数据服务 - 从东方财富获取PE/PB历史数据
"""
import json
import logging
import os
import requests
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger("info-hub.valuation")

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache', 'valuation')
os.makedirs(CACHE_DIR, exist_ok=True)

EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


def _code_to_secid(code: str) -> str:
    """转换代码为东方财富secid格式"""
    code = code.replace('.', '').replace('_', '').upper()
    if code.startswith('6'):
        return f"1.{code}"
    return f"0.{code}"


def get_current_valuation(code: str) -> Optional[Dict[str, Any]]:
    """获取当前估值数据（PE/PB/总市值）"""
    secid = _code_to_secid(code)
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": secid,
        "fields": "f116,f117,f9,f23,f162,f167,f170,f171",  # 总市值/流通市值/PE动态/PE静态/PE(TTM)/PB/ROE/毛利率
        "ut": "fa5fd1943c7b386f172d6893dbbd1"
    }
    try:
        r = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=10)
        data = r.json()
        if not data.get("data"):
            return None
        d = data["data"]
        return {
            "code": code,
            "name": d.get("f57", ""),
            "total_mv": round(d.get("f116", 0) / 1e8, 1) if d.get("f116") else None,  # 亿元
            "float_mv": round(d.get("f117", 0) / 1e8, 1) if d.get("f117") else None,
            "pe_dynamic": d.get("f162") / 100 if d.get("f162") else None,
            "pe_static": d.get("f170") / 100 if d.get("f170") else None,
            "pe_ttm": d.get("f162") / 100 if d.get("f162") else None,
            "pb": d.get("f167") / 100 if d.get("f167") else None,
            "roe": d.get("f171") / 100 if d.get("f171") else None,
        }
    except Exception as e:
        logger.warning(f"获取{code}估值失败: {e}")
        return None


def get_pe_history(code: str, days: int = 365) -> List[Dict[str, Any]]:
    """获取PE/PB历史数据（通过东方财富）"""
    secid = _code_to_secid(code)
    url = "https://push2.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日线
        "fqt": "1",
        "end": "20500101",
        "lmt": str(days),
    }
    try:
        r = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=10)
        data = r.json()
        if not data.get("data") or not data["data"].get("klines"):
            return []
        
        result = []
        for line in data["data"]["klines"]:
            parts = line.split(",")
            if len(parts) >= 11:
                result.append({
                    "date": parts[0],
                    "close": float(parts[2]),
                    "pe_ttm": float(parts[5]) if parts[5] != "-" else None,
                    "pb": float(parts[6]) if parts[6] != "-" else None,
                })
        return result
    except Exception as e:
        logger.warning(f"获取{code}历史估值失败: {e}")
        return []


def calculate_percentile(code: str, value: float, field: str = "pe_ttm") -> Optional[float]:
    """计算当前估值在历史中的百分位"""
    cache_path = os.path.join(CACHE_DIR, f"{code.replace('.', '_').replace('/', '_')}_pe.json")
    
    # 尝试从缓存读取
    history = []
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                history = json.load(f)
        except:
            history = []
    
    # 缓存不足则拉取
    if len(history) < 100:
        history = get_pe_history(code, days=730)  # 2年
        if history:
            try:
                with open(cache_path, 'w') as f:
                    json.dump(history, f)
            except:
                pass
    
    if not history:
        return None
    
    # 计算百分位
    values = [h[field] for h in history if h.get(field) is not None]
    if not values:
        return None
    
    values.sort()
    below = sum(1 for v in values if v < value)
    return round(below / len(values) * 100, 1)

"""
A股技术评分 — 用 akshare 新浪数据（直连，无需代理）
复刻 a-share-technical-analysis-cskill 的核心评分逻辑
"""
import sys
import json
import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import akshare as ak


def fetch_kline(symbol: str, days: int = 250) -> pd.DataFrame:
    """用 stock_zh_a_daily 拿 K 线"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=int(days * 1.5))).strftime("%Y%m%d")

    # 转换 symbol: 6xxxxx -> sh, 0xxxxx/3xxxxx -> sz
    if symbol.startswith("6"):
        full_symbol = f"sh{symbol}"
    elif symbol.startswith(("0", "3")):
        full_symbol = f"sz{symbol}"
    else:
        full_symbol = symbol

    df = ak.stock_zh_a_daily(symbol=full_symbol, start_date=start, end_date=end, adjust="qfq")
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.sort_values("date").reset_index(drop=True)
    df = df.tail(days).reset_index(drop=True)
    return df


def compute_indicators(df: pd.DataFrame) -> dict:
    """计算 MA / RSI / MACD / 布林带 等指标"""
    if df.empty or len(df) < 30:
        return {"error": "数据不足 30 条"}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # MA
    ma5 = close.rolling(5).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(df) >= 60 else None

    # RSI 14
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi14 = float((100 - 100 / (1 + rs)).iloc[-1]) if not rs.isna().iloc[-1] else 50

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2

    # 布林带 (20, 2)
    boll_mid = ma20
    std20 = close.rolling(20).std().iloc[-1]
    boll_upper = boll_mid + 2 * std20
    boll_lower = boll_mid - 2 * std20

    # 20 日涨跌幅
    pct_20d = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(df) >= 20 else 0
    pct_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(df) >= 5 else 0

    # 量比（最近 5 日均量 / 60 日均量）
    avg_vol_5 = volume.tail(5).mean()
    avg_vol_60 = volume.tail(60).mean() if len(df) >= 60 else avg_vol_5
    vol_ratio = float(avg_vol_5 / avg_vol_60) if avg_vol_60 > 0 else 1

    return {
        "close": float(close.iloc[-1]),
        "ma5": round(float(ma5), 2),
        "ma20": round(float(ma20), 2),
        "ma60": round(float(ma60), 2) if ma60 else None,
        "rsi14": round(rsi14, 1),
        "macd_dif": round(float(dif.iloc[-1]), 3),
        "macd_dea": round(float(dea.iloc[-1]), 3),
        "macd_bar": round(float(macd_bar.iloc[-1]), 3),
        "boll_upper": round(float(boll_upper), 2),
        "boll_mid": round(float(boll_mid), 2),
        "boll_lower": round(float(boll_lower), 2),
        "pct_5d": round(pct_5d, 2),
        "pct_20d": round(pct_20d, 2),
        "vol_ratio": round(vol_ratio, 2),
        "highest_20d": round(float(high.tail(20).max()), 2),
        "lowest_20d": round(float(low.tail(20).min()), 2),
    }


def score(indicators: dict) -> tuple:
    """评分 -10 到 +10，返回 (score, rating, signals)"""
    score = 0
    signals = []

    close = indicators.get("close", 0)
    ma5 = indicators.get("ma5", 0)
    ma20 = indicators.get("ma20", 0)
    ma60 = indicators.get("ma60") or 0
    rsi = indicators.get("rsi14", 50)
    macd_bar = indicators.get("macd_bar", 0)
    boll_up = indicators.get("boll_upper", 0)
    boll_lo = indicators.get("boll_lower", 0)
    pct_5d = indicators.get("pct_5d", 0)
    pct_20d = indicators.get("pct_20d", 0)
    vol_ratio = indicators.get("vol_ratio", 1)

    # 1. MA 趋势 (max ±3)
    if ma5 > ma20 > ma60 and ma5 > 0:
        score += 3
        signals.append("多头排列 MA5>MA20>MA60 +3")
    elif ma5 < ma20 < ma60 and ma60 > 0:
        score -= 3
        signals.append("空头排列 MA5<MA20<MA60 -3")
    elif ma5 > ma20 and ma5 > 0:
        score += 1
        signals.append("MA5 上穿 MA20 +1")
    elif ma5 < ma20 and ma20 > 0:
        score -= 1
        signals.append("MA5 下穿 MA20 -1")

    # 2. RSI (max ±2)
    if rsi >= 80:
        score -= 2
        signals.append(f"RSI={rsi} 超买 -2")
    elif rsi >= 65:
        score += 2
        signals.append(f"RSI={rsi} 强势 +2")
    elif rsi <= 30:
        score += 1  # 超卖反弹机会
        signals.append(f"RSI={rsi} 超卖反弹 +1")
    elif rsi <= 45:
        score -= 1
        signals.append(f"RSI={rsi} 偏弱 -1")

    # 3. MACD (max ±2)
    if macd_bar > 0:
        score += 2 if macd_bar > 0.1 else 1
        signals.append(f"MACD 红柱 {macd_bar} +{2 if macd_bar > 0.1 else 1}")
    else:
        score -= 2 if macd_bar < -0.1 else 1
        signals.append(f"MACD 绿柱 {macd_bar} -{2 if macd_bar < -0.1 else 1}")

    # 4. 涨幅动能 (max ±2)
    if pct_5d >= 10:
        score += 2
        signals.append(f"5日 +{pct_5d}% 强势 +2")
    elif pct_5d >= 3:
        score += 1
        signals.append(f"5日 +{pct_5d}% 偏强 +1")
    elif pct_5d <= -10:
        score -= 2
        signals.append(f"5日 {pct_5d}% 弱势 -2")
    elif pct_5d <= -3:
        score -= 1
        signals.append(f"5日 {pct_5d}% 偏弱 -1")

    # 5. 量能 (max ±1)
    if vol_ratio >= 2:
        score += 1
        signals.append(f"量比 {vol_ratio} 放量 +1")
    elif vol_ratio <= 0.5:
        score -= 1
        signals.append(f"量比 {vol_ratio} 缩量 -1")

    # 6. 布林带位置 (max ±1)
    if boll_up > 0 and close > boll_up:
        score += 1
        signals.append("突破布林上轨 +1")
    elif boll_lo > 0 and close < boll_lo:
        score -= 1
        signals.append("跌破布林下轨 -1")

    # 评级
    if score >= 7:
        rating = "强势"
    elif score >= 3:
        rating = "偏强"
    elif score >= -2:
        rating = "中性"
    elif score >= -6:
        rating = "偏弱"
    else:
        rating = "弱势"

    return score, rating, signals


def analyze(symbol: str) -> dict:
    """主分析函数"""
    df = fetch_kline(symbol, days=250)
    if df.empty:
        return {"error": f"无法获取 {symbol} 的 K 线数据"}

    indicators = compute_indicators(df)
    if "error" in indicators:
        return {"error": indicators["error"]}

    s, rating, signals = score(indicators)

    return {
        "symbol": symbol,
        "as_of": df["date"].iloc[-1].strftime("%Y-%m-%d"),
        "indicators": indicators,
        "score": s,
        "rating": rating,
        "signals": signals,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True, help="股票代码，如 300227")
    parser.add_argument("--days", type=int, default=250)
    args = parser.parse_args()

    result = analyze(args.symbol)
    print(json.dumps(result, ensure_ascii=False, indent=2))
"""
回测引擎 — 基于历史K线的信号回测
买点：执念六阶段信号触发
卖点：住相破裂信号触发 或 止盈止损
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger("info-hub.backtester")

# ═══════════════════════════════════════════════════════
# 一、K线数据预处理
# ═══════════════════════════════════════════════════════

def prepare_kline_data(klines: List[Dict]) -> List[Dict]:
    """
    将原始K线数据转换为标准化格式
    补充 MA5/MA20/MA60，计算成交量加权价格等
    """
    if not klines:
        return []

    result = []
    closes = []

    for i, k in enumerate(klines):
        close = float(k.get("收盘", k.get("close", 0)) or 0)
        opens = float(k.get("开盘", k.get("open", 0)) or 0)
        high = float(k.get("最高", k.get("high", 0)) or 0)
        low = float(k.get("最低", k.get("low", 0)) or 0)
        vol = float(k.get("成交量", k.get("volume", 0)) or 0)
        date = str(k.get("日期", k.get("date", "")))

        closes.append(close)

        # 移动平均
        ma5 = sum(closes[-5:]) / min(5, len(closes)) if len(closes) >= 1 else close
        ma20 = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 1 else close
        ma60 = sum(closes[-60:]) / min(60, len(closes)) if len(closes) >= 1 else close

        # 涨幅
        prev_close = closes[-2] if len(closes) > 1 else close
        change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0

        # 成交量均线
        vols = [float(x.get("成交量", x.get("volume", 0)) or 0) for x in klines[:i+1]]
        vol_ma5 = sum(vols[-5:]) / min(5, len(vols))

        result.append({
            "date": date,
            "open": opens,
            "high": high,
            "low": low,
            "close": close,
            "volume": vol,
            "change_pct": round(change_pct, 2),
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "vol_ma5": round(vol_ma5, 2),
            "vol_ratio": round(vol / vol_ma5, 2) if vol_ma5 > 0 else 0,
            "close_above_ma5": close > ma5,
            "close_above_ma20": close > ma20,
            "close_above_ma60": close > ma60,
        })

    return result


# ═══════════════════════════════════════════════════════
# 二、执念阶段回测识别
# ═══════════════════════════════════════════════════════

def detect_phase_from_kline(klines: List[Dict]) -> List[Dict]:
    """
    基于历史K线识别执念阶段演变
    返回每日的执念阶段标签
    """
    if not klines:
        return []

    result = []
    for i, k in enumerate(klines):
        phase = "震荡"
        change = k["change_pct"]
        vol_ratio = k["vol_ratio"]
        zt = change >= 9.9
        dt = change <= -9.9

        # 简单规则
        if zt and vol_ratio > 2:
            phase = "游资点火期"
        elif change > 3 and vol_ratio > 1.5:
            phase = "机构试错期"
        elif change > 5 and vol_ratio > 2:
            phase = "散户共识期"
        elif change < -3:
            phase = "派发期"
        else:
            phase = "震荡"

        result.append({**k, "phase": phase})

    return result


# ═══════════════════════════════════════════════════════
# 三、回测单个信号
# ═══════════════════════════════════════════════════════

def backtest_signal(klines: List[Dict],
                    signal_type: str = "ma20_break",
                    stop_loss_pct: float = 7.0,
                    take_profit_pct: float = 15.0,
                    holding_days_max: int = 10) -> Dict[str, Any]:
    """
    回测单个买入信号
    signal_type: 'ma20_break' | 'zt_confirm' | 'dip_buy'
    返回交易记录和统计数据
    """
    klines = prepare_kline_data(klines)
    if not klines:
        return {"error": "K线数据不足"}

    trades = []
    equity_curve = []
    initial_capital = 100000  # 10万模拟资金

    # 模拟撮合
    capital = initial_capital
    position = 0
    entry_price = 0
    entry_date = ""

    i = 0
    while i < len(klines):
        k = klines[i]

        if position == 0:
            # 无持仓，寻找买入信号
            buy_signal = False
            signal_reason = ""

            if signal_type == "ma20_break":
                # MA20突破：前日<MA20，今日>MA20，量比>1.5
                if i > 1:
                    prev = klines[i-1]
                    if (prev["close"] <= prev["ma20"] and k["close"] > k["ma20"] and k["vol_ratio"] > 1.5):
                        buy_signal = True
                        signal_reason = f"MA20突破，量比{k['vol_ratio']}"

            elif signal_type == "zt_confirm":
                # 涨停次日确认
                if k["change_pct"] >= 9.9:
                    buy_signal = True
                    signal_reason = f"涨停{abs(k['change_pct']):.1f}%"

            elif signal_type == "dip_buy":
                # 回踩MA20
                if k["close"] <= k["ma20"] * 1.02 and k["close"] >= k["ma20"] * 0.98 and k["vol_ratio"] > 1.2:
                    buy_signal = True
                    signal_reason = f"回踩MA20，量比{k['vol_ratio']}"

            if buy_signal:
                entry_price = k["close"]
                entry_date = k["date"]
                position = int(capital / entry_price / 100) * 100  # 按手买
                cost = position * entry_price
                capital -= cost
                i += 1
                holding_days = 0
                max_drawdown = 0.0
                peak = entry_price
                continue

        else:
            # 持仓中
            holding_days += 1
            current_price = k["close"]

            # 权益
            current_value = capital + position * current_price
            total_value = position * entry_price + (initial_capital - position * entry_price)
            pnl_pct = (current_value - initial_capital) / initial_capital * 100

            # 回撤跟踪
            if current_price > peak:
                peak = current_price
            drawdown = (peak - current_price) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

            equity_curve.append({
                "date": k["date"],
                "value": round(current_value, 2),
                "pnl_pct": round(pnl_pct, 2),
            })

            # 卖出条件
            sell_reason = ""
            sell = False

            # 止损
            if current_price < entry_price * (1 - stop_loss_pct / 100):
                sell = True
                sell_reason = f"止损-{stop_loss_pct}%"
            # 止盈
            elif current_price >= entry_price * (1 + take_profit_pct / 100):
                sell = True
                sell_reason = f"止盈+{take_profit_pct}%"
            # 持仓超时
            elif holding_days >= holding_days_max:
                sell = True
                sell_reason = f"超时{holding_days}天"
            # MA20跌破（跟踪止损）
            elif current_price < k["ma20"]:
                sell = True
                sell_reason = "MA20止损"

            if sell:
                sell_price = current_price
                pnl = (sell_price - entry_price) * position
                pnl_pct_final = (sell_price - entry_price) / entry_price * 100
                win = pnl > 0

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": k["date"],
                    "entry_price": entry_price,
                    "exit_price": sell_price,
                    "shares": position,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct_final, 2),
                    "holding_days": holding_days,
                    "max_drawdown": round(max_drawdown, 2),
                    "sell_reason": sell_reason,
                    "win": win,
                })

                # 结算
                capital += position * sell_price
                position = 0
                entry_price = 0

        i += 1

    # 最终权益
    final_value = capital + position * (klines[-1]["close"] if klines else 0)
    total_return = (final_value - initial_capital) / initial_capital * 100

    # 统计
    wins = [t for t in trades if t["win"]]
    losses = [t for t in trades if not t["win"]]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_pnl = sum(t["pnl"] for t in trades) / len(trades) if trades else 0
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    max_drawdown_overall = max([t["max_drawdown"] for t in trades]) if trades else 0

    return {
        "signal_type": signal_type,
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return, 2),
        "total_trades": len(trades),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
        "max_drawdown_pct": round(max_drawdown_overall, 2),
        "trades": trades,
        "equity_curve": equity_curve,
        "start_date": klines[0]["date"] if klines else "",
        "end_date": klines[-1]["date"] if klines else "",
    }


# ═══════════════════════════════════════════════════════
# 四、批量回测（多只股票 + 多策略）
# ═══════════════════════════════════════════════════════

def batch_backtest(stock_codes: List[str],
                   start_date: str = "",
                   end_date: str = "",
                   signal_types: List[str] = None) -> List[Dict]:
    """批量回测多只股票"""
    if signal_types is None:
        signal_types = ["ma20_break", "zt_confirm", "dip_buy"]

    results = []
    for code in stock_codes:
        klines = _fetch_backtest_kline(code)
        if len(klines) < 60:
            continue

        for sig_type in signal_types:
            result = backtest_signal(
                klines,
                signal_type=sig_type,
                stop_loss_pct=7.0,
                take_profit_pct=15.0,
            )
            result["stock_code"] = code
            result["signal_type"] = sig_type
            results.append(result)

    # 按总收益率排序
    results.sort(key=lambda x: x["total_return_pct"], reverse=True)
    return results


def _fetch_backtest_kline(code: str) -> List[Dict]:
    """获取回测用K线数据"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date="20240101",
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq"
        )
        return df.to_dict("records")
    except Exception:
        return []


# ═══════════════════════════════════════════════════════
# 五、信号有效性评分
# ═══════════════════════════════════════════════════════

def evaluate_signal_quality(results: List[Dict]) -> Dict[str, Any]:
    """评估信号质量"""
    if not results:
        return {"verdict": "无数据", "score": 0}

    # 过滤有效结果
    valid = [r for r in results if "error" not in r]
    if not valid:
        return {"verdict": "回测失败", "score": 0}

    # 汇总统计
    total_return_avg = sum(r["total_return_pct"] for r in valid) / len(valid)
    win_rate_avg = sum(r["win_rate_pct"] for r in valid) / len(valid)
    max_dd_avg = sum(r["max_drawdown_pct"] for r in valid) / len(valid)
    trades_total = sum(r["total_trades"] for r in valid)

    # 胜率 x 收益率评分
    raw_score = win_rate_avg * 0.4 + max(0, total_return_avg) * 2

    # 最大回撤惩罚
    if max_dd_avg > 15:
        raw_score *= 0.7
    elif max_dd_avg > 10:
        raw_score *= 0.85

    # 交易次数置信度
    if trades_total < 10:
        verdict = "信号样本不足，建议积累更多数据"
        score = raw_score * 0.8
    elif total_return_avg > 10 and win_rate_avg > 55:
        verdict = "信号有效，可积极使用"
        score = min(raw_score, 95)
    elif total_return_avg > 5 and win_rate_avg > 50:
        verdict = "信号有效，可适度使用"
        score = min(raw_score, 80)
    elif total_return_avg > 0:
        verdict = "信号效果一般，需谨慎"
        score = min(raw_score * 0.8, 60)
    else:
        verdict = "信号负向，禁用"
        score = raw_score * 0.5

    return {
        "verdict": verdict,
        "score": round(score, 1),
        "total_return_avg": round(total_return_avg, 2),
        "win_rate_avg": round(win_rate_avg, 1),
        "max_drawdown_avg": round(max_dd_avg, 2),
        "total_trades": trades_total,
        "stocks_tested": len(valid),
    }

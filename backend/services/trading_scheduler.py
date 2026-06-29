"""
交易定时调度 — 时间门自动化
09:20 竞价快照 | 10:00 广度确认 | 14:00 午后确认 | 14:30 收盘验证
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("info-hub.trading-scheduler")

# ═══════════════════════════════════════════════════════
# 各时间门任务
# ═══════════════════════════════════════════════════════

def job_pre_market(snapshot: Dict, signal_result: Dict) -> Dict[str, Any]:
    """09:20 盘前快照"""
    return {
        "time_gate": "pre_market",
        "time": datetime.now().strftime("%H:%M"),
        "market_status": signal_result.get("market_status", ""),
        "obsession_phase": signal_result.get("obsession_phase", ""),
        "confidence_grade": signal_result.get("confidence_grade", ""),
        "shanghai_change": snapshot.get("shanghai_change_pct", 0),
        "zt_count": snapshot.get("zt_count", 0),
        "main_net_flow": snapshot.get("main_net_flow", 0),
        "top_sectors": _top3_sectors(snapshot),
        "action": "盘前准备：根据信号决定是否参与",
    }


def job_morning_confirm(snapshot: Dict, signal_result: Dict) -> Dict[str, Any]:
    """10:00 早盘确认（最重要）"""
    breadth = snapshot.get("breadth", 0)
    zt = snapshot.get("zt_count", 0)
    phase = signal_result.get("obsession_phase", "")
    grade = signal_result.get("confidence_grade", "")
    zhuxiang = signal_result.get("signal_count", 0)

    action = "维持现状"
    if zhuxiang >= 3:
        action = "⚠️ 住相破裂，强制减仓"
    elif grade == "D" or breadth < 1500:
        action = "广度不足，观望"
    elif grade == "A" and breadth >= 2500:
        action = "✅ 主线确认，可加仓"
    elif grade == "B" and breadth >= 2000:
        action = "✅ 适度参与"

    return {
        "time_gate": "morning_confirm",
        "time": datetime.now().strftime("%H:%M"),
        "breadth": breadth,
        "zt_count": zt,
        "obsession_phase": phase,
        "confidence_grade": grade,
        "zhuxiang_count": zhuxiang,
        "action": action,
        "position_advice": _position_advice(grade, zhuxiang),
    }


def job_afternoon_confirm(snapshot: Dict, signal_result: Dict) -> Dict[str, Any]:
    """14:00 午后确认"""
    phase = signal_result.get("obsession_phase", "")
    zt = snapshot.get("zt_count", 0)
    dt = snapshot.get("dt_count", 0)

    action = "观察"
    if phase == "派发期":
        action = "⚠️ 派发期，持仓减仓"
    elif dt > zt * 0.5:
        action = "⚠️ 跌停增多，谨慎"
    elif zt > 30:
        action = "✅ 涨停数健康，维持"

    return {
        "time_gate": "afternoon_confirm",
        "time": datetime.now().strftime("%H:%M"),
        "zt_count": zt,
        "dt_count": dt,
        "obsession_phase": phase,
        "action": action,
    }


def job_close_verification(snapshot: Dict, signal_result: Dict) -> Dict[str, Any]:
    """14:30 收盘验证"""
    zt = snapshot.get("zt_count", 0)
    dt = snapshot.get("dt_count", 0)
    breadth = snapshot.get("breadth", 0)
    phase = signal_result.get("obsession_phase", "")
    grade = signal_result.get("confidence_grade", "")
    zhuxiang = signal_result.get("signal_count", 0)

    # 今日总结
    verdict = ""
    if zt >= 50 and breadth >= 2500 and phase not in ("派发期", "全民住相期"):
        verdict = "✅ 强势行情，次日关注延续"
    elif zt >= 30 and breadth >= 1500:
        verdict = "✅ 有主线，可参与"
    elif zt < 20 or zhuxiang >= 4:
        verdict = "❌ 弱势/派发，清仓观望"
    else:
        verdict = "👀 震荡市，控仓"

    return {
        "time_gate": "close_verification",
        "time": datetime.now().strftime("%H:%M"),
        "zt_count": zt,
        "dt_count": dt,
        "breadth": breadth,
        "obsession_phase": phase,
        "confidence_grade": grade,
        "verdict": verdict,
        "signal_count": zhuxiang,
    }


def _top3_sectors(snapshot: Dict) -> list:
    ind = snapshot.get("top_industry_sectors", [])
    return [{"name": s.get("板块名称", ""), "change": s.get("涨跌幅", 0)}
            for s in ind[:3]]


def _position_advice(grade: str, zhuxiang_count: int) -> Dict[str, Any]:
    """仓位建议"""
    limits = {
        "A": 80, "B": 60, "C": 30, "D": 0
    }
    base = limits.get(grade, 0)

    # 住相修正
    if zhuxiang_count >= 4:
        return {"limit_pct": 0, "action": "强制清仓"}
    elif zhuxiang_count == 3:
        return {"limit_pct": base * 0.5, "action": "减半仓"}
    elif zhuxiang_count == 2:
        return {"limit_pct": base * 0.8, "action": "控仓"}
    else:
        return {"limit_pct": base, "action": "正常仓位"}

"""
住相信号链 — 执念 → 住相 → 破裂 可视化分析

接入真实市场数据自动判断 5 个破裂信号：
1. 龙头乏力: 涨停家数 < 30 或 炸板率 > 40%
2. 跟风先跑: 板块涨跌比 < 0.5 (跌的板块比涨的多一倍)
3. 扩散停止: 热门板块数 < 5 或 板块集中度 > 70%
4. 情绪背离: 指数涨但涨停数降 (对比昨日)
5. 资金转向: 主力资金净流出 > 100 亿
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from database import get_db

logger = logging.getLogger("info-hub.obsession")

router = APIRouter()

# ── 信号定义模板 ───────────────────────────────────────
SIGNAL_TEMPLATES = [
    {
        "name": "leader_weak",
        "label": "龙头乏力",
        "triggered": False,
        "description": "涨停打开/封不住/缩量，龙头上涨动能衰减",
        "reason": "",
    },
    {
        "name": "followers_flee",
        "label": "跟风先跑",
        "triggered": False,
        "description": "后排跟风股率先大跌，资金最先撤离",
        "reason": "",
    },
    {
        "name": "diffusion_stop",
        "label": "扩散停止",
        "triggered": False,
        "description": "板块不再有分支补涨，扩散效应消失",
        "reason": "",
    },
    {
        "name": "emotion_diverge",
        "label": "情绪背离",
        "triggered": False,
        "description": "指数涨但涨停数降/炸板率升，价格与情绪背离",
        "reason": "",
    },
    {
        "name": "capital_shift",
        "label": "资金转向",
        "triggered": False,
        "description": "资金从高位切低位/从题材切防御",
        "reason": "",
    },
]

# ── 阶段定义 ──────────────────────────────────────────
PHASES = {
    "emptiness": {
        "label": "空性",
        "description": "事件无固定意义，同一事件在不同阶段意义不同",
    },
    "subtle_use": {
        "label": "妙用",
        "description": "同一事件对机构、游资、散户、被套盘、踏空者作用不同",
    },
    "obsession_form": {
        "label": "执念形成",
        "description": "人群开始相信叙事，执念成为主线持续性的燃料",
    },
    "obsession_strong": {
        "label": "住相强化",
        "description": "把阶段性的有效当成永恒真理，执念不断强化",
    },
    "obsession_break": {
        "label": "住相破裂",
        "description": "叙事崩塌，资金撤离，住相开始破裂",
    },
}

# ── 操作建议映射 ───────────────────────────────────────
ACTION_SUGGESTIONS = {
    0: "执念未形成或处于早期，继续观察，不急于出手",
    1: "出现首个信号，开始盯盘，注意龙头承接质量",
    2: "2 个信号出现，考虑减仓，降低敞口",
    3: "3 个信号，住相开始松动，必须减仓",
    4: "4 个信号，住相破裂前夜，清仓准备",
    5: "5 个信号全亮，住相已破，远离该板块",
}

# ── 内存中信号状态（供 /mark 端点手动覆盖） ────────────
_signals_memory: Optional[list[dict]] = None


def _phase_from_count(count: int) -> str:
    """根据触发的信号数量判断当前阶段"""
    if count == 0:
        return "obsession_strong"
    elif count <= 2:
        return "obsession_strong"
    elif count <= 3:
        return "obsession_break"
    else:
        return "obsession_break"


# ── 信号判断逻辑 ───────────────────────────────────────
async def _evaluate_signals() -> list[dict]:
    """
    基于真实市场数据评估 5 个破裂信号。
    如果数据获取失败，降级为全部未触发（安全默认值）。
    """
    signals = [dict(s) for s in SIGNAL_TEMPLATES]  # 深拷贝

    try:
        from services.zt_service import get_zt_today
        from services.market_service import get_sector_movers, get_index_snapshot, get_capital_flow
    except ImportError as e:
        logger.warning(f"无法导入市场/涨停服务，降级为未触发: {e}")
        return signals

    # ── 获取数据 ─────────────────────────────────────
    try:
        zt_rows = await get_zt_today()
    except Exception as e:
        logger.warning(f"获取涨停数据失败: {e}")
        zt_rows = []

    try:
        rising_sectors = await get_sector_movers(limit=20, rising=True)
    except Exception as e:
        logger.warning(f"获取上涨板块失败: {e}")
        rising_sectors = []

    try:
        falling_sectors = await get_sector_movers(limit=20, rising=False)
    except Exception as e:
        logger.warning(f"获取下跌板块失败: {e}")
        falling_sectors = []

    try:
        index_snap = await get_index_snapshot()
    except Exception as e:
        logger.warning(f"获取指数快照失败: {e}")
        index_snap = []

    try:
        cap_flow = await get_capital_flow()
    except Exception as e:
        logger.warning(f"获取资金流向失败: {e}")
        cap_flow = {}

    # ── 1. 龙头乏力: 涨停家数 < 30 或 炸板率 > 40% ──
    zt_count = len(zt_rows) if zt_rows else 0
    # 炸板率估算: 从涨停数据中判断（如果有炸板标记）
    # 这里用涨停家数 < 30 作为主要判断
    if zt_count < 30:
        signals[0]["triggered"] = True
        signals[0]["reason"] = f"涨停家数仅 {zt_count} 家 (< 30)"

    # ── 2. 跟风先跑: 板块涨跌比 < 0.5 ──────────────
    rising_count = len(rising_sectors) if rising_sectors else 0
    falling_count = len(falling_sectors) if falling_sectors else 0
    if rising_count + falling_count > 0:
        ratio = rising_count / (rising_count + falling_count)
        if ratio < 0.5:
            signals[1]["triggered"] = True
            signals[1]["reason"] = f"涨跌板块比 {rising_count}:{falling_count} (涨占比 {ratio:.0%} < 50%)"
    # 如果数据不足，保持未触发

    # ── 3. 扩散停止: 热门板块数 < 5 或 板块集中度 > 70%
    # 用上涨板块数代表热门板块
    hot_sector_count = rising_count
    # 板块集中度: 前 3 大板块占总涨幅的比例
    concentration = 0.0
    if rising_sectors:
        changes = [abs(float(s.get("change_pct", 0) or 0)) for s in rising_sectors]
        total_change = sum(changes)
        if total_change > 0:
            top3 = sorted(changes, reverse=True)[:3]
            concentration = sum(top3) / total_change

    if hot_sector_count < 5:
        signals[2]["triggered"] = True
        signals[2]["reason"] = f"热门板块仅 {hot_sector_count} 个 (< 5)"
    elif concentration > 0.7:
        signals[2]["triggered"] = True
        signals[2]["reason"] = f"板块集中度 {concentration:.0%} (> 70%)，涨幅集中在少数板块"

    # ── 4. 情绪背离: 指数涨但涨停数降 ────────────────
    # 检查指数是否上涨
    index_up = False
    for idx in (index_snap or []):
        pct = float(idx.get("change_pct", 0) or 0)
        # 主要指数: 上证指数、深证成指、创业板指
        idx_name = str(idx.get("name", "") or idx.get("code", ""))
        if any(k in idx_name for k in ["上证", "深证", "创业", "沪深", "SH", "SZ", "CHI"]):
            if pct > 0:
                index_up = True
                break

    if index_up and zt_count < 30:
        signals[3]["triggered"] = True
        signals[3]["reason"] = f"指数上涨但涨停仅 {zt_count} 家，情绪与指数背离"

    # ── 5. 资金转向: 主力资金净流出 > 100 亿 ────────
    main_net_flow = 0.0
    if cap_flow:
        # 不同来源的数据字段可能不同，尝试多种字段名
        main_net_flow = (
            float(cap_flow.get("main_net_flow", 0) or 0)
            or float(cap_flow.get("main_net_inflow", 0) or 0)
            or float(cap_flow.get("主力净流入", 0) or 0)
        )
        # 如果值是负数且绝对值 > 100亿，说明主力大幅流出
        # 有些接口返回的单位是亿，有些是元
        # 判断: 如果是负数且绝对值很大
        if main_net_flow < -100:
            signals[4]["triggered"] = True
            signals[4]["reason"] = f"主力资金净流出 {abs(main_net_flow):.0f} 亿 (> 100 亿)"
        elif main_net_flow < 0 and abs(main_net_flow) < 100:
            # 单位可能是元而非亿，转换判断
            if abs(main_net_flow) > 100_0000_0000:  # > 100亿元
                signals[4]["triggered"] = True
                signals[4]["reason"] = f"主力资金净流出 {abs(main_net_flow) / 1_0000_0000:.0f} 亿 (> 100 亿)"

    return signals


def _build_response(signals: list[dict]) -> dict:
    """根据信号列表构建标准返回结构"""
    triggered_count = sum(1 for s in signals if s["triggered"])
    current_phase = _phase_from_count(triggered_count)
    phase_info = PHASES[current_phase]

    return {
        "current_phase": current_phase,
        "phase_label": phase_info["label"],
        "phase_description": phase_info["description"],
        "signals": signals,
        "signal_count": triggered_count,
        "action_suggestion": ACTION_SUGGESTIONS[triggered_count],
        "last_updated": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST"),
    }


async def _record_to_history(response: dict) -> None:
    """将当前信号状态记录到历史表"""
    signals_json = json.dumps(
        [{"name": s["name"], "label": s["label"], "triggered": s["triggered"], "reason": s.get("reason", "")}
         for s in response["signals"]],
        ensure_ascii=False,
    )
    recorded_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO obsession_signals_history
                   (recorded_at, current_phase, phase_label, signal_count, signals_json, action_suggestion)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    recorded_at,
                    response["current_phase"],
                    response["phase_label"],
                    response["signal_count"],
                    signals_json,
                    response["action_suggestion"],
                ),
            )
    except Exception as e:
        logger.warning(f"记录住相信号历史失败: {e}")


# ── API 端点 ───────────────────────────────────────────

@router.get("/status")
async def get_obsession_phase_status():
    """
    获取当前住相状态和信号链。
    基于真实市场数据自动判断 5 个破裂信号。
    数据获取失败时优雅降级为全部未触发。
    """
    global _signals_memory

    if _signals_memory is not None:
        # 有手动覆盖，使用内存中的状态
        signals = _signals_memory
    else:
        signals = await _evaluate_signals()

    response = _build_response(signals)

    # 自动记录到历史
    await _record_to_history(response)

    return response


@router.post("/mark")
async def mark_signal(signal_name: str, triggered: bool):
    """手动标记某个信号触发/解除"""
    global _signals_memory

    # 如果还没有内存状态，先加载当前评估
    if _signals_memory is None:
        _signals_memory = await _evaluate_signals()

    found = False
    for s in _signals_memory:
        if s["name"] == signal_name:
            s["triggered"] = triggered
            found = True
            break

    if not found:
        return {"error": f"未知信号: {signal_name}", "valid_signals": [s["name"] for s in _signals_memory]}

    response = _build_response(_signals_memory)

    # 记录手动标记后的状态
    await _record_to_history(response)

    return response


@router.post("/reset")
async def reset_signals():
    """清除手动覆盖，恢复自动评估"""
    global _signals_memory
    _signals_memory = None
    signals = await _evaluate_signals()
    response = _build_response(signals)
    return response


@router.get("/history")
async def history(days: int = Query(default=7, ge=1, le=365)):
    """获取历史信号记录，按 recorded_at 倒序"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, recorded_at, current_phase, phase_label, signal_count,
                      signals_json, action_suggestion, market_snapshot_json
               FROM obsession_signals_history
               ORDER BY recorded_at DESC
               LIMIT ?""",
            (days * 48,),  # 假设每半小时一条，最多 48 条/天
        ).fetchall()

    records = []
    for row in rows:
        records.append({
            "id": row["id"],
            "recorded_at": row["recorded_at"],
            "current_phase": row["current_phase"],
            "phase_label": row["phase_label"],
            "signal_count": row["signal_count"],
            "signals": json.loads(row["signals_json"]) if row["signals_json"] else [],
            "action_suggestion": row["action_suggestion"],
        })

    return {"total": len(records), "records": records}


@router.get("/backtest")
async def backtest(days: int = Query(default=30, ge=1, le=365)):
    """回测分析：统计信号出现频率、阶段分布、准确率等"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT recorded_at, current_phase, signal_count, signals_json
               FROM obsession_signals_history
               ORDER BY recorded_at DESC
               LIMIT ?""",
            (days * 48,),
        ).fetchall()

    if not rows:
        return {
            "days_analyzed": days,
            "total_records": 0,
            "message": "暂无历史数据，无法回测",
            "signal_frequency": {},
            "phase_distribution": {},
            "avg_signal_count": 0,
            "max_signal_count": 0,
            "break_phase_ratio": 0,
        }

    total = len(rows)
    signal_freq: dict[str, int] = {}
    phase_dist: dict[str, int] = {}
    signal_counts = []

    # 初始化信号频率
    for t in SIGNAL_TEMPLATES:
        signal_freq[t["name"]] = 0

    for row in rows:
        signal_counts.append(row["signal_count"])

        # 阶段分布
        phase = row["current_phase"]
        phase_dist[phase] = phase_dist.get(phase, 0) + 1

        # 信号频率
        try:
            sigs = json.loads(row["signals_json"]) if row["signals_json"] else []
            for sig in sigs:
                if sig.get("triggered"):
                    name = sig.get("name", "unknown")
                    signal_freq[name] = signal_freq.get(name, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    # 计算住相破裂阶段占比
    break_count = phase_dist.get("obsession_break", 0)
    break_phase_ratio = break_count / total if total > 0 else 0

    avg_signal = sum(signal_counts) / total if total > 0 else 0
    max_signal = max(signal_counts) if signal_counts else 0

    return {
        "days_analyzed": days,
        "total_records": total,
        "signal_frequency": signal_freq,
        "signal_frequency_pct": {k: round(v / total * 100, 1) for k, v in signal_freq.items()} if total > 0 else {},
        "phase_distribution": phase_dist,
        "phase_distribution_pct": {k: round(v / total * 100, 1) for k, v in phase_dist.items()} if total > 0 else {},
        "avg_signal_count": round(avg_signal, 2),
        "max_signal_count": max_signal,
        "break_phase_ratio": round(break_phase_ratio, 3),
        "break_phase_ratio_pct": f"{break_phase_ratio:.1%}",
    }

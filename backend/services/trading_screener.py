"""
筛选器 — 主升浪 / 大行情细分方向筛选
基于方法论：执念六阶段 + 板块梯队 + 连板结构
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("info-hub.screener")

# ═══════════════════════════════════════════════════════
# 一、板块热度评分
# ═══════════════════════════════════════════════════════

def score_sector(sector: Dict, main_flow_sectors: List[Dict]) -> float:
    """给板块打分：涨幅 + 资金 + 成分股强度"""
    change = float(sector.get("涨跌幅", 0) or 0)
    name = sector.get("板块名称", "")

    # 基础分：涨幅
    score = change * 10

    # 资金加成
    flow_names = [s.get("行业") or s.get("名称", "") for s in main_flow_sectors]
    if name in flow_names:
        score += 20

    # 证券/多元金融额外加分
    if "证券" in name:
        score += 30
    if "多元金融" in name or "多元" in name:
        score += 20
    if "AI" in name or "人工智能" in name:
        score += 15
    if "科技" in name:
        score += 10
    if "芯片" in name or "半导体" in name:
        score += 15

    return round(score, 1)


# ═══════════════════════════════════════════════════════
# 二、候选股评分
# ═══════════════════════════════════════════════════════

def score_candidate(stock: Dict, market_data: Dict,
                   obsession_phase: str, zt_days: int = 0) -> Dict[str, Any]:
    """
    给候选股票打分
    综合：竞价强度 + 承接力度 + 板块支撑 + 消息催化 + 方法论适配
    """
    code = stock.get("code", stock.get("代码", ""))
    name = stock.get("name", stock.get("名称", ""))
    change_pct = float(stock.get("涨跌幅") or stock.get("change_pct") or 0)
    turnover = float(stock.get("换手率") or stock.get("turnover_rate") or 0)
    amount = float(stock.get("成交额") or stock.get("amount") or 0)
    volume_ratio = float(stock.get("量比") or stock.get("volume_ratio") or 0)

    # 涨停加分
    zhangting_bonus = zt_days * 15 if change_pct >= 9.9 else 0

    # 换手率加分（活跃度）
    turnover_score = min(turnover * 3, 30)

    # 成交额加分（资金认可）
    amount_score = 0
    if amount > 5e8:
        amount_score = 20
    elif amount > 2e8:
        amount_score = 15
    elif amount > 1e8:
        amount_score = 10

    # 量比加分（动能）
    volume_score = min(volume_ratio * 5, 20) if volume_ratio > 1 else 0

    # 阶段适配分
    phase_scores = {
        "少数先知期": {"add": 0, "prefer": "量比>2"},
        "机构试错期": {"add": 20, "prefer": "换手>3%"},
        "游资点火期": {"add": 35, "prefer": "连板"},
        "散户共识期": {"add": 15, "prefer": "高位"},
        "全民住相期": {"add": -20, "prefer": "减仓"},
        "派发期": {"add": -100, "prefer": "空仓"},
    }
    ps = phase_scores.get(obsession_phase, {"add": 0})

    # 住相惩罚
    zhuxiang_count = market_data.get("signal_count", 0)
    zhuxiang_penalty = zhuxiang_count * -15

    total = (
        change_pct * 5 +
        turnover_score +
        amount_score +
        volume_score +
        zhangting_bonus +
        ps["add"] +
        zhuxiang_penalty
    )
    total = max(0, min(100, total))

    # 定档
    if total >= 75:
        tier = "A"
        level = "首选"
    elif total >= 55:
        tier = "B"
        level = "备选"
    elif total >= 35:
        tier = "C"
        level = "观察"
    else:
        tier = "D"
        level = "不参与"

    # 买入条件检查
    buy_allowed = (
        total >= 55 and
        zt_days >= 1 and
        zhuxiang_count <= 2 and
        obsession_phase in ("机构试错期", "游资点火期", "散户共识期")
    )

    reason_parts = []
    if zt_days >= 1:
        reason_parts.append(f"{zt_days}连板")
    if turnover > 5:
        reason_parts.append(f"换手{turnover:.1f}%")
    if amount > 2e8:
        reason_parts.append(f"成交{amount/1e8:.1f}亿")
    if volume_ratio > 2:
        reason_parts.append(f"量比{volume_ratio:.1f}")
    reason_parts.append(ps["prefer"])
    reason = " | ".join(reason_parts)

    return {
        "code": code,
        "name": name,
        "change_pct": round(change_pct, 2),
        "turnover_rate": round(turnover, 2),
        "amount": round(amount / 1e8, 2),  # 亿
        "lianban_days": zt_days,
        "score": round(total, 1),
        "tier": tier,
        "level": level,
        "reason": reason,
        "buy_allowed": buy_allowed,
        "obsession_phase": obsession_phase,
        "zhuxiang_count": zhuxiang_count,
    }


# ═══════════════════════════════════════════════════════
# 三、主线方向判断
# ═══════════════════════════════════════════════════════

def identify_main_line(snapshot: Dict) -> Dict[str, Any]:
    """
    识别主线方向
    返回：主线板块列表 + 细分方向 + 处于哪个执念阶段
    """
    top_industry = snapshot.get("top_industry_sectors", [])
    top_concept = snapshot.get("top_concept_sectors", [])
    top_flow = snapshot.get("top_flow_sectors", [])
    zt_codes = snapshot.get("zt_codes", [])

    # 合并板块
    all_sectors = top_industry[:10] + top_concept[:10]

    # 评分
    scored = []
    for s in all_sectors:
        score = score_sector(s, top_flow)
        scored.append({**s, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)

    # 主线 = 评分最高且涨幅 > 1.5%
    main_lines = [s for s in scored if s["score"] > 50 and float(s.get("涨跌幅", 0) or 0) > 1.5]

    # 细分方向 = 同一主线下的子板块
    if main_lines:
        top_sector_name = main_lines[0].get("板块名称", "")
        sub_sectors = [s for s in scored
                       if s.get("score", 0) > 20
                       and top_sector_name not in s.get("板块名称", "")
                       and float(s.get("涨跌幅", 0) or 0) > 0]
        sub_sectors = sub_sectors[:5]
    else:
        sub_sectors = []

    # 判断主线行情还是独立龙头
    if len(main_lines) >= 3:
        market_type = "主线行情"
    elif len(main_lines) == 1 and float(main_lines[0].get("涨跌幅", 0) or 0) > 3:
        market_type = "独立龙头"
    else:
        market_type = "震荡/无主线"

    return {
        "market_type": market_type,
        "main_lines": main_lines[:5],
        "sub_sectors": sub_sectors,
        "all_scored_sectors": scored[:15],
        "zt_count": snapshot.get("zt_count", 0),
        "breadth": snapshot.get("breadth", 0),
        "main_net_flow": snapshot.get("main_net_flow", 0),
    }


# ═══════════════════════════════════════════════════════
# 四、执行完整筛选
# ═══════════════════════════════════════════════════════

def run_screening(snapshot: Dict, signal_result: Dict,
                  watchlist: List[Dict]) -> Dict[str, Any]:
    """
    执行完整筛选流程
    1. 识别主线方向
    2. 从涨停池/关注池打捞候选
    3. 逐只评分
    4. 分类输出
    """
    obsession_phase = signal_result.get("obsession_phase", "未知")
    phase_label = signal_result.get("phase_label", "")
    zhuxiang_count = signal_result.get("signal_count", 0)
    fin_tier = signal_result.get("financial_tier", "")
    score = signal_result.get("confidence_score", 0)
    grade = signal_result.get("confidence_grade", "D")

    # 主线识别
    main_line = identify_main_line(snapshot)

    # 候选股来源：
    # 1. 涨停池（来自快照）
    # 2. 主力净流入前排
    # 3. 关注池

    candidates = []

    # 从涨停池打捞
    top_flow = snapshot.get("top_flow_stocks", [])
    for s in top_flow[:15]:
        c = score_candidate(s, signal_result, obsession_phase, zt_days=0)
        if c["score"] >= 35:
            candidates.append(c)

    # 从关注池打捞
    for wl in watchlist:
        code = wl.get("stock_code", "")
        # 这里需要 fetch_stock_detail，但会单独调用
        from services.trading_data_service import fetch_stock_detail
        detail = fetch_stock_detail(code)
        if detail:
            c = score_candidate(detail, signal_result, obsession_phase, zt_days=0)
            candidates.append(c)

    # 去重 + 排序
    seen = set()
    unique = []
    for c in candidates:
        if c["code"] not in seen:
            seen.add(c["code"])
            unique.append(c)
    candidates = unique
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 分层
    picks_A = [c for c in candidates if c["tier"] == "A"]
    picks_B = [c for c in candidates if c["tier"] == "B"]
    picks_C = [c for c in candidates if c["tier"] == "C"]

    # 可买清单（住相未破裂 + 阶段适配）
    buyable = [c for c in candidates if c["buy_allowed"]]

    # ── 主线龙头挖掘 ──────────────────────────
    # 给每个主线板块挂上 top_leaders，供"大方向里的细分板块"展示
    try:
        from services.trading_data_service import fetch_sector_top_stocks
        if main_line and main_line.get("main_lines"):
            for line in main_line["main_lines"]:
                sector_code = line.get("板块代码", "")
                if sector_code:
                    leaders = fetch_sector_top_stocks(sector_code, top_n=3)
                    line["top_leaders"] = leaders
                    line["leader_count"] = len(leaders)
                    line["zt_in_leaders"] = sum(1 for ld in leaders if ld.get("is_zt"))
    except Exception:
        pass

    return {
        "screening_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade_date": snapshot.get("trade_date", ""),
        "market_status": signal_result.get("market_status", ""),
        "obsession_phase": obsession_phase,
        "phase_label": phase_label,
        "financial_tier": fin_tier,
        "confidence_score": score,
        "confidence_grade": grade,
        "zhuxiang_count": zhuxiang_count,
        "main_line": main_line,
        "total_candidates": len(candidates),
        "picks_A": picks_A,
        "picks_B": picks_B,
        "picks_C": picks_C,
        "buyable": buyable,
        "all_candidates": candidates,
        "final_action": signal_result.get("final_action", ""),
    }


# ═══════════════════════════════════════════════════════
# 五、买点确认（竞价/开盘）
# ═══════════════════════════════════════════════════════

def confirm_buy_point(stock_code: str, snapshot: Dict,
                     signal_result: Dict) -> Dict[str, Any]:
    """确认买点时机和条件"""
    from services.trading_data_service import fetch_stock_detail
    detail = fetch_stock_detail(stock_code)
    if not detail:
        return {"code": stock_code, "confirm": False, "reason": "无法获取数据"}

    phase = signal_result.get("obsession_phase", "")
    zt_count = signal_result.get("signal_count", 0)

    price = detail.get("price", 0)
    open_price = detail.get("open", 0)
    prev_close = detail.get("prev_close", price)
    change_pct = detail.get("change_pct", 0)
    turnover = detail.get("turnover_rate", 0)
    vol_ratio = detail.get("volume_ratio", 0)

    # 竞价高开判断
    if open_price > 0 and prev_close > 0:
        gap = (open_price - prev_close) / prev_close * 100
    else:
        gap = 0

    reasons = []
    confirm = True
    tier = "B"

    # 检查1：住相未破裂
    if zt_count >= 3:
        confirm = False
        reasons.append("住相破裂，禁止买入")

    # 检查2：阶段适配
    if phase in ("全民住相期", "派发期"):
        confirm = False
        reasons.append(f"{phase}，不买入")

    # 检查3：涨幅过大（追高风险）
    if change_pct > 9:
        tier = "C"
        reasons.append("已涨停，观察次日后")

    # 检查4：竞价高开过多（诱多风险）
    if gap > 7:
        tier = "C"
        reasons.append(f"竞价高开{gap:.1f}%，谨慎")
        confirm = False

    # 检查5：换手率（活跃度）
    if turnover < 2:
        tier = "D"
        reasons.append(f"换手率仅{turnover:.1f}%，不够活跃")

    # 检查6：量比（动能）
    if vol_ratio < 1:
        reasons.append(f"量比{vol_ratio:.1f}，动能不足")

    if confirm:
        reasons.append("满足买入条件")

    return {
        "code": stock_code,
        "name": detail.get("name", ""),
        "price": price,
        "change_pct": round(change_pct, 2),
        "turnover_rate": round(turnover, 2),
        "volume_ratio": round(vol_ratio, 2),
        "gap_open_pct": round(gap, 2),
        "confirm": confirm,
        "tier": tier,
        "reasons": reasons,
        "signal": signal_result,
    }

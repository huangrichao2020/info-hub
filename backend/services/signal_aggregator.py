"""
信号聚合服务 — 把多源信号融合为交易可执行的决策信号
融合：同花顺热点 + 行业对比 + 龙虎榜 + 百度概念 + 解禁预警
"""
import logging
from datetime import datetime
from collections import Counter
from typing import Optional

logger = logging.getLogger("info-hub.signal-aggregator")

from services.signal_service import (
    ths_hot_reason,
    industry_comparison,
    daily_dragon_tiger,
    dragon_tiger_stock,
    baidu_concept_blocks,
    lockup_expiry,
)


def aggregate_market_signals(trade_date: str = None) -> dict:
    """
    聚合全市场信号，生成盘前/盘后决策参考
    
    返回结构:
    - market_theme: 当日核心题材
    - sector_rotation: 行业轮动方向
    - money_flow: 资金流向（龙虎榜）
    - risk_warnings: 风险预警（解禁/异动）
    - action_suggestion: 操作建议
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    
    result = {
        "date": trade_date,
        "generated_at": datetime.now().isoformat(),
        "market_theme": {},
        "sector_rotation": {},
        "money_flow": {},
        "risk_warnings": [],
        "action_suggestion": "",
    }
    
    # 1. 题材热度分析（同花顺热点）
    try:
        hot = ths_hot_reason(trade_date)
        if "error" not in hot:
            top_tags = hot.get("top_tags", {})
            # 识别核心主线（出现频次 >= 3 的题材）
            core_themes = {k: v for k, v in top_tags.items() if v >= 3}
            secondary_themes = {k: v for k, v in top_tags.items() if v < 3}
            
            result["market_theme"] = {
                "core": core_themes,
                "secondary": secondary_themes,
                "stock_count": hot.get("count", 0),
            }
    except Exception as e:
        logger.warning("题材分析失败: %s", e)
    
    # 2. 行业轮动方向
    try:
        ind = industry_comparison(top_n=10)
        if "error" not in ind:
            top_sectors = ind.get("top", [])
            bottom_sectors = ind.get("bottom", [])
            
            # 识别资金流入方向
            inflow_sectors = [s for s in top_sectors if s.get("change_pct", 0) > 0.5]
            outflow_sectors = [s for s in bottom_sectors if s.get("change_pct", 0) < -2]
            
            result["sector_rotation"] = {
                "inflow": [{"name": s["name"], "change": s["change_pct"], "leader": s["leader"]} 
                          for s in inflow_sectors[:5]],
                "outflow": [{"name": s["name"], "change": s["change_pct"], "leader": s["leader"]} 
                           for s in outflow_sectors[:5]],
                "total_sectors": ind.get("total", 0),
            }
    except Exception as e:
        logger.warning("行业轮动分析失败: %s", e)
    
    # 3. 资金流向（龙虎榜）
    try:
        lhb = daily_dragon_tiger(trade_date, min_net_buy=5000)
        if "error" not in lhb and lhb.get("total", 0) > 0:
            top_stocks = lhb.get("stocks", [])[:10]
            
            # 识别机构/游资偏好
            reasons = [s.get("reason", "") for s in top_stocks]
            reason_keywords = []
            for r in reasons:
                # 提取关键词
                for kw in ["涨幅", "偏离", "换手", "振幅", "涨停"]:
                    if kw in r:
                        reason_keywords.append(kw)
            
            result["money_flow"] = {
                "top_net_buy": [{"code": s["code"], "name": s["name"], 
                                "net_buy_wan": s["net_buy_wan"], "reason": s["reason"][:40]} 
                               for s in top_stocks],
                "total_records": lhb.get("total", 0),
                "dominant_reason": dict(Counter(reason_keywords).most_common(3)),
            }
    except Exception as e:
        logger.warning("龙虎榜分析失败: %s", e)
    
    # 4. 风险预警
    # 4.1 检查核心题材股是否有解禁风险
    core_themes = result["market_theme"].get("core", {})
    if core_themes:
        # 取题材高频股（简化：用热点股列表）
        try:
            hot = ths_hot_reason(trade_date)
            if "error" not in hot and hot.get("stocks"):
                for stock in hot["stocks"][:5]:  # 检查前 5 只
                    code = stock.get("code", "")
                    if code:
                        lockup = lockup_expiry(code, trade_date, forward_days=30)
                        if lockup.get("upcoming"):
                            result["risk_warnings"].append({
                                "code": code,
                                "name": stock.get("name", ""),
                                "risk": f"未来 30 天有 {len(lockup['upcoming'])} 批解禁",
                                "details": lockup["upcoming"],
                            })
        except Exception as e:
            logger.debug("解禁检查失败: %s", e)
    
    # 5. 操作建议生成
    action = _generate_action_suggestion(result)
    result["action_suggestion"] = action
    
    return result


def _generate_action_suggestion(signals: dict) -> str:
    """
    根据信号生成操作建议
    
    逻辑：
    - 核心题材集中度高（单一题材占比 > 30%）→ 主线清晰，可做
    - 行业轮动分散（TOP 3 涨幅差异 < 1%）→ 无主线，观望
    - 龙虎榜净买入集中 → 资金共识强
    - 有解禁预警 → 避开相关标的
    """
    parts = []
    
    # 题材集中度
    themes = signals.get("market_theme", {})
    core = themes.get("core", {})
    total_stocks = themes.get("stock_count", 0)
    
    if core and total_stocks > 0:
        top_theme = max(core, key=core.get)
        concentration = core[top_theme] / total_stocks * 100
        
        if concentration > 20:
            parts.append(f"🎯 主线明确：{top_theme} 占比{concentration:.0f}%，资金聚焦")
        else:
            parts.append("🔄 题材分散，无绝对主线，资金轮动快")
    
    # 行业方向
    rotation = signals.get("sector_rotation", {})
    inflow = rotation.get("inflow", [])
    outflow = rotation.get("outflow", [])
    
    if inflow:
        sector_names = [s["name"] for s in inflow[:3]]
        parts.append(f"📈 资金流入：{'+'.join(sector_names)}")
    
    if outflow:
        sector_names = [s["name"] for s in outflow[:3]]
        parts.append(f"📉 资金流出：{'+'.join(sector_names)}")
    
    # 龙虎榜强度
    money = signals.get("money_flow", {})
    if money.get("total_records", 0) > 30:
        parts.append("💰 龙虎榜活跃，游资参与度高")
    
    # 风险预警
    risks = signals.get("risk_warnings", [])
    if risks:
        risk_codes = [r["code"] for r in risks[:3]]
        parts.append(f"⚠️ 解禁预警：{'+'.join(risk_codes)} 需避开")
    
    # 综合建议
    if not parts:
        return "信号不足，建议观望"
    
    return "\n".join(parts)


def stock_signal_detail(code: str, trade_date: str = None) -> dict:
    """
    单票信号详情：概念 + 龙虎榜 + 解禁预警
    
    用于个股深度调研
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    
    result = {
        "code": code,
        "date": trade_date,
        "concept_blocks": {},
        "dragon_tiger": {},
        "lockup_warning": {},
        "signal_score": 0,
    }
    
    # 1. 概念板块
    try:
        blocks = baidu_concept_blocks(code)
        result["concept_blocks"] = blocks
    except Exception as e:
        logger.debug("概念获取失败: %s", e)
    
    # 2. 龙虎榜
    try:
        lhb = dragon_tiger_stock(code, trade_date, look_back=30)
        result["dragon_tiger"] = lhb
    except Exception as e:
        logger.debug("龙虎榜获取失败: %s", e)
    
    # 3. 解禁预警
    try:
        lockup = lockup_expiry(code, trade_date, forward_days=90)
        result["lockup_warning"] = lockup
    except Exception as e:
        logger.debug("解禁获取失败: %s", e)
    
    # 4. 信号评分（0-100）
    score = 0
    
    # 概念加分（有明确概念 +5）
    concepts = result["concept_blocks"].get("concept_tags", [])
    if len(concepts) > 0:
        score += 5
    
    # 龙虎榜加分（近期上过榜 +15）
    if result["dragon_tiger"].get("records"):
        score += 15
    
    # 解禁扣分（未来 90 天有解禁 -20）
    if result["lockup_warning"].get("upcoming"):
        score -= 20
    
    result["signal_score"] = max(0, min(100, score))
    
    return result

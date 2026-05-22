"""
信号层路由 — a-stock-data V2.1 核心能力集成
"""
from fastapi import APIRouter, Query
from typing import Optional

from services.signal_service import (
    daily_dragon_tiger,
    dragon_tiger_stock,
    industry_comparison,
    lockup_expiry,
    baidu_concept_blocks,
    ths_hot_reason,
)
from services.signal_aggregator import (
    aggregate_market_signals,
    stock_signal_detail,
)

router = APIRouter(tags=["信号层"])


@router.get("/dragon-tiger/daily")
def daily_lhb(
    trade_date: str = Query(None, description="日期 YYYY-MM-DD，默认当日"),
    min_net_buy: float = Query(None, description="净买入下限（万元）"),
):
    """全市场龙虎榜 — 当日所有上榜股票 + 净买入排名"""
    return daily_dragon_tiger(trade_date, min_net_buy)


@router.get("/dragon-tiger/stock/{code}")
def stock_lhb(
    code: str,
    trade_date: str = Query(None, description="日期 YYYY-MM-DD"),
    look_back: int = Query(30, description="回看天数"),
):
    """个股龙虎榜历史 + 上榜记录"""
    return dragon_tiger_stock(code, trade_date, look_back)


@router.get("/industry-comparison")
def industry_rank(
    top_n: int = Query(20, description="返回 TOP N"),
):
    """行业横向对比 — 同花顺 90 行业涨跌幅排名"""
    return industry_comparison(top_n)


@router.get("/lockup-expiry/{code}")
def lockup(
    code: str,
    trade_date: str = Query(None, description="日期 YYYY-MM-DD"),
    forward_days: int = Query(90, description="未来预警天数"),
):
    """限售解禁日历 — 历史 + 未来预警"""
    return lockup_expiry(code, trade_date, forward_days)


@router.get("/concept-blocks/{code}")
def concept(
    code: str,
):
    """百度概念板块归属 — 行业/概念/地域三维"""
    return baidu_concept_blocks(code)


@router.get("/ths-hot")
def hot_reason(
    date: str = Query(None, description="日期 YYYY-MM-DD，默认当日"),
):
    """同花顺热点 — 当日强势股 + 题材归因 reason tags"""
    return ths_hot_reason(date)


# ═══════════════════════════════════════════════
# 信号聚合端点 — 直接用于交易决策
# ═══════════════════════════════════════════════

@router.get("/aggregate")
def market_signals(
    trade_date: str = Query(None, description="日期 YYYY-MM-DD，默认当日"),
):
    """
    市场信号聚合 — 融合题材 + 行业 + 资金 + 风险
    
    直接返回盘前/盘后决策参考：
    - 核心题材集中度
    - 行业轮动方向
    - 龙虎榜资金流向
    - 解禁风险预警
    - 操作建议
    """
    return aggregate_market_signals(trade_date)


@router.get("/stock-detail/{code}")
def stock_detail(
    code: str,
    trade_date: str = Query(None, description="日期 YYYY-MM-DD"),
):
    """
    个股信号详情 — 概念 + 龙虎榜 + 解禁 + 信号评分
    
    用于个股深度调研，返回 0-100 信号评分
    """
    return stock_signal_detail(code, trade_date)

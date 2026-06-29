"""
交易系统 API 路由 — 市场快照 / 信号分析 / 筛选 / 回测 / 持仓
"""
import json
import logging
from datetime import datetime, date
from typing import List, Optional, Any

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
import numpy as np


def _to_native(obj: Any) -> Any:
    """递归转换 numpy/pandas 类型为 Python 原生类型，方便 JSON 序列化"""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, (np.bool_, np.bool)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(i) for i in obj]
    return obj

from database import get_db
from services.signal_engine import (
    SignalEngine, check_position_signals, BuySignalDetector
)
from services.trading_data_service import (
    fetch_full_snapshot, fetch_stock_detail, fetch_historical_kline,
    fetch_sector_top_stocks, fetch_main_line_leaders,
    get_today_str, is_trade_time
)
from services.trading_screener import run_screening, confirm_buy_point
from services.choke_point_analyzer import get_choke_analyzer, get_three_lens_analyzer
from services.trading_backtester import (
    backtest_signal, batch_backtest, evaluate_signal_quality,
    prepare_kline_data
)
from services.trading_scheduler import (
    job_pre_market, job_morning_confirm,
    job_afternoon_confirm, job_close_verification
)

logger = logging.getLogger("info-hub.trading-router")
router = APIRouter()


# ═══════════════════════════════════════════════════════
# 请求/响应模型
# ═══════════════════════════════════════════════════════

class PositionInput(BaseModel):
    stock_code: str
    stock_name: str
    position_type: str
    shares: int = 0
    avg_cost: float = 0
    current_price: float = 0
    stop_loss_price: float = 0
    notes: str = ""

    class Config:
        json_schema_extra = {"example": {
            "stock_code": "000001", "stock_name": "平安银行",
            "position_type": "MID", "shares": 1000, "avg_cost": 12.50
        }}


class BacktestRequest(BaseModel):
    stock_code: str
    signal_type: str = "ma20_break"
    stop_loss_pct: float = 7.0
    take_profit_pct: float = 15.0
    holding_days_max: int = 10


# ═══════════════════════════════════════════════════════
# 一、实时行情
# ═══════════════════════════════════════════════════════

@router.get("/snapshot")
async def get_snapshot():
    """获取完整市场快照（实时）"""
    try:
        snapshot = fetch_full_snapshot()

        # 存入数据库
        _save_snapshot(snapshot)

        return {
            "status": "ok",
            "snapshot": _to_native(snapshot),
            "trade_time": is_trade_time(),
        }
    except Exception as e:
        logger.error(f"snapshot error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 二、信号分析
# ═══════════════════════════════════════════════════════

@router.get("/signal")
async def get_signal():
    """执行完整信号分析（住相五维 + 金融三级表 + 执念阶段）"""
    try:
        snapshot = fetch_full_snapshot()
        sector_data = {
            **snapshot.get("financial_tier", {}),
            "zt_count": snapshot.get("zt_count", 0),
        }
        engine = SignalEngine(snapshot, sector_data)
        result = engine.analyze()

        # 存入数据库
        _save_signal(result, snapshot)

        return {"status": "ok", "snapshot": _to_native(snapshot), "signal": _to_native(result)}
    except Exception as e:
        logger.error(f"signal error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/time-gate")
async def get_time_gate(phase: str = Query("", description="pre_market/morning/afternoon/close")):
    """执行时间门分析"""
    try:
        snapshot = fetch_full_snapshot()
        sector_data = {
            **snapshot.get("financial_tier", {}),
            "zt_count": snapshot.get("zt_count", 0),
        }
        engine = SignalEngine(snapshot, sector_data)
        signal_result = engine.analyze()

        phase_map = {
            "pre_market": job_pre_market,
            "morning": job_morning_confirm,
            "afternoon": job_afternoon_confirm,
            "close": job_close_verification,
        }
        func = phase_map.get(phase, job_morning_confirm)
        result = func(snapshot, signal_result)

        return {"status": "ok", "time_gate": result, "signal": signal_result}
    except Exception as e:
        logger.error(f"time_gate error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 三、筛选
# ═══════════════════════════════════════════════════════

@router.get("/screen")
async def screen_stocks():
    """执行完整筛选（主线方向 + 候选股评分）"""
    try:
        # 采集数据
        snapshot = fetch_full_snapshot()
        sector_data = {
            **snapshot.get("financial_tier", {}),
            "zt_count": snapshot.get("zt_count", 0),
        }

        # 信号分析
        engine = SignalEngine(snapshot, sector_data)
        signal_result = engine.analyze()

        # 关注池
        watchlist = _get_watchlist()

        # 筛选
        result = run_screening(snapshot, signal_result, watchlist)

        # 保存结果
        _save_screening_result(result)

        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"screen error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/buy-confirm/{stock_code}")
async def confirm_buy(stock_code: str):
    """确认个股买点"""
    try:
        snapshot = fetch_full_snapshot()
        sector_data = {
            **snapshot.get("financial_tier", {}),
            "zt_count": snapshot.get("zt_count", 0),
        }
        engine = SignalEngine(snapshot, sector_data)
        signal_result = engine.analyze()

        result = confirm_buy_point(stock_code, snapshot, signal_result)
        return {"status": "ok", "buy_point": result}
    except Exception as e:
        logger.error(f"buy_confirm error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 四、持仓管理
# ═══════════════════════════════════════════════════════

@router.get("/positions")
async def list_positions():
    """查看当前持仓"""
    try:
        positions = _get_positions()
        if not positions:
            return {"status": "ok", "positions": [], "signal_check": []}

        # 逐只检查信号
        snapshot = fetch_full_snapshot()
        sector_data = {
            **snapshot.get("financial_tier", {}),
            "zt_count": snapshot.get("zt_count", 0),
        }
        engine = SignalEngine(snapshot, sector_data)
        signal_result = engine.analyze()

        # 补充实时价格
        for pos in positions:
            detail = fetch_stock_detail(pos["stock_code"])
            if detail:
                pos["current_price"] = detail.get("price", 0)
                pos["change_pct"] = detail.get("change_pct", 0)

        signal_check = check_position_signals(positions, {
            "signal_count": signal_result.get("signal_count", 0),
            **snapshot,
        })

        return {
            "status": "ok",
            "positions": positions,
            "signal_check": signal_check,
            "market_status": signal_result.get("market_status", ""),
            "obsession_phase": signal_result.get("obsession_phase", ""),
            "zhuxiang_count": signal_result.get("signal_count", 0),
        }
    except Exception as e:
        logger.error(f"positions error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/positions")
async def add_position(pos: PositionInput):
    """添加/更新持仓"""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO positions
                (stock_code, stock_name, trade_date, position_type, shares,
                 avg_cost, current_price, stop_loss_price, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pos.stock_code, pos.stock_name, get_today_str(),
                pos.position_type, pos.shares, pos.avg_cost, pos.current_price,
                pos.stop_loss_price, pos.notes,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        return {"status": "ok", "message": f"已保存 {pos.stock_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/positions/{stock_code}")
async def remove_position(stock_code: str):
    """删除持仓"""
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM positions WHERE stock_code = ?", (stock_code,))
        return {"status": "ok", "message": "已删除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 五、回测
# ═══════════════════════════════════════════════════════

@router.post("/backtest")
async def run_backtest(req: BacktestRequest):
    """执行单次回测"""
    try:
        klines = fetch_historical_kline(req.stock_code)
        if len(klines) < 60:
            return {"status": "error", "message": "K线数据不足60条"}

        result = backtest_signal(
            klines,
            signal_type=req.signal_type,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            holding_days_max=req.holding_days_max,
        )

        # 保存结果
        _save_backtest_result(req, result)

        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"backtest error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/backtest/batch")
async def run_batch_backtest(codes: List[str] = Body(...)):
    """批量回测"""
    try:
        results = batch_backtest(codes)
        quality = evaluate_signal_quality(results)
        return {"status": "ok", "results": results, "quality": quality}
    except Exception as e:
        logger.error(f"batch_backtest error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 六、关注池
# ═══════════════════════════════════════════════════════

@router.get("/watchlist")
async def list_watchlist():
    """查看关注池"""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist WHERE status='active' ORDER BY added_at DESC"
            ).fetchall()
        return {"status": "ok", "watchlist": [dict(r) for r in rows]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/watchlist")
async def add_to_watchlist(
    stock_code: str = Query(...),
    stock_name: str = Query(...),
    added_reason: str = Query(""),
    tags: str = Query(""),
):
    """加入关注池"""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO watchlist
                (stock_code, stock_name, added_reason, tags, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (stock_code, stock_name, added_reason, tags,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        return {"status": "ok", "message": f"已加入关注：{stock_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/watchlist/{stock_code}")
async def remove_from_watchlist(stock_code: str):
    """移出关注池"""
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE watchlist SET status='removed' WHERE stock_code = ?",
                (stock_code,)
            )
        return {"status": "ok", "message": "已移出关注池"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 七、个股详情
# ═══════════════════════════════════════════════════════

@router.get("/stock/{code}")
async def get_stock(code: str):
    """查询单只股票详情"""
    try:
        detail = fetch_stock_detail(code)
        if not detail:
            return {"status": "error", "message": "未找到该股票"}
        return {"status": "ok", "stock": detail}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 八、主线龙头挖掘（主升浪细分板块）
# ═══════════════════════════════════════════════════════

@router.get("/leaders")
async def get_main_line_leaders(
    top_sectors: int = Query(5, description="取几个主线板块"),
    per_sector: int = Query(3, description="每个板块取几只龙头"),
):
    """主线 → 龙头股 一站式挖掘"""
    try:
        result = fetch_main_line_leaders(top_sectors, per_sector)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"leaders error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/sector-leaders/{sector_code}")
async def get_sector_leaders(
    sector_code: str,
    top_n: int = Query(5, description="返回几只龙头"),
):
    """按板块代码单独挖龙头"""
    try:
        leaders = fetch_sector_top_stocks(sector_code, top_n)
        return {"status": "ok", "leaders": leaders}
    except Exception as e:
        logger.error(f"sector-leaders error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 八点五、个股技术评分（a-share-technical-analysis）
# ═══════════════════════════════════════════════════════

@router.get("/technical/{symbol}")
async def get_technical_analysis(
    symbol: str,
    days: int = Query(250, description="K 线天数"),
):
    """
    个股技术评分（基于 MA/RSI/MACD/布林带/量能）
    直连新浪 stock_zh_a_daily（不需代理）
    """
    try:
        from services.a_share_technical import analyze
        result = analyze(symbol)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"technical {symbol} error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/technical")
async def technical_analysis_batch(
    symbols: str = Query(..., description="逗号分隔的股票代码"),
):
    """批量技术评分（用于筛选结果附打分）"""
    try:
        from services.a_share_technical import analyze
        results = {}
        for sym in symbols.split(","):
            sym = sym.strip()
            if sym:
                results[sym] = analyze(sym)
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"technical batch error: {e}")
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════
# 八、辅助函数
# ═══════════════════════════════════════════════════════

def _save_snapshot(snapshot: Dict):
    """保存市场快照到数据库"""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO market_snapshots
                (snapshot_time, trade_date, shanghai_close, shanghai_change_pct,
                 chuangye_close, chuangye_change_pct, zt_count, dt_count,
                 limit_up_break_count, main_flow, market_status,
                 financial_tier, breadth, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.get("snapshot_time", ""),
                snapshot.get("trade_date", ""),
                snapshot.get("shanghai_close", 0),
                snapshot.get("shanghai_change_pct", 0),
                snapshot.get("chuangye_close", 0),
                snapshot.get("chuangye_change_pct", 0),
                snapshot.get("zt_count", 0),
                snapshot.get("dt_count", 0),
                snapshot.get("break_count", 0),
                json.dumps(_to_native(snapshot.get("top_flow_sectors", []))),
                snapshot.get("market_status", ""),
                snapshot.get("financial_tier", {}).get("sec", 0),
                snapshot.get("breadth", 0),
                json.dumps(_to_native(snapshot), ensure_ascii=False),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
    except Exception as e:
        logger.error(f"_save_snapshot error: {e}")


def _save_signal(signal: Dict, snapshot: Dict):
    """保存信号分析结果"""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO market_signals
                (recorded_at, trade_date, obsession_phase, phase_label,
                 signal_count, signals_json, confidence_score,
                 action_suggestion, position_limit_pct, market_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                snapshot.get("trade_date", ""),
                signal.get("obsession_phase", ""),
                signal.get("phase_label", ""),
                signal.get("signal_count", 0),
                json.dumps(signal.get("lit_signals", [])),
                signal.get("confidence_score", 0),
                signal.get("final_action", ""),
                signal.get("position_limit_pct", 100),
                signal.get("market_status", ""),
            ))
    except Exception as e:
        logger.error(f"_save_signal error: {e}")


def _save_screening_result(result: Dict):
    """保存筛选结果"""
    try:
        with get_db() as conn:
            cur = conn.execute("""
                INSERT INTO screening_runs
                (trade_date, run_time, market_status, obsession_phase,
                 candidates_json, top_sectors_json, total_candidates, final_picks,
                 status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get("trade_date", ""),
                result.get("screening_time", ""),
                result.get("market_status", ""),
                result.get("obsession_phase", ""),
                json.dumps(result.get("buyable", []), ensure_ascii=False),
                json.dumps(result.get("main_line", {}), ensure_ascii=False),
                result.get("total_candidates", 0),
                len(result.get("buyable", [])),
                "done",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            run_id = cur.lastrowid

            # 保存候选明细
            for c in result.get("all_candidates", []):
                conn.execute("""
                    INSERT INTO screening_candidates
                    (run_id, stock_code, stock_name, sector, score, tier,
                     zhangting_days, turnover_rate, main_net_inflow, reason, selection_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, c["code"], c["name"], "", c["score"],
                    c["tier"], c.get("lianban_days", 0), c.get("turnover_rate", 0),
                    c.get("amount", 0), c.get("reason", ""), c.get("level", "")
                ))
    except Exception as e:
        logger.error(f"_save_screening_result error: {e}")


def _save_backtest_result(req: BacktestRequest, result: Dict):
    """保存回测结果"""
    try:
        # 取最优一笔交易
        best_trade = max(result.get("trades", []), key=lambda x: x["pnl"], default={})
        with get_db() as conn:
            conn.execute("""
                INSERT INTO backtest_runs
                (run_time, stock_code, stock_name, start_date, end_date,
                 signal_type, entry_price, exit_price, holding_days,
                 profit_pct, max_drawdown, win_rate, signal_detail, verdict)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                req.stock_code, "", result.get("start_date", ""),
                result.get("end_date", ""), req.signal_type,
                best_trade.get("entry_price", 0),
                best_trade.get("exit_price", 0),
                best_trade.get("holding_days", 0),
                result.get("total_return_pct", 0),
                result.get("max_drawdown_pct", 0),
                result.get("win_rate_pct", 0),
                json.dumps({"stop_loss": req.stop_loss_pct,
                           "take_profit": req.take_profit_pct}),
                f"胜率{result['win_rate_pct']:.0f}% 总收益{result['total_return_pct']:.1f}%"
            ))
    except Exception as e:
        logger.error(f"_save_backtest_result error: {e}")


def _get_positions() -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM positions WHERE trade_date = ? ORDER BY created_at DESC",
            (get_today_str(),)
        ).fetchall()
        return [dict(r) for r in rows]


def _get_watchlist() -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE status='active' ORDER BY added_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════
# 九、Serenity 卡脖子 + Prism 三棱镜分析（集成自 knowhub）
# ═══════════════════════════════════════════════════════
# 集成来源：
#   - github.com/fadewalk/serenity-stock-choke
#   - github.com/destiny520537work-lab/fate-skill
# 触发方式（前端）：
#   - GET /api/trading/choke-point/{code}
#   - GET /api/trading/choke-point?codes=688146,603986  （批量）
#   - GET /api/trading/three-lens/{code}


@router.get("/choke-point/{stock_code}")
async def get_choke_point(stock_code: str):
    """Serenity 卡脖子分析（单股）"""
    try:
        result = get_choke_analyzer().analyze(stock_code)
        return result
    except Exception as e:
        logger.error(f"choke-point error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/choke-point")
async def batch_choke_point(codes: str = Query(..., description="逗号分隔的股票代码")):
    """Serenity 卡脖子分析（批量）"""
    try:
        code_list = [c.strip() for c in codes.split(",") if c.strip()]
        result = get_choke_analyzer().batch_analyze(code_list)
        return result
    except Exception as e:
        logger.error(f"choke-point batch error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/three-lens/{stock_code}")
async def get_three_lens(stock_code: str):
    """Prism 三棱镜单股分析（Seri + 道士 + Cat 三视角联合）"""
    try:
        result = get_three_lens_analyzer().analyze(stock_code)
        return result
    except Exception as e:
        logger.error(f"three-lens error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/three-lens")
async def batch_three_lens(codes: str = Query(..., description="逗号分隔的股票代码")):
    """Prism 三棱镜批量分析"""
    try:
        code_list = [c.strip() for c in codes.split(",") if c.strip()]
        analyzer = get_three_lens_analyzer()
        results = {code: analyzer.analyze(code) for code in code_list}
        return {
            "status": "ok",
            "framework": "Prism 三棱镜 v3.1.0",
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"three-lens batch error: {e}")
        return {"status": "error", "message": str(e)}

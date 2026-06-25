"""
Info-Hub 决策引擎 API 路由
提供盘前/盘中/盘后报告的触发和查询
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo

from services.decision_engine import (
    run_pre_market,
    run_intraday,
    run_post_market,
    REPORT_DIR,
    _today_str,
    _now_str,
)

logger = logging.getLogger("info-hub.decision-api")
router = APIRouter()
CN_TZ = ZoneInfo("Asia/Shanghai")


class ReportResponse(BaseModel):
    status: str
    report_type: str
    content: str
    generated_at: str


@router.get("/pre-market", response_model=ReportResponse)
async def generate_pre_market():
    """生成盘前作战报告"""
    try:
        content = await run_pre_market()
        return ReportResponse(
            status="ok",
            report_type="pre_market",
            content=content,
            generated_at=_now_str(),
        )
    except Exception as e:
        logger.exception("盘前报告生成失败")
        raise HTTPException(500, f"生成失败: {e}")


@router.get("/intraday", response_model=ReportResponse)
async def generate_intraday():
    """生成盘中快报"""
    try:
        content = await run_intraday()
        return ReportResponse(
            status="ok",
            report_type="intraday",
            content=content,
            generated_at=_now_str(),
        )
    except Exception as e:
        logger.exception("盘中快报生成失败")
        raise HTTPException(500, f"生成失败: {e}")


@router.get("/post-market", response_model=ReportResponse)
async def generate_post_market():
    """生成盘后复盘报告"""
    try:
        content = await run_post_market()
        return ReportResponse(
            status="ok",
            report_type="post_market",
            content=content,
            generated_at=_now_str(),
        )
    except Exception as e:
        logger.exception("盘后复盘生成失败")
        raise HTTPException(500, f"生成失败: {e}")


@router.get("/reports")
async def list_reports(
    report_type: str = Query(None, description="pre_market / intraday / post_market"),
    days: int = Query(7, ge=1, le=30),
):
    """查询历史报告列表"""
    import os
    reports = []
    today = _today_str()
    
    for f in sorted(REPORT_DIR.glob("*.md"), reverse=True):
        name = f.stem
        parts = name.split("_", 2)
        if len(parts) >= 3:
            date_str = parts[0]
            rtype = "_".join(parts[1:])
        elif len(parts) == 2:
            date_str = parts[0]
            rtype = parts[1]
        else:
            continue
        
        if report_type and report_type not in name:
            continue
        
        reports.append({
            "date": date_str,
            "type": rtype,
            "filename": f.name,
            "size": os.path.getsize(f),
        })
    
    return {"status": "ok", "count": len(reports), "reports": reports[:days * 3]}


@router.get("/latest")
async def latest_report(report_type: str = Query("pre_market")):
    """获取最新报告"""
    today = _today_str()
    filepath = REPORT_DIR / f"{today}_{report_type}.md"
    
    if not filepath.exists():
        # 尝试找最近的一份
        pattern = f"*_{report_type}.md"
        files = sorted(REPORT_DIR.glob(pattern), reverse=True)
        if files:
            filepath = files[0]
        else:
            raise HTTPException(404, "暂无报告")
    
    content = filepath.read_text(encoding="utf-8")
    return ReportResponse(
        status="ok",
        report_type=report_type,
        content=content,
        generated_at=datetime.fromtimestamp(filepath.stat().st_mtime, CN_TZ).strftime("%Y-%m-%d %H:%M"),
    )


@router.get("/status")
async def decision_status():
    """决策引擎状态"""
    import os
    today = _today_str()
    
    reports_today = {
        "pre_market": (REPORT_DIR / f"{today}_pre_market.md").exists(),
        "intraday": (REPORT_DIR / f"{today}_intraday.md").exists(),
        "post_market": (REPORT_DIR / f"{today}_post_market.md").exists(),
    }
    
    return {
        "status": "ok",
        "today": today,
        "reports_today": reports_today,
        "total_reports": len(list(REPORT_DIR.glob("*.md"))),
        "report_dir": str(REPORT_DIR),
    }

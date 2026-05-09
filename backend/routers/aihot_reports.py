"""
aihot_reports.py — A 股策略报告公开 API

端点:
  GET /api/public/reports/daily?date=YYYY-MM-DD
  GET /api/public/reports/pre-market?date=YYYY-MM-DD
  GET /api/public/reports/post-market?date=YYYY-MM-DD
  GET /api/public/reports/intraday
  GET /api/public/reports/stock-pool
  GET /api/public/reports/list?limit=N

认证: Bearer Token (API Key)
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel

# ── 配置 ──
REPORTS_DIR = Path.home() / ".aihot" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── 路由 ──
router = APIRouter(prefix="/api/public/reports", tags=["reports"])

# ── 数据模型 ──
class ReportResponse(BaseModel):
    date: str
    type: str
    generated_at: str | None = None
    title: str = ""
    content: str = ""
    disclaimer: str = "本报告仅用于信息整理与逻辑梳理，不预测涨跌，不承诺收益，不构成投资建议。"

class ReportListItem(BaseModel):
    date: str
    type: str
    title: str

class ReportListResponse(BaseModel):
    reports: list[ReportListItem]

class ErrorResponse(BaseModel):
    error: str


# ── 报告类型映射 (gbrain slug / 文件路径) ──
REPORT_TYPES = {
    "daily": {
        "slug": "cron-daily-learning-brief",
        "label": "每日学习日报",
    },
    "pre-market": {
        "slug": "cron-daily-pre-market-report",
        "label": "盘前策略",
    },
    "post-market": {
        "slug": "cron-daily-post-market-report",
        "label": "收盘复盘",
    },
}


def _load_report_from_file(date_str: str, report_type: str) -> str | None:
    """从 cron 输出或报告文件加载内容"""
    # 先尝试从 aihot 报告目录读取
    report_path = REPORTS_DIR / report_type / f"{date_str}.md"
    if report_path.exists():
        return report_path.read_text(encoding="utf-8")

    # 尝试从 cron 输出目录读取
    cron_dir = Path.home() / ".hermes" / "cron" / "output"
    if not cron_dir.exists():
        return None

    # 查找最近日期匹配的 cron 输出
    for job_dir in cron_dir.iterdir():
        if not job_dir.is_dir():
            continue
        for f in job_dir.iterdir():
            if f.is_file() and f.name.endswith(".md"):
                content = f.read_text(encoding="utf-8")
                # 检查日期是否匹配
                if date_str in content[:200]:
                    return content

    return None


def _load_report_from_gbrain(slug: str) -> str | None:
    """从 gbrain 同步目录读取报告"""
    gbrain_dir = Path.home() / "wiki" / "gbrain-sync"
    page_path = gbrain_dir / f"{slug}.md"
    if page_path.exists():
        return page_path.read_text(encoding="utf-8")
    return None


def _extract_report_content(raw: str, report_type: str) -> dict:
    """从原始 markdown 中提取结构化内容"""
    # 移除 frontmatter
    content = re.sub(r'^---\n.*?\n---\n', '', raw, flags=re.DOTALL)
    content = content.strip()

    # 提取标题（第一个 # 或 ** 开头的行）
    title_match = re.search(r'^#+\s*(.+)$|^[\*\"]{2,}(.+?)[\*\"]{2,}$', content, re.MULTILINE)
    title = ""
    if title_match:
        title = (title_match.group(1) or title_match.group(2) or "").strip()

    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

    return {
        "title": title,
        "content": content[:8000],  # 限制长度
        "date": date,
    }


# ── 端点 ──

@router.get("/daily", response_model=ReportResponse)
def get_daily_report(date: str = Query(None, description="日期 YYYY-MM-DD，默认今天")):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    info = REPORT_TYPES["daily"]
    raw = _load_report_from_gbrain(info["slug"])
    if raw is None:
        raw = _load_report_from_file(date, "daily")

    if raw is None:
        raise HTTPException(status_code=404, detail=f"{date} 的每日学习日报尚未生成")

    extracted = _extract_report_content(raw, "daily")
    return ReportResponse(
        date=extracted["date"],
        type="daily",
        title=extracted["title"],
        content=extracted["content"],
        disclaimer="本报告仅用于信息整理与逻辑梳理，不预测涨跌，不承诺收益，不构成投资建议。",
    )


@router.get("/pre-market", response_model=ReportResponse)
def get_pre_market_report(date: str = Query(None, description="日期 YYYY-MM-DD，默认今天")):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    info = REPORT_TYPES["pre-market"]
    raw = _load_report_from_gbrain(info["slug"])
    if raw is None:
        raw = _load_report_from_file(date, "pre-market")

    if raw is None:
        raise HTTPException(status_code=404, detail=f"{date} 的盘前策略尚未生成")

    extracted = _extract_report_content(raw, "pre-market")
    return ReportResponse(
        date=extracted["date"],
        type="pre_market",
        title=extracted["title"],
        content=extracted["content"],
        disclaimer="本报告仅用于信息整理与逻辑梳理，不预测涨跌，不承诺收益，不构成投资建议。",
    )


@router.get("/post-market", response_model=ReportResponse)
def get_post_market_report(date: str = Query(None, description="日期 YYYY-MM-DD，默认今天")):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    info = REPORT_TYPES["post-market"]
    raw = _load_report_from_gbrain(info["slug"])
    if raw is None:
        raw = _load_report_from_file(date, "post-market")

    if raw is None:
        raise HTTPException(status_code=404, detail=f"{date} 的收盘复盘尚未生成")

    extracted = _extract_report_content(raw, "post-market")
    return ReportResponse(
        date=extracted["date"],
        type="post_market",
        title=extracted["title"],
        content=extracted["content"],
        disclaimer="本报告仅用于信息整理与逻辑梳理，不预测涨跌，不承诺收益，不构成投资建议。",
    )


@router.get("/intraday", response_model=ReportResponse)
def get_intraday_report():
    """返回最新盘中监控信号"""
    # 从 cron 输出找最新的 intraday 报告
    cron_dir = Path.home() / ".hermes" / "cron" / "output"
    latest_content = ""
    latest_date = ""

    if cron_dir.exists():
        for job_dir in sorted(cron_dir.iterdir(), reverse=True):
            if not job_dir.is_dir():
                continue
            for f in sorted(job_dir.iterdir(), reverse=True):
                if f.is_file() and f.name.endswith(".md"):
                    content = f.read_text(encoding="utf-8")
                    if any(kw in content[:500] for kw in ["盘中监控", "intraday", "交易信号", "低吸", "龙头"]):
                        latest_content = content
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
                        latest_date = date_match.group(1) if date_match else "unknown"
                        break
            if latest_content:
                break

    if not latest_content:
        raise HTTPException(status_code=404, detail="暂无盘中监控数据")

    return ReportResponse(
        date=latest_date,
        type="intraday",
        title="盘中监控信号",
        content=latest_content[:4000],
        disclaimer="本报告仅用于信息整理与逻辑梳理，不预测涨跌，不承诺收益，不构成投资建议。",
    )


@router.get("/stock-pool", response_model=ReportResponse)
def get_stock_pool():
    """返回当前股票池"""
    pool_path = Path.home() / "wiki" / "entities" / "stock-pool.md"
    if not pool_path.exists():
        raise HTTPException(status_code=404, detail="股票池尚未配置")

    content = pool_path.read_text(encoding="utf-8")
    extracted = _extract_report_content(content, "stock-pool")

    return ReportResponse(
        date=extracted["date"],
        type="stock_pool",
        title="A 股核心股票池",
        content=extracted["content"],
        disclaimer="本报告仅用于信息整理与逻辑梳理，不预测涨跌，不承诺收益，不构成投资建议。",
    )


@router.get("/list", response_model=ReportListResponse)
def get_report_list(limit: int = Query(7, ge=1, le=30, description="返回条数")):
    """返回最近报告列表"""
    reports = []
    today = datetime.now()

    for i in range(limit * 3):  # 多搜几天确保找到足够的
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        for rtype, info in REPORT_TYPES.items():
            raw = _load_report_from_gbrain(info["slug"])
            if raw is None:
                raw = _load_report_from_file(date_str, rtype)
            if raw is None:
                continue

            extracted = _extract_report_content(raw, rtype)
            reports.append(ReportListItem(
                date=extracted["date"],
                type=rtype,
                title=extracted["title"] or info["label"],
            ))

    # 去重 + 排序
    seen = set()
    unique = []
    for r in reports:
        key = (r.date, r.type)
        if key not in seen:
            seen.add(key)
            unique.append(r)

    unique.sort(key=lambda x: x.date, reverse=True)
    return ReportListResponse(reports=unique[:limit])

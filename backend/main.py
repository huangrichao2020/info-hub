"""
Info-Hub FastAPI 入口
"""
import logging
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config  # noqa: F401  触发 sys.path 注入和环境变量加载
from database import init_db
from scheduler import scheduler, setup_scheduler

# ===== 日志配置 =====
LOG_DIR = Path.home() / ".info-hub" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            LOG_DIR / "info-hub.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger("info-hub")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    init_db()
    setup_scheduler()
    scheduler.start()
    logger.info("Info-Hub 启动完成 | 日志目录: %s", LOG_DIR)
    yield
    # 关闭
    scheduler.shutdown()
    logger.info("Info-Hub 已关闭")


app = FastAPI(
    title="Info-Hub API",
    description="全网资讯中枢 + 自媒体爆文 + 股票复盘",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──────────────────────────────────────────────
from routers import chan, evidence, fin_news, hot_sectors, zt_analysis, article_gen, review_report, ai_news, trending, viral_content, turn_strong, quant_market, assistant, investment_calendar  # noqa: E402

app.include_router(chan.router, prefix="/api/chan", tags=["日K缠论图"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["交易证据"])
app.include_router(fin_news.router, prefix="/api/fin-news", tags=["财经新闻"])
app.include_router(hot_sectors.router, prefix="/api/sectors", tags=["热门板块"])
app.include_router(quant_market.router, prefix="/api/amazingdata-market", tags=["AmazingData市场数据"])
app.include_router(quant_market.router, prefix="/api/quant-market", tags=["量化市场数据兼容"])
app.include_router(zt_analysis.router, prefix="/api/zt", tags=["涨停分析"])
app.include_router(turn_strong.router, prefix="/api/turn-strong", tags=["转强选股"])
app.include_router(article_gen.router, prefix="/api/article", tags=["文章生成"])
app.include_router(review_report.router, prefix="/api/review", tags=["复盘报告"])
app.include_router(ai_news.router, prefix="/api/ai-news", tags=["AI新闻"])
app.include_router(trending.router, prefix="/api/trending", tags=["热门话题"])
app.include_router(viral_content.router, prefix="/api/viral", tags=["自媒体爆款"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["复盘大师Agent"])
app.include_router(investment_calendar.router, prefix="/api/investment-calendar", tags=["投资日历"])


@app.get("/api/health")
async def health():
    """增强健康检查：数据库 + 定时任务状态"""
    from database import get_db

    checks = {"status": "ok", "service": "info-hub", "version": "2.3"}

    # 检查数据库
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        checks["status"] = "degraded"

    # 检查定时任务
    try:
        jobs = scheduler.get_jobs()
        checks["scheduler"] = {
            "running": scheduler.running,
            "job_count": len(jobs),
        }
    except Exception as exc:
        checks["scheduler"] = f"error: {exc}"
        checks["status"] = "degraded"

    # 检查日志目录
    try:
        log_file = LOG_DIR / "info-hub.log"
        checks["logging"] = {
            "log_dir": str(LOG_DIR),
            "log_exists": log_file.exists(),
        }
    except Exception as exc:
        checks["logging"] = f"error: {exc}"

    return checks


@app.get("/")
async def root():
    return {
        "service": "info-hub",
        "message": "这是 Info-Hub 后端服务，不是前端页面。",
        "frontend": "http://127.0.0.1:5174/",
        "health": "/api/health",
        "docs": "/docs",
    }

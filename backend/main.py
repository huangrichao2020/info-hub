"""
Info-Hub FastAPI 入口
"""
import logging
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

import config  # noqa: F401  触发 sys.path 注入和环境变量加载
from database import init_db, get_db
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


def init_keywords():
    """初始化关键词数据（公众号搜索专用）"""
    default_keywords = [
        # 原有关键词（用于其他模块）
        "股票", "基金", "投资", "理财", "财经", "市场", "行情", "交易",
        "A股", "港股", "美股", "期货", "期权", "债券", "宏观", "经济",
        "公司", "企业", "行业", "板块", "热点", "机会", "风险", "策略",
    ]

    # 公众号搜索专用关键词（带分类和优先级）
    wechat_keywords = [
        ("复盘", "复盘", 10),
        ("交易复盘", "复盘", 10),
        ("盘前", "盘前", 10),
        ("盘前预判", "盘前", 10),
        ("股票", "股票", 5),
        ("股市", "股票", 5),
        ("热点", "热点", 8),
        ("市场热点", "热点", 8),
        ("涨停", "股票", 7),
        ("跌停", "股票", 7),
        ("龙头股", "股票", 7),
        ("A股分析", "股票", 6),
    ]

    with get_db() as conn:
        cursor = conn.cursor()
        
        # 插入原有关键词（不分类别）
        for keyword in default_keywords:
            cursor.execute("""
                INSERT OR IGNORE INTO keywords (word) VALUES (?)
            """, (keyword,))
        
        # 插入公众号专用关键词（带分类和优先级）
        for word, category, priority in wechat_keywords:
            cursor.execute("""
                INSERT OR IGNORE INTO keywords (word, category, priority) VALUES (?, ?, ?)
            """, (word, category, priority))
        
        logger.info("关键词初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    init_db()
    init_keywords()
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


# ── 全局异常处理 ── 防止单个 API 崩溃整个进程 ──────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，返回 500 JSON 而不崩溃进程"""
    logger.exception(f"[unhandled-error] {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"服务器内部错误: {type(exc).__name__}"},
    )

# ── 注册路由 ──────────────────────────────────────────────
from routers import chan, evidence, fin_news, hot_sectors, zt_analysis, article_gen, review_report, ai_news, trending, viral_content, turn_strong, quant_market, assistant, investment_calendar, wechat, obsession_phase, stock_analysis, cross_validation  # noqa: E402


# ── 版本信息 ──────────────────────────────────────────────
import json

@app.get("/api/version")
async def get_version():
    """返回当前部署版本信息"""
    import subprocess
    import os
    
    version_info = {
        "status": "ok",
        "service": "info-hub",
    }
    
    # 尝试从 version_info.json 读取（部署时写入）
    version_file = os.path.join(os.path.dirname(__file__), "version_info.json")
    if os.path.exists(version_file):
        try:
            with open(version_file) as f:
                version_info.update(json.load(f))
        except Exception:
            pass
    
    # 尝试获取 git 信息
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            stderr=subprocess.DEVNULL
        ).decode().strip()
        version_info.setdefault("commit", commit)
        
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            stderr=subprocess.DEVNULL
        ).decode().strip()
        version_info.setdefault("version", tag)
    except Exception:
        pass
    
    version_info.setdefault("version", "dev")
    version_info.setdefault("commit", "unknown")
    
    return version_info



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
app.include_router(obsession_phase.router, prefix="/api/obsession-phase", tags=["住相信号"])
app.include_router(stock_analysis.router, prefix="/api/stock", tags=["A股分析引擎"])
app.include_router(cross_validation.router, prefix="/api/stock", tags=["交叉验证"])
app.include_router(wechat.router, prefix="", tags=["微信公众号搜索"])


@app.post("/api/deploy")
async def trigger_deploy(request: Request):
    """Webhook 部署接口：GitHub CI 推送触发
    
    安全加固（借鉴 OpenClaw fail-closed 模式）：
    - 使用 constant-time 比较防时序攻击
    - 记录所有尝试（成功/失败）
    - 失败时不泄露具体原因（统一返回 Unauthorized）
    """
    import os
    import asyncio
    import hashlib
    import hmac
    from datetime import datetime
    
    # Fail-closed: 没有 secret 时直接拒绝
    deploy_secret = os.environ.get("DEPLOY_SECRET")
    if not deploy_secret:
        logger.warning("[deploy] DEPLOY_SECRET not set, rejecting request")
        return {"status": "error", "message": "Unauthorized"}
    
    auth = request.headers.get("X-Deploy-Secret", "")
    
    # 使用 constant-time 比较防时序攻击
    if not hmac.compare_digest(auth, deploy_secret):
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(f"[deploy] Invalid secret from {client_ip} at {datetime.now().isoformat()}")
        # 不泄露具体原因，统一返回
        return {"status": "error", "message": "Unauthorized"}
    
    # 异步执行部署脚本
    async def run_deploy():
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", "/home/deploy/info-hub/deploy.sh",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/home/deploy/info-hub"
            )
            stdout, stderr = await proc.communicate()
            logger.info(f"[deploy] Exit code: {proc.returncode}")
            if stdout:
                logger.info(stdout.decode()[-1000:])
            if stderr:
                logger.error(stderr.decode()[-1000:])
        except Exception as e:
            logger.error(f"[deploy] Failed: {e}")
    
    asyncio.create_task(run_deploy())
    return {"status": "triggered", "message": "Deploy started"}

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

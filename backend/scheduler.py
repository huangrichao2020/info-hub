"""
Info-Hub 定时任务调度器
"""
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("info-hub.scheduler")

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Shanghai"))


def setup_scheduler():
    """配置所有定时任务"""
    # 财经新闻采集 - 每30分钟
    scheduler.add_job(
        _collect_fin_news,
        "interval",
        minutes=30,
        id="fin_news",
        name="财经新闻采集",
    )
    # AI新闻采集 - 每30分钟
    scheduler.add_job(
        _collect_ai_news,
        "interval",
        minutes=30,
        id="ai_news",
        name="AI新闻采集",
    )
    # 热搜更新 - 每15分钟
    scheduler.add_job(
        _collect_trending,
        "interval",
        minutes=15,
        id="trending",
        name="热搜更新",
    )
    # 转强选股 - 每个交易日 09:28 执行一次
    scheduler.add_job(
        _generate_turn_strong,
        "cron",
        day_of_week="mon-fri",
        hour=9,
        minute=28,
        id="turn_strong",
        name="转强选股生成",
    )
    # 公众号文章采集 - 每2小时
    scheduler.add_job(
        _collect_wechat_articles,
        "interval",
        hours=2,
        id="wechat_articles",
        name="公众号文章采集",
    )
    logger.info("定时任务已配置完成")


async def _collect_fin_news():
    """采集财经新闻"""
    try:
        from services.news_service import collect_financial_news
        count = await collect_financial_news()
        logger.info(f"财经新闻采集完成: {count} 条")
    except Exception as e:
        logger.error(f"财经新闻采集失败: {e}")


async def _collect_ai_news():
    """采集AI新闻"""
    try:
        from services.ai_news_service import collect_ai_news
        count = await collect_ai_news()
        logger.info(f"AI新闻采集完成: {count} 条")
    except Exception as e:
        logger.error(f"AI新闻采集失败: {e}")


async def _collect_trending():
    """采集热搜"""
    try:
        from services.trending_service import collect_trending
        count = await collect_trending()
        logger.info(f"热搜采集完成: {count} 条")
    except Exception as e:
        logger.error(f"热搜采集失败: {e}")


async def _generate_turn_strong():
    """生成转强选股"""
    try:
        from services.turn_strong_service import generate_turn_strong_run

        result = await generate_turn_strong_run(force=True)
        logger.info("转强选股生成完成: %s 条", len(result.get("items") or []))
    except Exception as e:
        logger.error(f"转强选股生成失败: {e}")


async def _collect_wechat_articles():
    """采集微信公众号文章"""
    try:
        import asyncio
        from database import get_db
        from services.wechat_crawler import run_wechat_crawler

        logger.info("开始采集微信公众号文章")
        
        # 获取数据库连接
        with get_db() as db_conn:
            result = await run_wechat_crawler(db_conn)
            
        logger.info(f"公众号文章采集完成: 爬取 {result.get('total_crawled', 0)} 篇, 保存 {result.get('total_saved', 0)} 篇")
    except Exception as e:
        logger.error(f"公众号文章采集失败: {e}")

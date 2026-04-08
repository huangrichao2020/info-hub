"""
Info-Hub 定时任务调度器
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("info-hub.scheduler")

scheduler = AsyncIOScheduler()


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

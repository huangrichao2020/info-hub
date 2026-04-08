"""自媒体爆款分析服务"""
import logging
from database import get_db

logger = logging.getLogger("info-hub.viral")


def get_viral_trending(page: int = 1, page_size: int = 30) -> list[dict]:
    """获取跨平台爆款内容（基于热搜数据的二次分析）"""
    with get_db() as conn:
        # 跨平台出现的话题更可能是爆款
        sql = """
            SELECT title, GROUP_CONCAT(DISTINCT platform) as platforms,
                   COUNT(DISTINCT platform) as cross_platform_count,
                   MAX(heat_score) as max_heat,
                   SUM(heat_score) as total_heat
            FROM trending_topics
            WHERE collected_at >= datetime('now', '-24 hours')
            GROUP BY title
            HAVING cross_platform_count >= 1
            ORDER BY total_heat DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(sql, [page_size, (page - 1) * page_size]).fetchall()
        return [dict(r) for r in rows]


def get_viral_templates() -> list[dict]:
    """获取已提取的爆款模板"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM viral_content WHERE viral_template IS NOT NULL ORDER BY collected_at DESC LIMIT 20"
        ).fetchall()
        return [dict(r) for r in rows]

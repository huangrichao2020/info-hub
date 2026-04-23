"""
微信公众号 CRUD 操作
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger("info-hub.wechat-crud")


class WechatCRUD:
    """微信公众号数据库操作"""

    @staticmethod
    def search_articles(
        db_conn,
        keyword: str = None,
        category: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        搜索文章
        :param db_conn: 数据库连接
        :param keyword: 搜索关键词
        :param category: 分类过滤
        :param page: 页码
        :param page_size: 每页数量
        :return: 搜索结果 {"total": int, "page": int, "page_size": int, "articles": list, "pages": int}
        """
        cursor = db_conn.cursor()

        # 构建查询
        where_clauses = []
        params = []

        if keyword:
            where_clauses.append("(a.title LIKE ? OR a.summary LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if category:
            where_clauses.append("json_extract(a.keywords, '$.category') = ?")
            params.append(category)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 查询总数
        count_sql = f"""
            SELECT COUNT(*) FROM articles a
            WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # 查询文章
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT 
                a.id,
                a.title,
                a.summary,
                a.url,
                a.author,
                a.publish_date,
                a.crawled_at,
                a.official_account_id,
                a.keywords,
                o.name as account_name,
                o.wechat_id as account_wechat_id
            FROM articles a
            LEFT JOIN official_accounts o ON a.official_account_id = o.id
            WHERE {where_sql}
            ORDER BY 
                CASE WHEN a.publish_date IS NOT NULL THEN a.publish_date ELSE a.crawled_at END DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        
        cursor.execute(query_sql, params)
        rows = cursor.fetchall()

        # 转换为字典
        articles = []
        for row in rows:
            try:
                keywords = json.loads(row[8]) if row[8] else {}
            except:
                keywords = {}

            articles.append({
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "url": row[3],
                "author": row[4],
                "publish_date": row[5],
                "crawled_at": row[6],
                "official_account_id": row[7],
                "keywords": keywords,
                "account_name": row[9],
                "account_wechat_id": row[10],
            })

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "articles": articles,
            "pages": pages,
        }

    @staticmethod
    def get_articles_by_account(
        db_conn,
        account_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        获取特定公众号的文章
        :param db_conn: 数据库连接
        :param account_id: 公众号ID
        :param page: 页码
        :param page_size: 每页数量
        :return: 文章列表
        """
        cursor = db_conn.cursor()

        # 总数
        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE official_account_id = ?",
            (account_id,),
        )
        total = cursor.fetchone()[0]

        # 文章
        offset = (page - 1) * page_size
        cursor.execute("""
            SELECT 
                id, title, summary, url, author, publish_date, crawled_at, keywords
            FROM articles
            WHERE official_account_id = ?
            ORDER BY 
                CASE WHEN publish_date IS NOT NULL THEN publish_date ELSE crawled_at END DESC
            LIMIT ? OFFSET ?
        """, (account_id, page_size, offset))

        rows = cursor.fetchall()
        articles = []
        for row in rows:
            try:
                keywords = json.loads(row[7]) if row[7] else {}
            except:
                keywords = {}

            articles.append({
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "url": row[3],
                "author": row[4],
                "publish_date": row[5],
                "crawled_at": row[6],
                "keywords": keywords,
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "articles": articles,
        }

    @staticmethod
    def get_trending_topics(db_conn, limit: int = 10) -> List[Dict]:
        """
        获取热门话题（从 keywords 字段中统计）
        :param db_conn: 数据库连接
        :param limit: 返回数量
        :return: 话题列表
        """
        cursor = db_conn.cursor()

        # 统计 keywords JSON 中的 tags
        cursor.execute("""
            SELECT 
                json_extract(keywords, '$.tags[0]') as topic,
                COUNT(*) as count
            FROM articles
            WHERE keywords IS NOT NULL
            GROUP BY topic
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        return [{"topic": row[0], "count": row[1]} for row in rows if row[0]]

    @staticmethod
    def get_recommended_accounts(db_conn, limit: int = 10) -> List[Dict]:
        """
        获取推荐公众号（按文章数和最近更新排序）
        :param db_conn: 数据库连接
        :param limit: 返回数量
        :return: 公众号列表
        """
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT 
                id, name, wechat_id, description, avatar_url, article_count, status, updated_at
            FROM official_accounts
            WHERE status = 'active' AND article_count > 0
            ORDER BY article_count DESC, updated_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        accounts = []
        for row in rows:
            accounts.append({
                "id": row[0],
                "name": row[1],
                "wechat_id": row[2],
                "description": row[3],
                "avatar_url": row[4],
                "article_count": row[5],
                "status": row[6],
                "updated_at": row[7],
            })

        return accounts

    @staticmethod
    def get_account_by_id(db_conn, account_id: int) -> Optional[Dict]:
        """
        根据ID获取公众号信息
        :param db_conn: 数据库连接
        :param account_id: 公众号ID
        :return: 公众号信息
        """
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, name, wechat_id, description, avatar_url, article_count, status, updated_at FROM official_accounts WHERE id = ?",
            (account_id,),
        )
        row = cursor.fetchone()

        if row:
            return {
                "id": row[0],
                "name": row[1],
                "wechat_id": row[2],
                "description": row[3],
                "avatar_url": row[4],
                "article_count": row[5],
                "status": row[6],
                "updated_at": row[7],
            }
        return None

    @staticmethod
    def cleanup_old_articles(db_conn, days: int = 30) -> int:
        """
        清理超过指定天数的文章
        :param db_conn: 数据库连接
        :param days: 天数
        :return: 删除数量
        """
        cursor = db_conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute(
            "DELETE FROM articles WHERE crawled_at < ?",
            (cutoff_date,),
        )
        deleted = cursor.rowcount
        db_conn.commit()

        logger.info(f"清理了 {deleted} 篇超过 {days} 天的文章")
        return deleted

    @staticmethod
    def get_categories(db_conn) -> List[str]:
        """
        获取所有文章分类
        :param db_conn: 数据库连接
        :return: 分类列表
        """
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT DISTINCT json_extract(keywords, '$.category') as category
            FROM articles
            WHERE keywords IS NOT NULL
            AND json_extract(keywords, '$.category') IS NOT NULL
            ORDER BY category
        """)

        return [row[0] for row in cursor.fetchall() if row[0]]

    @staticmethod
    def get_statistics(db_conn) -> Dict:
        """
        获取统计信息
        :param db_conn: 数据库连接
        :return: 统计信息
        """
        cursor = db_conn.cursor()

        # 文章总数
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]

        # 公众号总数
        cursor.execute("SELECT COUNT(*) FROM official_accounts WHERE status = 'active'")
        total_accounts = cursor.fetchone()[0]

        # 最近7天新增文章
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute(
            "SELECT COUNT(*) FROM articles WHERE crawled_at > ?",
            (week_ago,),
        )
        recent_articles = cursor.fetchone()[0]

        # 分类统计
        cursor.execute("""
            SELECT 
                json_extract(keywords, '$.category') as category,
                COUNT(*) as count
            FROM articles
            WHERE keywords IS NOT NULL
            GROUP BY category
        """)
        category_stats = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

        return {
            "total_articles": total_articles,
            "total_accounts": total_accounts,
            "recent_articles_7d": recent_articles,
            "category_stats": category_stats,
        }

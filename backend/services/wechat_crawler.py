"""
微信公众号搜索爬虫
使用 Jina Reader API 搜索微信公众号文章
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote

import httpx

logger = logging.getLogger("info-hub.wechat-crawler")


class WechatCrawler:
    """微信公众号搜索爬虫（基于 Jina Reader）"""

    # Jina Reader API 配置
    JINA_READER_URL = "https://r.jina.ai/"
    JINA_HEADERS = {
        "Accept": "application/json",
        "X-Return-Format": "text",
        "X-No-Cache": "true",
    }

    # 搜索平台配置
    SEARCH_PLATFORMS = {
        "sogou": {
            "name": "搜狗微信",
            "search_url": "https://weixin.sogou.com/weixin?type=2&query={query}",
            "result_selector": "parse_sogou_results",
        },
        "xueqiu": {
            "name": "雪球",
            "search_url": "https://xueqiu.com/k?q={query}",
            "result_selector": "parse_xueqiu_results",
        },
    }

    def __init__(self, db_conn=None):
        """
        初始化爬虫
        :param db_conn: SQLite 数据库连接
        """
        self.db = db_conn
        self.client = httpx.AsyncClient(
            timeout=6.0,
            headers=self.JINA_HEADERS,
            follow_redirects=True,
            trust_env=False,
        )
        self.direct_client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"},
        )

    async def search_wechat_articles(
        self,
        keyword: str,
        platforms: List[str] = None,
        max_results_per_platform: int = 10,
    ) -> List[Dict]:
        """
        搜索微信公众号文章
        :param keyword: 搜索关键词
        :param platforms: 搜索平台列表，默认使用所有平台
        :param max_results_per_platform: 每个平台最大结果数
        :return: 文章列表
        """
        if platforms is None:
            platforms = list(self.SEARCH_PLATFORMS.keys())

        all_results = []
        tasks = []

        for platform in platforms:
            if platform in self.SEARCH_PLATFORMS:
                task = self._search_single_platform(
                    platform, keyword, max_results_per_platform
                )
                tasks.append(task)

        # 并发搜索所有平台
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"搜索平台失败: {result}")
                elif isinstance(result, list):
                    all_results.extend(result)

        # 去重（基于 URL）
        seen_urls = set()
        unique_results = []
        for article in all_results:
            if article.get("url") not in seen_urls:
                seen_urls.add(article.get("url"))
                unique_results.append(article)

        logger.info(
            f"关键词 '{keyword}' 搜索完成，共 {len(unique_results)} 篇唯一文章"
        )
        return unique_results

    async def _search_single_platform(
        self, platform: str, keyword: str, max_results: int
    ) -> List[Dict]:
        """搜索单个平台"""
        platform_config = self.SEARCH_PLATFORMS[platform]
        search_url = platform_config["search_url"].format(query=quote(keyword))

        try:
            logger.info(f"正在搜索 {platform_config['name']}: {keyword}")
            parser_method = getattr(self, platform_config["result_selector"], None)
            if not parser_method:
                logger.warning(f"未找到平台 {platform} 的解析方法")
                return []

            text_content = ""
            try:
                response = await self.client.get(self.JINA_READER_URL + search_url)
                response.raise_for_status()
                text_content = response.json().get("content", "")
                articles = parser_method(text_content, keyword, max_results)
                if articles:
                    return articles
            except Exception as jina_error:
                logger.warning(f"Jina 搜索 {platform_config['name']} 失败，尝试直连: {jina_error!r}")

            response = await self.direct_client.get(search_url)
            response.raise_for_status()
            return parser_method(response.text, keyword, max_results)

        except Exception as e:
            logger.error(f"搜索 {platform_config['name']} 失败: {e!r}")
            return []

    def parse_sogou_results(
        self, text: str, keyword: str, max_results: int
    ) -> List[Dict]:
        """
        解析搜狗微信搜索结果
        注意：由于 Jina Reader 返回纯文本，需要启发式解析
        """
        articles = []
        if "news-list" in text or "sogou_vr_11002601_title" in text:
            import html
            import re
            blocks = re.findall(r'<li[^>]+id="sogou_vr_11002601_box_\d+".*?</li>', text, flags=re.S)
            for block in blocks[:max_results]:
                title_match = re.search(r'<a[^>]+href="([^"]+)"[^>]+uigs="article_title_\d+"[^>]*>(.*?)</a>', block, flags=re.S)
                if not title_match:
                    continue
                href, title_html = title_match.groups()
                title = re.sub(r'<!--.*?-->|<.*?>', '', title_html, flags=re.S)
                title = html.unescape(title).strip()
                summary_match = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', block, flags=re.S)
                summary = ""
                if summary_match:
                    summary = re.sub(r'<!--.*?-->|<.*?>', '', summary_match.group(1), flags=re.S)
                    summary = html.unescape(summary).strip()
                author_match = re.search(r'<span class="all-time-y2">(.*?)</span>', block, flags=re.S)
                author = html.unescape(re.sub(r'<.*?>', '', author_match.group(1))).strip() if author_match else "搜狗微信"
                if href.startswith("/"):
                    href = "https://weixin.sogou.com" + href.replace("&amp;", "&")
                articles.append({
                    "title": title,
                    "summary": summary,
                    "url": href,
                    "source": author or "搜狗微信",
                    "publish_time": None,
                    "keywords": {"tags": [keyword]},
                })
            return articles[:max_results]

        lines = text.strip().split("\n")

        current_article = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 启发式：如果行包含 http 且看起来像微信文章 URL
            if "mp.weixin.qq.com" in line or "weixin.sogou.com" in line:
                if current_article.get("title"):
                    articles.append(current_article)
                    if len(articles) >= max_results:
                        break
                    current_article = {}
                current_article["url"] = line
            elif line and not current_article.get("title") and len(line) > 10:
                # 假设第一个长行是标题
                current_article["title"] = line
            elif line and not current_article.get("summary") and len(line) > 20:
                current_article["summary"] = line[:500]

        # 添加最后一篇
        if current_article.get("title") and len(articles) < max_results:
            articles.append(current_article)

        # 补充默认字段
        for article in articles:
            article.setdefault("title", "未知标题")
            article.setdefault("summary", "")
            article.setdefault("source", "搜狗微信")
            article.setdefault("publish_time", None)
            article.setdefault("keywords", {"tags": [keyword]})

        return articles[:max_results]

    def parse_xueqiu_results(
        self, text: str, keyword: str, max_results: int
    ) -> List[Dict]:
        """解析雪球搜索结果"""
        articles = []
        lines = text.strip().split("\n")

        current_article = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 雪球文章通常有 xueqiu.com/xxx/数字 格式
            if "xueqiu.com" in line and ("/" in line or "http" in line):
                if current_article.get("title"):
                    articles.append(current_article)
                    if len(articles) >= max_results:
                        break
                    current_article = {}
                current_article["url"] = line if "http" in line else f"https://{line}"
            elif line and not current_article.get("title") and len(line) > 10:
                current_article["title"] = line
            elif line and not current_article.get("summary") and len(line) > 20:
                current_article["summary"] = line[:500]

        if current_article.get("title") and len(articles) < max_results:
            articles.append(current_article)

        for article in articles:
            article.setdefault("title", "未知标题")
            article.setdefault("summary", "")
            article.setdefault("source", "雪球")
            article.setdefault("publish_time", None)
            article.setdefault("keywords", {"tags": [keyword]})

        return articles[:max_results]

    async def crawl_by_keywords(self, keywords: List[Dict]) -> Dict:
        """
        根据关键词列表批量爬取文章
        :param keywords: 关键词列表，每个关键词是 {"word": str, "category": str, "priority": int}
        :return: 统计信息 {"total_crawled": int, "total_saved": int}
        """
        # 按优先级排序
        sorted_keywords = sorted(keywords, key=lambda x: x.get("priority", 0), reverse=True)

        total_crawled = 0
        total_saved = 0

        for kw in sorted_keywords:
            word = kw["word"]
            category = kw.get("category", "其他")

            logger.info(f"开始爬取关键词: {word} (分类: {category}, 优先级: {kw.get('priority', 0)})")

            try:
                articles = await self.search_wechat_articles(
                    keyword=word,
                    max_results_per_platform=5,
                )

                total_crawled += len(articles)

                # 保存到数据库
                if self.db and articles:
                    saved = self.save_articles(articles, word, category)
                    total_saved += saved

                # 礼貌延迟
                await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"爬取关键词 {word} 失败: {e}")
                continue

        return {"total_crawled": total_crawled, "total_saved": total_saved}

    def save_articles(
        self, articles: List[Dict], keyword: str, category: str
    ) -> int:
        """
        保存文章到数据库
        :param articles: 文章列表
        :param keyword: 搜索关键词
        :param category: 分类
        :return: 保存数量
        """
        if not self.db:
            logger.warning("数据库连接为空，跳过保存")
            return 0

        saved_count = 0
        cursor = self.db.cursor()

        for article_data in articles:
            try:
                title = article_data.get("title", "")
                url = article_data.get("url", "")
                summary = article_data.get("summary", "")
                source = article_data.get("source", "")
                publish_time_str = article_data.get("publish_time", "")

                if not title or not url:
                    continue

                # 检查文章是否已存在
                cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
                if cursor.fetchone():
                    logger.debug(f"文章已存在: {title}")
                    continue

                # 获取或创建公众号
                cursor.execute(
                    "SELECT id, article_count FROM official_accounts WHERE name = ?",
                    (source,),
                )
                account_row = cursor.fetchone()

                if account_row:
                    account_id = account_row[0]
                    article_count = account_row[1] or 0
                    cursor.execute(
                        "UPDATE official_accounts SET article_count = ?, updated_at = ? WHERE id = ?",
                        (article_count + 1, datetime.now().isoformat(), account_id),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO official_accounts (name, wechat_id, article_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (
                            source,
                            source,
                            1,
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                        ),
                    )
                    account_id = cursor.lastrowid

                # 解析发布时间
                publish_time = self._parse_publish_time(publish_time_str)

                # 插入文章
                keywords_json = article_data.get(
                    "keywords", {"category": category, "tags": [keyword]}
                )

                cursor.execute(
                    "INSERT INTO articles (title, summary, url, author, publish_date, crawled_at, official_account_id, keywords) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        title,
                        summary,
                        url,
                        source,
                        publish_time.isoformat() if publish_time else None,
                        datetime.now().isoformat(),
                        account_id,
                        str(keywords_json),
                    ),
                )

                saved_count += 1
                logger.debug(f"保存文章: {title}")

            except Exception as e:
                logger.error(f"保存文章失败: {e}")
                continue

        self.db.commit()
        return saved_count

    def _parse_publish_time(self, time_str: str) -> Optional[datetime]:
        """解析发布时间字符串"""
        from datetime import timedelta
        
        if not time_str:
            return None

        try:
            # 尝试 ISO 格式
            if "T" in time_str:
                return datetime.fromisoformat(time_str)

            # 尝试 YYYY-MM-DD 格式
            if "-" in time_str and len(time_str) == 10:
                return datetime.strptime(time_str, "%Y-%m-%d")

            # 尝试相对时间
            if "分钟前" in time_str:
                minutes = int("".join(filter(str.isdigit, time_str)))
                return datetime.now() - timedelta(minutes=minutes)

            if "小时前" in time_str:
                hours = int("".join(filter(str.isdigit, time_str)))
                return datetime.now() - timedelta(hours=hours)

            if "天前" in time_str:
                days = int("".join(filter(str.isdigit, time_str)))
                return datetime.now() - timedelta(days=days)

            return None

        except Exception:
            return None

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
        await self.direct_client.aclose()


async def run_wechat_crawler(db_conn) -> Dict:
    """
    爬虫执行函数（用于 APScheduler 或手动调用）
    :param db_conn: SQLite 数据库连接
    :return: 统计信息
    """
    cursor = db_conn.cursor()

    # 获取所有关键词（按优先级排序）
    cursor.execute(
        "SELECT word, category, priority FROM keywords WHERE category != '其他' ORDER BY priority DESC"
    )
    keywords = [
        {"word": row[0], "category": row[1], "priority": row[2]} for row in cursor.fetchall()
    ]

    if not keywords:
        logger.warning("没有找到关键词，跳过爬取")
        return {"total_crawled": 0, "total_saved": 0}

    crawler = WechatCrawler(db_conn)
    try:
        result = await crawler.crawl_by_keywords(keywords)
        return result
    finally:
        await crawler.close()

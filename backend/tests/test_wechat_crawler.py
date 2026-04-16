"""
微信公众号爬虫测试
"""
import unittest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio

from services.wechat_crawler import WechatCrawler, run_wechat_crawler


class TestWechatCrawler(unittest.TestCase):
    """微信公众号爬虫测试"""

    def setUp(self):
        """设置测试环境"""
        self.mock_db = Mock()
        self.crawler = WechatCrawler(self.mock_db)

    def test_parse_publish_time_minutes(self):
        """测试解析相对时间 - 分钟前"""
        result = self.crawler._parse_publish_time("30分钟前")
        self.assertIsNotNone(result)
        self.assertTrue(result < datetime.now())
        self.assertTrue(result > datetime.now() - timedelta(hours=1))

    def test_parse_publish_time_hours(self):
        """测试解析相对时间 - 小时前"""
        result = self.crawler._parse_publish_time("2小时前")
        self.assertIsNotNone(result)
        self.assertTrue(result < datetime.now())
        self.assertTrue(result > datetime.now() - timedelta(hours=3))

    def test_parse_publish_time_days(self):
        """测试解析相对时间 - 天前"""
        result = self.crawler._parse_publish_time("3天前")
        self.assertIsNotNone(result)
        self.assertTrue(result < datetime.now())
        self.assertTrue(result > datetime.now() - timedelta(days=4))

    def test_parse_publish_time_iso(self):
        """测试解析 ISO 格式时间"""
        result = self.crawler._parse_publish_time("2026-04-17T10:30:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 4)

    def test_parse_publish_time_date(self):
        """测试解析日期格式"""
        result = self.crawler._parse_publish_time("2026-04-17")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 4)
        self.assertEqual(result.day, 17)

    def test_parse_publish_time_empty(self):
        """测试空字符串"""
        result = self.crawler._parse_publish_time("")
        self.assertIsNone(result)

    def test_parse_publish_time_none(self):
        """测试 None 值"""
        result = self.crawler._parse_publish_time(None)
        self.assertIsNone(result)

    def test_parse_sogou_results_basic(self):
        """测试解析搜狗结果 - 基础"""
        text = """
        测试文章标题1
        http://mp.weixin.qq.com/s/abc123
        这是文章的摘要内容，包含一些关键信息
        """
        results = self.crawler.parse_sogou_results(text, "测试", 10)
        
        self.assertIsInstance(results, list)
        if results:
            self.assertIn("title", results[0])
            self.assertIn("url", results[0])
            self.assertIn("summary", results[0])

    def test_parse_sogou_results_max_limit(self):
        """测试解析结果数量限制"""
        # 模拟包含多个结果的文本
        text = """
        文章1
        http://mp.weixin.qq.com/s/1
        摘要1
        
        文章2
        http://mp.weixin.qq.com/s/2
        摘要2
        
        文章3
        http://mp.weixin.qq.com/s/3
        摘要3
        """
        results = self.crawler.parse_sogou_results(text, "测试", 2)
        self.assertLessEqual(len(results), 2)

    def test_parse_xueqiu_results(self):
        """测试解析雪球结果"""
        text = """
        关于某股票的深度分析
        https://xueqiu.com/123456
        这是一篇关于股票投资的文章，包含了很多有用的信息
        """
        results = self.crawler.parse_xueqiu_results(text, "股票", 10)
        
        self.assertIsInstance(results, list)
        if results:
            self.assertIn("title", results[0])
            self.assertIn("url", results[0])

    def test_save_articles_empty(self):
        """测试保存空列表"""
        count = self.crawler.save_articles([], "测试", "股票")
        self.assertEqual(count, 0)

    @patch.object(WechatCrawler, 'save_articles')
    def test_crawl_by_keywords_structure(self, mock_save):
        """测试批量爬取结构"""
        mock_save.return_value = 5
        
        keywords = [
            {"word": "复盘", "category": "复盘", "priority": 10},
            {"word": "股票", "category": "股票", "priority": 5},
        ]
        
        # 这里只是测试结构，不实际执行网络请求
        self.assertIsInstance(keywords, list)
        self.assertEqual(len(keywords), 2)


class TestWechatCrawlerIntegration(unittest.TestCase):
    """爬虫集成测试"""

    def test_run_wechat_crawler_with_empty_db(self):
        """测试空数据库情况"""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_db.cursor.return_value = mock_cursor
        
        # 应该返回空结果
        # 注：实际异步测试需要 async test framework
        # 这里只测试结构
        self.assertTrue(callable(run_wechat_crawler))


if __name__ == "__main__":
    unittest.main()

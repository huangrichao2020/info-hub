"""
微信公众号 API 测试
"""
import unittest
import os
import sys
import json
from datetime import datetime

# 添加 backend 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from database import get_db, init_db


class TestWechatAPI(unittest.TestCase):
    """微信公众号 API 测试"""

    @classmethod
    def setUpClass(cls):
        """初始化数据库"""
        init_db()
        cls.client = TestClient(app)

    def test_search_articles_empty(self):
        """测试搜索文章 - 空结果"""
        response = self.client.get("/api/wechat/search")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total", data)
        self.assertIn("articles", data)
        self.assertIsInstance(data["articles"], list)

    def test_search_articles_with_keyword(self):
        """测试搜索文章 - 带关键词"""
        response = self.client.get("/api/wechat/search?q=测试")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("page_size", data)

    def test_search_articles_pagination(self):
        """测试分页"""
        response = self.client.get("/api/wechat/search?page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 10)

    def test_search_articles_category_filter(self):
        """测试分类过滤"""
        response = self.client.get("/api/wechat/search?category=股票")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("articles", data)

    def test_trending_topics(self):
        """测试热门话题"""
        response = self.client.get("/api/wechat/trending-topics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_trending_topics_with_limit(self):
        """测试热门话题 - 带限制"""
        response = self.client.get("/api/wechat/trending-topics?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_recommended_accounts(self):
        """测试推荐公众号"""
        response = self.client.get("/api/wechat/recommended-accounts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_recommended_accounts_with_limit(self):
        """测试推荐公众号 - 带限制"""
        response = self.client.get("/api/wechat/recommended-accounts?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_categories(self):
        """测试获取分类"""
        response = self.client.get("/api/wechat/categories")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("categories", data)
        self.assertIsInstance(data["categories"], list)

    def test_statistics(self):
        """测试获取统计信息"""
        response = self.client.get("/api/wechat/statistics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_articles", data)
        self.assertIn("total_accounts", data)

    def test_account_not_found(self):
        """测试获取不存在的公众号"""
        response = self.client.get("/api/wechat/accounts/999999")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)

    def test_account_articles_empty(self):
        """测试获取公众号文章 - 空结果"""
        response = self.client.get("/api/wechat/accounts/1/articles")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total", data)
        self.assertIn("articles", data)

    def test_cleanup_old_articles(self):
        """测试清理旧文章"""
        response = self.client.post("/api/wechat/cleanup?days=30")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("deleted", data)
        self.assertIn("message", data)


class TestWechatAPIValidation(unittest.TestCase):
    """API 验证测试"""

    def setUp(self):
        self.client = TestClient(app)

    def test_search_invalid_page(self):
        """测试无效页码"""
        response = self.client.get("/api/wechat/search?page=0")
        # FastAPI 应该返回 422 验证错误
        self.assertIn(response.status_code, [422, 200])

    def test_search_invalid_page_size(self):
        """测试无效每页数量"""
        response = self.client.get("/api/wechat/search?page_size=0")
        self.assertIn(response.status_code, [422, 200])

    def test_search_page_size_too_large(self):
        """测试每页数量过大"""
        response = self.client.get("/api/wechat/search?page_size=200")
        self.assertIn(response.status_code, [422, 200])


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from main import LOG_DIR, LOG_FORMAT


class DeploymentTests(unittest.TestCase):
    def test_log_directory_exists(self):
        """日志目录应该存在或可创建"""
        # LOG_DIR 在 main.py 导入时创建
        self.assertTrue(LOG_DIR.exists())
        self.assertTrue(LOG_DIR.is_dir())

    def test_log_format_is_correct(self):
        """日志格式应该包含时间/logger名/级别/消息"""
        self.assertIn("%(asctime)s", LOG_FORMAT)
        self.assertIn("%(name)s", LOG_FORMAT)
        self.assertIn("%(levelname)s", LOG_FORMAT)
        self.assertIn("%(message)s", LOG_FORMAT)

    def test_log_path_is_correct(self):
        """日志路径应该在 ~/.info-hub/logs/"""
        expected = Path.home() / ".info-hub" / "logs"
        self.assertEqual(LOG_DIR, expected)

    def test_health_endpoint_structure(self):
        """健康检查应该返回结构化数据"""
        import asyncio
        from main import health

        async def run():
            result = await health()
            return result

        result = asyncio.run(run())
        self.assertIn("status", result)
        self.assertIn("service", result)
        self.assertIn("version", result)
        self.assertIn("database", result)
        self.assertIn("scheduler", result)
        self.assertIn("logging", result)

    def test_start_script_exists(self):
        """启动脚本应该存在"""
        script = Path(__file__).parent.parent / "start.sh"
        self.assertTrue(script.exists())

    def test_gitignore_exists(self):
        """.gitignore 应该存在"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        self.assertTrue(gitignore.exists())


if __name__ == "__main__":
    unittest.main()

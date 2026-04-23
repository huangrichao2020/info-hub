import unittest
from unittest.mock import AsyncMock, patch

from services.turn_strong_service import build_turn_strong_validation


class TurnStrongValidationTests(unittest.TestCase):
    def test_build_turn_strong_validation_aggregates_next_day_bars(self):
        run_payload = {
            "trade_date": "2026-04-10",
            "items": [
                {"code": "600000", "name": "浦发银行", "screen": {"latest_price": 10.0}},
                {"code": "300502", "name": "新易盛", "screen": {"latest_price": 20.0}},
            ],
        }

        async def fake_get_kline(code: str, period: str, begin_date: int, end_date: int):
            if code == "600000.SH":
                return {
                    "items": [
                        {"timestamp": "2026-04-10", "open": 10.0, "high": 10.1, "close": 10.0},
                        {"timestamp": "2026-04-13", "open": 10.3, "high": 10.8, "close": 10.6},
                    ]
                }
            return {
                "items": [
                    {"timestamp": "2026-04-10", "open": 20.0, "high": 20.4, "close": 20.1},
                    {"timestamp": "2026-04-13", "open": 19.5, "high": 19.8, "close": 19.2},
                ]
            }

        with patch("services.turn_strong_service.get_turn_strong_run", return_value=run_payload), patch(
            "services.turn_strong_service.get_kline",
            new=AsyncMock(side_effect=fake_get_kline),
        ):
            import asyncio

            result = asyncio.run(build_turn_strong_validation("2026-04-10"))

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["summary"]["count"], 2)
        self.assertEqual(result["summary"]["success_count"], 1)
        self.assertEqual(result["summary"]["fail_count"], 1)
        self.assertEqual(result["items"][0]["next_trade_date"], "2026-04-13")
        self.assertEqual(result["items"][0]["verdict"], "success")
        self.assertEqual(result["items"][1]["verdict"], "fail")

    def test_validation_includes_enhanced_statistics(self):
        """验证应包含增强的统计字段"""
        run_payload = {
            "trade_date": "2026-04-10",
            "items": [
                {"code": "600000", "name": "浦发银行", "screen": {"latest_price": 10.0, "industry": "银行", "style_concept": "金融"}},
                {"code": "300502", "name": "新易盛", "screen": {"latest_price": 20.0, "industry": "通信", "style_concept": "科技"}},
                {"code": "000001", "name": "平安银行", "screen": {"latest_price": 15.0, "industry": "银行", "style_concept": "金融"}},
            ],
        }

        async def fake_get_kline(code: str, period: str, begin_date: int, end_date: int):
            if code == "600000.SH":
                return {"items": [{"timestamp": "2026-04-13", "open": 10.3, "high": 10.8, "close": 10.6}]}
            elif code == "300502.SZ":
                return {"items": [{"timestamp": "2026-04-13", "open": 19.5, "high": 19.8, "close": 19.2}]}
            elif code == "000001.SZ":
                return {"items": [{"timestamp": "2026-04-13", "open": 15.1, "high": 15.2, "close": 15.05}]}
            return {"items": []}

        with patch("services.turn_strong_service.get_turn_strong_run", return_value=run_payload), patch(
            "services.turn_strong_service.get_kline",
            new=AsyncMock(side_effect=fake_get_kline),
        ):
            import asyncio

            result = asyncio.run(build_turn_strong_validation("2026-04-10"))

        summary = result["summary"]

        # 验证新增统计字段
        self.assertIn("total_verifiable", summary)
        self.assertIn("success_rate_pct", summary)
        self.assertIn("weak_count", summary)
        self.assertIn("flat_count", summary)
        self.assertIn("insufficient_count", summary)
        self.assertIn("verdict_distribution", summary)
        self.assertIn("failure_analysis", summary)

        # 验证成功率计算
        self.assertGreater(summary["success_rate_pct"], 0)
        self.assertGreaterEqual(summary["total_verifiable"], 2)  # 至少 2 只有 K 线数据

        # 验证 verdict 分布
        dist = summary["verdict_distribution"]
        self.assertIn("success", dist)
        self.assertIn("fail", dist)
        self.assertIn("weak", dist)
        self.assertIn("flat", dist)
        self.assertIn("insufficient", dist)

        # 验证失败归因
        analysis = summary["failure_analysis"]
        self.assertIn("count", analysis)
        self.assertIn("patterns", analysis)
        self.assertIn("summary", analysis)
        self.assertGreater(analysis["count"], 0)

    def test_validation_handles_empty_run(self):
        """空 run 应该返回 empty 状态"""
        # 清除缓存 + mock 所有数据源返回空
        with patch("services.turn_strong_service._cache_get", return_value=None), \
             patch("services.turn_strong_service.get_turn_strong_run", return_value=None):
            import asyncio
            result = asyncio.run(build_turn_strong_validation("2099-01-01"))  # 用未来日期确保无数据

        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["items"], [])


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import AsyncMock, patch

from services.quant_market_service import (
    KLINE_PERIOD_ALIAS,
    get_multi_period_klines,
    normalize_kline_period,
    transform_kline_response,
)


class QuantMarketServiceTests(unittest.TestCase):
    def test_normalize_kline_period(self):
        self.assertEqual(normalize_kline_period("minute"), "min1")
        self.assertEqual(normalize_kline_period("15min"), "min15")
        self.assertEqual(normalize_kline_period("hour"), "min60")
        self.assertEqual(normalize_kline_period("day"), "day")

    def test_period_alias_map_has_expected_entries(self):
        self.assertEqual(KLINE_PERIOD_ALIAS["1m"], "min1")
        self.assertEqual(KLINE_PERIOD_ALIAS["15m"], "min15")
        self.assertEqual(KLINE_PERIOD_ALIAS["1h"], "min60")
        self.assertEqual(KLINE_PERIOD_ALIAS["d1"], "day")
        # 新增周期
        self.assertEqual(KLINE_PERIOD_ALIAS["5m"], "min5")
        self.assertEqual(KLINE_PERIOD_ALIAS["30m"], "min30")

    def test_transform_kline_response(self):
        raw = {
            "code": "600376.SH",
            "period": "min15",
            "requested_period": "15min",
            "begin_date": 20260410,
            "end_date": 20260410,
            "count": 2,
            "items": [
                {
                    "code": "600376.SH",
                    "kline_time": "2026-04-10 09:30:00",
                    "open": 4.81,
                    "high": 4.84,
                    "low": 4.80,
                    "close": 4.83,
                    "volume": 1842958,
                    "amount": 8879138,
                },
                {
                    "code": "600376.SH",
                    "kline_time": "2026-04-10 09:45:00",
                    "open": 4.83,
                    "high": 4.85,
                    "low": 4.81,
                    "close": 4.82,
                    "volume": 925000,
                    "amount": 4432100,
                },
            ],
        }

        result = transform_kline_response(raw)

        self.assertEqual(result["code"], "600376.SH")
        self.assertEqual(result["period"], "min15")
        self.assertEqual(result["requested_period"], "15min")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["items"][0]["timestamp"], "2026-04-10 09:30:00")
        self.assertEqual(result["items"][0]["close"], 4.83)

    def test_multi_period_kline_returns_four_series(self):
        """多周期K线应返回 minute/fifteen_minute/hour/day 四个系列"""
        import asyncio

        mock_eastmoney = AsyncMock(return_value=[{
            "code": "600376.SH",
            "timestamp": "2026-04-14T09:31:00",
            "open": 4.81, "high": 4.84, "low": 4.80, "close": 4.83,
            "volume": 1842958, "amount": 8879138,
        }])
        mock_iwencai = AsyncMock(return_value={
            "code": "600376.SH",
            "period": "day",
            "begin_date": 20251012,
            "end_date": 20260410,
            "count": 1,
            "items": [{
                "code": "600376.SH",
                "timestamp": "2026-04-10T00:00:00",
                "open": 4.81, "high": 4.85, "low": 4.80, "close": 4.83,
                "volume": 1842958, "amount": 8879138,
            }],
        })

        with patch("services.quant_market_service._fetch_eastmoney_kline", mock_eastmoney), \
             patch("services.quant_market_service.get_kline", mock_iwencai):
            result = asyncio.run(get_multi_period_klines("600376.SH", 20260410))

        self.assertEqual(result["code"], "600376.SH")
        self.assertEqual(result["trade_date"], 20260410)
        # 验证四个周期都存在
        self.assertIn("minute", result["series"])
        self.assertIn("fifteen_minute", result["series"])
        self.assertIn("hour", result["series"])
        self.assertIn("day", result["series"])
        # 验证分钟级数据有内容
        self.assertGreater(result["series"]["minute"]["count"], 0)


if __name__ == "__main__":
    unittest.main()

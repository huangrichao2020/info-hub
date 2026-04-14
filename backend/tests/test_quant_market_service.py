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

    def test_multi_period_kline_uses_lookback_windows(self):
        payload = {"code": "600376.SH", "period": "min1", "requested_period": "minute", "begin_date": 0, "end_date": 0, "count": 0, "items": []}
        with patch("services.quant_market_service.get_kline", new=AsyncMock(return_value=payload)) as mock_get_kline:
            import asyncio

            result = asyncio.run(get_multi_period_klines("600376.SH", 20260410))

        self.assertEqual(result["code"], "600376.SH")
        self.assertEqual(result["trade_date"], 20260410)
        calls = mock_get_kline.await_args_list
        self.assertEqual(calls[0].kwargs["period"], "min1")
        self.assertEqual(calls[0].kwargs["begin_date"], 20260410)
        self.assertEqual(calls[1].kwargs["period"], "min15")
        self.assertEqual(calls[1].kwargs["begin_date"], 20260403)
        self.assertEqual(calls[2].kwargs["period"], "min60")
        self.assertEqual(calls[2].kwargs["begin_date"], 20260311)
        self.assertEqual(calls[3].kwargs["period"], "day")
        self.assertEqual(calls[3].kwargs["begin_date"], 20251012)


if __name__ == "__main__":
    unittest.main()

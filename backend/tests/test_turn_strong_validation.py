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


if __name__ == "__main__":
    unittest.main()

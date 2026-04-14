import unittest
from unittest.mock import patch

from services.turn_strong_service import list_recent_turn_strong_runs


class TurnStrongHistoryTests(unittest.TestCase):
    def test_list_recent_turn_strong_runs_returns_descending_rows(self):
        fake_rows = [
            {
                "trade_date": "2026-04-13",
                "generated_at": "2026-04-13T01:28:00Z",
                "refreshed_at": "2026-04-13T02:00:00Z",
                "status": "ready",
                "selection_total": 8,
            },
            {
                "trade_date": "2026-04-12",
                "generated_at": "2026-04-12T01:28:00Z",
                "refreshed_at": "2026-04-12T02:00:00Z",
                "status": "ready",
                "selection_total": 5,
            },
        ]

        class FakeConn:
            def execute(self, *_args, **_kwargs):
                return self

            def fetchall(self):
                return fake_rows

        class FakeCtx:
            def __enter__(self):
                return FakeConn()

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("services.turn_strong_service.get_db", return_value=FakeCtx()):
            result = list_recent_turn_strong_runs(limit=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["trade_date"], "2026-04-13")
        self.assertEqual(result[1]["selection_total"], 5)


if __name__ == "__main__":
    unittest.main()

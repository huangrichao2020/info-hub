import unittest

from services.chan_service import _secid_from_code, build_strokes, detect_pivots


class ChanServiceTests(unittest.TestCase):
    def test_secid_from_code_maps_sh_and_sz(self):
        self.assertEqual(_secid_from_code("600519.SH"), "1.600519")
        self.assertEqual(_secid_from_code("000001.SZ"), "0.000001")
        self.assertEqual(_secid_from_code("000001.SH"), "1.000001")

    def test_detect_pivots_and_strokes_on_simple_wave(self):
        bars = [
            {"date": "2026-04-01", "high": 10, "low": 8},
            {"date": "2026-04-02", "high": 12, "low": 9},
            {"date": "2026-04-03", "high": 15, "low": 10},
            {"date": "2026-04-04", "high": 11, "low": 7},
            {"date": "2026-04-05", "high": 14, "low": 9},
            {"date": "2026-04-06", "high": 9, "low": 6},
            {"date": "2026-04-07", "high": 13, "low": 8},
        ]
        for index, bar in enumerate(bars):
            bar["index"] = index
            bar["open"] = bar["low"]
            bar["close"] = bar["high"]
            bar["volume"] = 1

        pivots = detect_pivots(bars, window=1)
        strokes = build_strokes(pivots)

        self.assertGreaterEqual(len(pivots), 2)
        self.assertGreaterEqual(len(strokes), 1)
        self.assertIn(strokes[0]["direction"], {"up", "down"})


if __name__ == "__main__":
    unittest.main()

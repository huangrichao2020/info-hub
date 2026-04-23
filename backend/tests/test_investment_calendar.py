import unittest
from datetime import datetime

from data.investment_calendar import (
    INVESTMENT_CALENDAR_STATIC,
    get_events,
    get_event_types,
)


class InvestmentCalendarTests(unittest.TestCase):
    def test_static_calendar_has_events(self):
        """静态事件库应该有事件"""
        self.assertGreater(len(INVESTMENT_CALENDAR_STATIC), 0)

    def test_get_events_default_range(self):
        """默认范围（今天起+90天）应该返回事件"""
        events = get_events()
        self.assertIsInstance(events, list)
        # 事件应该有正确的结构
        if events:
            evt = events[0]
            self.assertIn("date", evt)
            self.assertIn("title", evt)
            self.assertIn("type", evt)
            self.assertIn("level", evt)
            self.assertIn("source", evt)
            self.assertEqual(evt["source"], "static")

    def test_get_events_filters_by_level(self):
        """按级别过滤应该只返回匹配的事件"""
        major_events = get_events(level="major")
        for evt in major_events:
            self.assertEqual(evt["level"], "major")

    def test_get_events_filters_by_type(self):
        """按类型过滤应该只返回匹配的事件"""
        policy_events = get_events(event_type="policy")
        for evt in policy_events:
            self.assertEqual(evt["type"], "policy")

    def test_get_events_date_range_filter(self):
        """日期范围过滤应该正确"""
        start = "2026-04-01"
        end = "2026-04-30"
        events = get_events(start_date=start, end_date=end)
        for evt in events:
            self.assertGreaterEqual(evt["date"], start)
            self.assertLessEqual(evt["date"], end)

    def test_get_events_sorted_by_date(self):
        """返回的事件应该按日期排序"""
        events = get_events()
        dates = [evt["date"] for evt in events]
        self.assertEqual(dates, sorted(dates))

    def test_get_event_types_returns_all_types(self):
        """事件类型应该包含所有5种类型"""
        types = get_event_types()
        self.assertEqual(len(types), 5)
        type_values = [t["value"] for t in types]
        self.assertIn("meeting", type_values)
        self.assertIn("policy", type_values)
        self.assertIn("economic_data", type_values)
        self.assertIn("earnings", type_values)
        self.assertIn("market", type_values)

    def test_event_structure_integrity(self):
        """所有事件应该有完整的结构"""
        required_fields = {"date", "title", "type", "level", "description", "benefit_sectors", "leading_stocks"}
        valid_types = {"meeting", "policy", "economic_data", "earnings", "market"}
        valid_levels = {"major", "moderate", "minor"}

        for evt in INVESTMENT_CALENDAR_STATIC:
            for field in required_fields:
                self.assertIn(field, evt, f"Event missing field: {field}")
            self.assertIn(evt["type"], valid_types, f"Invalid type: {evt['type']}")
            self.assertIn(evt["level"], valid_levels, f"Invalid level: {evt['level']}")
            self.assertIsInstance(evt["benefit_sectors"], list)
            self.assertIsInstance(evt["leading_stocks"], list)


if __name__ == "__main__":
    unittest.main()

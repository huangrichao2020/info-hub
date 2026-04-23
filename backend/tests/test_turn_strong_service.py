import unittest
from unittest.mock import AsyncMock, patch

from services.turn_strong_service import (
    _generate_llm_analysis,
    build_turn_strong_screen_query,
    build_turn_strong_screen_queries,
    build_iwencai_turn_strong_queries,
    choose_next_mx_key,
    extract_dates_from_screen_columns,
    extract_json_payload,
    _is_excluded_candidate,
    _merge_candidate_sources,
    _normalize_iwencai_candidates,
    normalize_turn_strong_candidates,
    _clean_concept_field,
)


class TurnStrongServiceTests(unittest.TestCase):
    def test_build_query_contains_core_filters_and_fields(self):
        query = build_turn_strong_screen_query()
        self.assertIn("主板股票", query)
        self.assertIn("前一交易日筹码获利比例小于60", query)
        self.assertNotIn("今日竞价量比大于1.3", query)
        self.assertIn("今日高开超过0.5%", query)
        self.assertIn("今日筹码获利比例大于60", query)
        self.assertIn("返回所属概念", query)
        self.assertIn("按今日竞价量比从高到低排序", query)

    def test_build_queries_has_fallback_ladder(self):
        queries = build_turn_strong_screen_queries()

        self.assertEqual(len(queries), 3)
        self.assertIn("前一交易日筹码获利比例小于60", queries[0])
        self.assertIn("今日筹码获利比例大于60", queries[0])
        self.assertIn("前一交易日筹码获利比例小于65", queries[1])
        self.assertIn("今日筹码获利比例大于55", queries[1])
        self.assertIn("前一交易日筹码获利比例小于70", queries[2])
        self.assertNotIn("今日筹码获利比例大于", queries[2])

    def test_build_iwencai_queries_use_simpler_validation(self):
        queries = build_iwencai_turn_strong_queries()

        self.assertEqual(len(queries), 2)
        self.assertIn("非ST", queries[0])
        self.assertIn("今日高开大于0", queries[0])
        self.assertNotIn("前一交易日筹码获利比例", queries[0])

    def test_extract_dates_from_screen_columns(self):
        columns = [
            {"key": "010000_HLP<70>{2026-04-08}"},
            {"key": "010000_HLP<70>{2026-04-09}"},
            {"key": "010000_AUC_VOLUME_RATIO{2026-04-09}"},
        ]

        dates = extract_dates_from_screen_columns(columns)

        self.assertEqual(dates["previous_trade_date"], "2026-04-08")
        self.assertEqual(dates["trade_date"], "2026-04-09")

    def test_normalize_turn_strong_candidates_maps_screen_fields(self):
        screen_payload = {
            "conditions": [{"describe": "上市板块包含主板", "stockCount": 3196}],
            "columns": [
                {"key": "010000_HLP<70>{2026-04-08}"},
                {"key": "010000_HLP<70>{2026-04-09}"},
                {"key": "010000_AUC_VOLUME_RATIO{2026-04-09}"},
                {"key": "010000_AUC_RANGE{2026-04-09}"},
                {"key": "010000_LIANGBI<70>{2026-04-09}"},
                {"key": "010000_TURNOVER_RATE<70>{2026-04-09}"},
                {"key": "010000_TRADING_VOLUMES<70>{2026-04-09}"},
                {"key": "010000_TOAL_MARKET_VALUE<70>{2026-04-09}"},
                {"key": "010000_CIRCULATION_MARKET_VALUE<70>{2026-04-09}"},
            ],
            "rows": [
                {
                    "SERIAL": "1",
                    "SECURITY_CODE": "600000",
                    "SECURITY_SHORT_NAME": "浦发银行",
                    "MARKET_SHORT_NAME": "SH",
                    "010000_CUSTOM_TRADEMARKET_TRADEMARKET_{2026-04-09}#LATEST#": "上交所主板",
                    "INDUSTRY": "银行",
                    "STYLE_CONCEPT": "中字头、国企改革",
                    "010000_HLP<70>{2026-04-08}": "58.12",
                    "010000_HLP<70>{2026-04-09}": "61.34",
                    "010000_AUC_VOLUME_RATIO{2026-04-09}": "2.18",
                    "010000_AUC_RANGE{2026-04-09}": "0.86",
                    "NEWEST_PRICE": "12.45",
                    "CHG": "3.28",
                    "010000_LIANGBI<70>{2026-04-09}": "1.67",
                    "010000_TURNOVER_RATE<70>{2026-04-09}": "2.35",
                    "010000_TRADING_VOLUMES<70>{2026-04-09}": "8.21亿",
                    "010000_TOAL_MARKET_VALUE<70>{2026-04-09}": "3521.45亿",
                    "010000_CIRCULATION_MARKET_VALUE<70>{2026-04-09}": "3521.45亿",
                }
            ],
        }

        result = normalize_turn_strong_candidates(screen_payload)

        self.assertEqual(result["trade_date"], "2026-04-09")
        self.assertEqual(result["previous_trade_date"], "2026-04-08")
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["code"], "600000")
        self.assertEqual(item["name"], "浦发银行")
        self.assertEqual(item["screen"]["board"], "上交所主板")
        self.assertAlmostEqual(item["screen"]["previous_profit_ratio"], 58.12)
        self.assertAlmostEqual(item["screen"]["current_profit_ratio"], 61.34)
        self.assertAlmostEqual(item["screen"]["auction_volume_ratio"], 2.18)
        self.assertAlmostEqual(item["screen"]["auction_change_pct"], 0.86)
        self.assertEqual(item["screen"]["trading_amount"], "8.21亿")

    def test_choose_next_mx_key_prefers_lowest_usage(self):
        keys = [
            {"name": "EM_API_KEY", "value": "a"},
            {"name": "EM_API_KEY_BACKUP", "value": "b"},
            {"name": "EM_API_KEY_3", "value": "c"},
        ]
        usage = {
            "EM_API_KEY": {"request_count": 20, "quota_exhausted": 1},
            "EM_API_KEY_BACKUP": {"request_count": 5, "quota_exhausted": 0},
            "EM_API_KEY_3": {"request_count": 2, "quota_exhausted": 0},
        }

        chosen = choose_next_mx_key(keys, usage)

        self.assertEqual(chosen["name"], "EM_API_KEY_3")

    def test_normalize_iwencai_candidates_maps_basic_fields(self):
        payload = {
            "datas": [
                {
                    "股票代码": "300502",
                    "股票简称": "新易盛",
                    "所属行业": "通信",
                    "所属概念": "CPO、算力",
                    "最新价": "105.80",
                    "竞价涨跌幅": "1.25",
                    "竞价量比": "2.31",
                    "前一交易日筹码获利比例": "58.5",
                    "今日筹码获利比例": "62.8",
                }
            ]
        }

        items = _normalize_iwencai_candidates(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["code"], "300502")
        self.assertEqual(items[0]["name"], "新易盛")
        self.assertEqual(items[0]["source_tags"], ["问财A股"])
        self.assertAlmostEqual(items[0]["screen"]["auction_volume_ratio"], 2.31)

    def test_merge_candidate_sources_deduplicates_by_code(self):
        merged = _merge_candidate_sources(
            [
                {
                    "rank": 1,
                    "code": "300502",
                    "name": "新易盛",
                    "screen": {"auction_volume_ratio": 1.8, "auction_change_pct": 0.9},
                    "source_tags": ["妙想"],
                }
            ],
            [
                {
                    "rank": 1,
                    "code": "300502",
                    "name": "新易盛",
                    "screen": {"auction_volume_ratio": 2.2, "industry": "通信"},
                    "source_tags": ["问财A股"],
                }
            ],
        )

        self.assertEqual(len(merged), 1)
        self.assertIn("妙想", merged[0]["source_tags"])
        self.assertIn("问财A股", merged[0]["source_tags"])
        self.assertEqual(merged[0]["screen"]["industry"], "通信")

    def test_is_excluded_candidate_filters_st_names(self):
        self.assertTrue(_is_excluded_candidate({"name": "*ST兰黄", "screen": {"board": "上交所主板"}}))
        self.assertTrue(_is_excluded_candidate({"name": "普通股票", "screen": {"board": "风险警示板"}}))
        self.assertFalse(_is_excluded_candidate({"name": "启明星辰", "screen": {"board": "上交所主板"}}))

    def test_extract_json_payload_handles_code_fence(self):
        raw = """分析如下:

```json
{"market_summary":"修复","analyses":[{"code":"600000","recommendation":"watch"}]}
```
"""

        payload = extract_json_payload(raw)

        self.assertEqual(payload["market_summary"], "修复")
        self.assertEqual(payload["analyses"][0]["code"], "600000")

    def test_generate_llm_analysis_falls_back_when_chat_fails(self):
        items = [
            {
                "code": "600000",
                "name": "浦发银行",
                "screen": {
                    "auction_volume_ratio": 2.18,
                    "auction_change_pct": 0.86,
                    "previous_profit_ratio": 58.12,
                    "current_profit_ratio": 61.34,
                },
                "news_items": [],
            }
        ]

        with patch("services.turn_strong_service.chat", new=AsyncMock(side_effect=TimeoutError("llm timeout"))):
            import asyncio

            payload = asyncio.run(_generate_llm_analysis(items, {"indices": [], "top_risers": [], "top_fallers": []}))

        self.assertIn("market_summary", payload)
        self.assertEqual(len(payload["analyses"]), 1)
        self.assertIn("raw_text", payload)

    # ===== 概念字段清洗测试 =====

    def test_clean_concept_field_removes_brackets(self):
        """应该去除 ['xxx'] 格式"""
        self.assertEqual(_clean_concept_field("['物业管理']"), "物业管理")
        self.assertEqual(_clean_concept_field("['统一大市场']"), "统一大市场")
        self.assertEqual(_clean_concept_field("['航空发动机']"), "航空发动机")

    def test_clean_concept_field_handles_multiple(self):
        """应该处理多个概念"""
        self.assertEqual(_clean_concept_field("['物业管理', '航空装备']"), "物业管理、航空装备")

    def test_clean_concept_field_handles_double_quotes(self):
        """应该处理双引号格式"""
        self.assertEqual(_clean_concept_field('["物业管理"]'), "物业管理")

    def test_clean_concept_field_passes_through_plain_text(self):
        """纯文本应该直接返回"""
        self.assertEqual(_clean_concept_field("物业管理"), "物业管理")
        self.assertEqual(_clean_concept_field("航空发动机"), "航空发动机")

    def test_clean_concept_field_handles_empty(self):
        """空值应该返回空字符串"""
        self.assertEqual(_clean_concept_field(None), "")
        self.assertEqual(_clean_concept_field(""), "")
        self.assertEqual(_clean_concept_field("  "), "")


if __name__ == "__main__":
    unittest.main()

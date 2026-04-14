import unittest

from llm.prompts import review_messages, turn_strong_messages
from llm.uwillberich import STEP_SKILL_MAP, build_review_system_prompt, build_turn_strong_system_prompt


class UwIllBeRichPromptTests(unittest.TestCase):
    def test_review_system_prompt_enforces_methodology_first(self):
        prompt = build_review_system_prompt()

        self.assertIn("先定方法论，再调工具", prompt)
        self.assertIn("市场分类", prompt)
        self.assertIn("基准 / 乐观 / 风险", prompt)
        self.assertIn("行情数据查询", prompt)
        self.assertIn("问财选板块", prompt)

    def test_turn_strong_system_prompt_enforces_json_and_market_state(self):
        prompt = build_turn_strong_system_prompt()

        self.assertIn("区间/防御市场", prompt)
        self.assertIn("recommendation", prompt)
        self.assertIn("buy`、`watch`、`avoid", prompt)
        self.assertIn("竞价强度、板块共振、消息支撑", prompt)

    def test_step_skill_map_covers_internal_structure(self):
        self.assertIn("内部结构层", STEP_SKILL_MAP)
        self.assertIn("行情数据查询", STEP_SKILL_MAP["内部结构层"])
        self.assertIn("问财选A股", STEP_SKILL_MAP["内部结构层"])

    def test_review_messages_use_uwillberich_prompt(self):
        messages = review_messages(
            portfolio_data=[{"name": "新易盛", "code": "300502", "shares": 100, "cost_price": 89.2}],
            market_context="指数走弱，科技修复尝试中。",
            date="2026-04-13",
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("uwillberich", messages[0]["content"])
        self.assertIn("市场分类", messages[0]["content"])
        self.assertIn("持仓明细", messages[1]["content"])

    def test_turn_strong_messages_use_uwillberich_prompt(self):
        messages = turn_strong_messages(
            candidates=[{"code": "300502", "name": "新易盛", "auction_volume_ratio": 2.3}],
            market_snapshot={"indices": [], "top_risers": [], "top_fallers": []},
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("转强分析不能跳过市场分类", messages[0]["content"])
        self.assertIn("严格返回 JSON", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()

import unittest

from services.assistant_prompt import (
    SAFETY_CONSTRAINTS,
    build_assistant_system_prompt,
)
from services.react_agent import SYSTEM_PROMPT_PREFIX


class SafetyConstraintTests(unittest.TestCase):
    def test_safety_constraints_exists(self):
        """安全约束字符串应该存在"""
        self.assertIn("安全约束", SAFETY_CONSTRAINTS)
        self.assertIn("话题边界", SAFETY_CONSTRAINTS)
        self.assertIn("禁止透露的信息", SAFETY_CONSTRAINTS)

    def test_safety_includes_device_protection(self):
        """应该包含设备信息保护"""
        self.assertIn("设备", SAFETY_CONSTRAINTS)
        self.assertIn("服务器", SAFETY_CONSTRAINTS)
        self.assertIn("操作系统", SAFETY_CONSTRAINTS)

    def test_safety_includes_key_protection(self):
        """应该包含 Key 保护"""
        self.assertIn("API Key", SAFETY_CONSTRAINTS)
        self.assertIn("环境变量", SAFETY_CONSTRAINTS)

    def test_safety_in_topic_boundary(self):
        """应该包含话题边界"""
        self.assertIn("A 股交易", SAFETY_CONSTRAINTS)
        self.assertIn("拒绝", SAFETY_CONSTRAINTS)

    def test_safety_injected_into_assistant_prompt(self):
        """安全约束应该注入到复盘大师提示词中"""
        prompt = build_assistant_system_prompt()
        self.assertIn("安全约束", prompt)
        self.assertIn("话题边界", prompt)
        # 安全约束应该在最前面
        safety_pos = prompt.index("安全约束")
        discipline_pos = prompt.index("复盘大师")
        self.assertLess(safety_pos, discipline_pos)

    def test_safety_injected_into_react_agent(self):
        """安全约束应该注入到 ReAct Agent 提示词中"""
        self.assertIn("安全约束", SYSTEM_PROMPT_PREFIX)
        self.assertIn("设备", SYSTEM_PROMPT_PREFIX)
        self.assertIn("API Key", SYSTEM_PROMPT_PREFIX)

    def test_safety_covers_all_attack_vectors(self):
        """安全约束应该覆盖所有攻击向量"""
        combined = SAFETY_CONSTRAINTS + SYSTEM_PROMPT_PREFIX
        attack_vectors = [
            "设备", "服务器", "操作系统", "API Key",
            "环境变量", "数据库路径", "代码实现", "技术架构",
        ]
        for vector in attack_vectors:
            self.assertIn(vector, combined, f"Missing protection for: {vector}")


if __name__ == "__main__":
    unittest.main()

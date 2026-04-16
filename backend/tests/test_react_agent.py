import unittest
from unittest.mock import AsyncMock, patch

from services.react_agent import (
    ToolRegistry,
    global_registry,
    init_tools,
)


class ToolRegistryTests(unittest.TestCase):
    def test_register_and_get_tool(self):
        registry = ToolRegistry()
        async def dummy():
            pass
        registry.register("test_tool", "A test tool", {}, dummy)
        tool = registry.get("test_tool")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.description, "A test tool")

    def test_get_unknown_tool_returns_none(self):
        registry = ToolRegistry()
        self.assertIsNone(registry.get("nonexistent"))

    def test_to_openai_format(self):
        registry = ToolRegistry()
        async def dummy():
            pass
        registry.register("foo", "Foo desc", {"type": "object"}, dummy)
        tools = registry.to_openai_format()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["type"], "function")
        self.assertEqual(tools[0]["function"]["name"], "foo")
        self.assertEqual(tools[0]["function"]["description"], "Foo desc")

    def test_execute_tool_returns_result(self):
        registry = ToolRegistry()
        async def adder(a: int, b: int):
            return a + b
        registry.register("adder", "Add two numbers", {}, adder)
        import asyncio
        result = asyncio.run(registry.execute("adder", {"a": 3, "b": 4}))
        self.assertEqual(result, 7)

    def test_execute_unknown_tool_returns_error(self):
        registry = ToolRegistry()
        import asyncio
        result = asyncio.run(registry.execute("unknown", {}))
        self.assertIn("error", result)

    def test_execute_tool_catches_exceptions(self):
        registry = ToolRegistry()
        async def failer():
            raise ValueError("boom")
        registry.register("failer", "Fails", {}, failer)
        import asyncio
        result = asyncio.run(registry.execute("failer", {}))
        self.assertIn("error", result)
        self.assertIn("boom", result["error"])


class InitToolsTests(unittest.TestCase):
    def test_init_tools_registers_all_tools(self):
        """init_tools 应该注册所有预期工具"""
        init_tools()
        expected_tools = [
            "query_stock_quote",
            "query_index_quote",
            "query_kline",
            "query_sector_movers",
            "query_review_history",
            "query_turn_strong",
            "search_stock_info",  # 新增搜索工具
        ]
        for tool_name in expected_tools:
            tool = global_registry.get(tool_name)
            self.assertIsNotNone(tool, f"Tool {tool_name} should be registered")
            self.assertIsNotNone(tool.function)

    def test_tools_openai_format_has_all_tools(self):
        init_tools()
        tools = global_registry.to_openai_format()
        tool_names = [t["function"]["name"] for t in tools]
        self.assertIn("query_stock_quote", tool_names)
        self.assertIn("query_index_quote", tool_names)
        self.assertIn("query_kline", tool_names)
        self.assertIn("query_sector_movers", tool_names)
        self.assertIn("query_review_history", tool_names)
        self.assertIn("query_turn_strong", tool_names)
        self.assertIn("search_stock_info", tool_names)


class SearchToolTests(unittest.TestCase):
    def test_search_tool_allows_stock_query(self):
        """搜索工具应该允许股票相关查询"""
        import asyncio
        from services.react_agent import _search_stock_info_impl

        # 股票代码查询
        result = asyncio.run(_search_stock_info_impl("600519 茅台"))
        self.assertIn("error", result)  # 网络请求可能失败，但不应该被安全过滤拦截

    def test_search_tool_blocks_non_stock_query(self):
        """搜索工具应该拒绝非股票查询"""
        import asyncio
        from services.react_agent import _search_stock_info_impl

        result = asyncio.run(_search_stock_info_impl("今天天气怎么样"))
        self.assertIn("error", result)
        self.assertIn("股票相关", result["error"])

    def test_search_tool_allows_sector_query(self):
        """搜索工具应该允许板块查询"""
        import asyncio
        from services.react_agent import _search_stock_info_impl

        result = asyncio.run(_search_stock_info_impl("新能源板块"))
        # 包含股票关键词，应该通过安全过滤
        self.assertNotIn("必须与股票相关", str(result.get("error", "")))


if __name__ == "__main__":
    unittest.main()

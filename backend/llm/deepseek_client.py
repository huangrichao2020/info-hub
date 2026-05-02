"""
DeepSeek API 客户端
用于 info-hub 复盘大师 AI 管家
"""
import json
import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger("info-hub.deepseek")

DEEPSEEK_API_KEY = "sk-7a6728c668b04b5fb2e09954c4fb2cd6"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"

CHAT_URL = f"{DEEPSEEK_BASE_URL}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json",
}


async def chat_stream(
    messages: list[dict],
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """流式调用 DeepSeek，逐块 yield 文本内容"""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", CHAT_URL, headers=HEADERS, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def chat(
    messages: list[dict],
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """同步调用 DeepSeek，返回完整响应文本"""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(CHAT_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def chat_stream_with_tools(
    messages: list[dict],
    tools: list[dict],
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """流式调用 DeepSeek with Function Calling
    如果有 tool_calls，返回工具调用信息；否则流式接收内容。
    返回: {"content": str, "tool_calls": list}
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "tools": tools,
        "tool_choice": "auto",
        "stream": True,
    }

    accumulated_content = []
    tool_calls = []

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", CHAT_URL, headers=HEADERS, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})

                    # 检查是否有 tool_calls
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            tool_calls.append(tc)

                    content = delta.get("content", "")
                    if content:
                        accumulated_content.append(content)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    content_str = "".join(accumulated_content)
    return {
        "content": content_str,
        "tool_calls": tool_calls if tool_calls else None,
    }

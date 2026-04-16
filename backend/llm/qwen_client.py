"""
DashScope (Qwen) API 客户端
支持同步调用、SSE 流式输出和 Function Calling
"""
import json
import logging
from typing import AsyncGenerator

import httpx

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, QWEN_MODEL

logger = logging.getLogger("info-hub.qwen")

CHAT_URL = f"{DASHSCOPE_BASE_URL}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
    "Content-Type": "application/json",
}


async def chat(
    messages: list[dict],
    model: str = QWEN_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """同步调用 Qwen，返回完整响应文本"""
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


async def chat_stream(
    messages: list[dict],
    model: str = QWEN_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """流式调用 Qwen，逐块 yield 文本内容"""
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


async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    model: str = QWEN_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """调用 Qwen with Function Calling，返回完整响应（含 tool_calls）"""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "tools": tools,
        "tool_choice": "auto",  # 让模型自主决定是否调用工具
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(CHAT_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        message = data["choices"][0]["message"]
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", []),
            "finish_reason": data["choices"][0].get("finish_reason", ""),
        }


async def chat_stream_with_tools(
    messages: list[dict],
    tools: list[dict],
    model: str = QWEN_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """流式调用 Qwen with Function Calling
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

    return {
        "content": "".join(accumulated_content),
        "tool_calls": tool_calls if tool_calls else None,
    }

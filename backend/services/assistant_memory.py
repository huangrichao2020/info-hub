"""复盘大师 Agent 记忆系统 - SQLite 存储"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from database import get_db

logger = logging.getLogger("info-hub.assistant")


def init_assistant_tables():
    """初始化 Assistant 相关表"""
    with get_db() as conn:
        # 对话历史
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assistant_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # 用户记忆（偏好/事实/约束）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assistant_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                tags TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def add_history(role: str, content: str) -> int:
    """添加对话历史"""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO assistant_history (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, now_iso),
        )
        conn.commit()
        return cursor.lastrowid


def get_history(limit: int = 30) -> list[dict]:
    """获取最近对话历史"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM assistant_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def clear_history():
    """清空对话历史"""
    with get_db() as conn:
        conn.execute("DELETE FROM assistant_history")
        conn.commit()


def add_memory(content: str, kind: str = "fact", tags: str = "") -> int:
    """添加记忆"""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO assistant_memories (kind, content, tags, status, created_at) VALUES (?, ?, ?, 'active', ?)",
            (kind, content, tags, now_iso),
        )
        conn.commit()
        return cursor.lastrowid


def get_memories(scope: str = "active", tags: str = "") -> list[dict]:
    """获取活跃记忆"""
    with get_db() as conn:
        if tags:
            rows = conn.execute(
                "SELECT id, kind, content, tags, status, created_at FROM assistant_memories WHERE status = ? AND tags LIKE ? ORDER BY created_at DESC",
                (scope, f"%{tags}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, kind, content, tags, status, created_at FROM assistant_memories WHERE status = ? ORDER BY created_at DESC",
                (scope,),
            ).fetchall()
        return [dict(r) for r in rows]


def update_memory_status(memory_id: int, status: str):
    """更新记忆状态"""
    with get_db() as conn:
        conn.execute(
            "UPDATE assistant_memories SET status = ? WHERE id = ?",
            (status, memory_id),
        )
        conn.commit()

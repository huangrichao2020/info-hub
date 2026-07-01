"""复盘盒子（fupanhezi）涨停数据缓存 + 读取模块

原集成在 GenericAgent/scripts/imagination_scorer.py，2026-07-01 拆出
到 info-hub 作为独立能力。GA agent 已停，所有 GenericAgent LaunchAgent 已废弃。

数据源：
- 官网：https://box.fupanhezi.com/stock/v1/zt-table  (POST JSON)
- 本地缓存：~/.hermes/data/fupanhezi/fupanhezi.db (SQLite)
- 用途：涨停梯队/封板资金/连板数/涨停原因（ztReson）

CLI:
  python fupanhezi.py update --days 21           # 增量更新缓存
  python fupanhezi.py read --date 2026-06-30    # 读取某日涨停池
  python fupanhezi.py read --latest              # 读取最近一个交易日
  python fupanhezi.py info                        # 看缓存统计
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

FUPANHEZI_BASE_URL = "https://box.fupanhezi.com"
DEFAULT_DB_PATH = Path.home() / ".hermes/data/fupanhezi/fupanhezi.db"
DEFAULT_LOOKBACK_DAYS = 21

# ============================================================
# Utils
# ============================================================

def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_trade_date(value: str | None) -> str | None:
    """接受 YYYY-MM-DD / YYYYMMDD，返回 YYYY-MM-DD"""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    if len(raw) == 10 and raw[4] == "-":
        return raw
    try:
        return datetime.strptime(raw, "%Y/%m/%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def candidate_trade_dates(end_date: str | None = None, lookback_days: int = 0) -> list[str]:
    """从 end_date 往前 lookback_days 个候选交易日（不去重周末，只按自然日）"""
    end = end_date or datetime.now().strftime("%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    return [(end_dt - timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(lookback_days + 1)]


# ============================================================
# 网络层
# ============================================================

def fetch_fupanhezi_web_records(trade_date: str, timeout: int = 30) -> list[dict[str, Any]]:
    """从复盘盒子官网拉某日的涨停股票列表"""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{FUPANHEZI_BASE_URL}/",
        "Origin": FUPANHEZI_BASE_URL,
        "Content-Type": "application/json",
    }
    payload = {"beginDate": trade_date, "endDate": trade_date, "ztlbNum": 1}
    try:
        response = requests.post(
            f"{FUPANHEZI_BASE_URL}/stock/v1/zt-table",
            headers=headers, json=payload, timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, json.JSONDecodeError):
        return []

    if result.get("code") != 0:
        return []

    records: list[dict[str, Any]] = []
    for row in ((result.get("data") or {}).get("body") or []):
        for cell in row or []:
            if not isinstance(cell, dict):
                continue
            if _to_int(cell.get("ztlbNum")) <= 0:
                continue
            if not cell.get("ztReson"):
                continue
            records.append(cell)
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        unique[(str(record.get("date")), str(record.get("stockCode")))] = record
    return list(unique.values())


# ============================================================
# SQLite 缓存层
# ============================================================

def ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zt_records (
                date TEXT NOT NULL,
                stockCode TEXT NOT NULL,
                stockName TEXT,
                ztReson TEXT,
                ztlbNum INTEGER,
                fbAmount REAL,
                amo REAL,
                closePe REAL,
                realHsRate REAL,
                zbNum INTEGER,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (date, stockCode)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_zt_records_date ON zt_records(date)")


def upsert_records(db_path: Path, records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    ensure_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            str(record.get("date") or ""),
            str(record.get("stockCode") or ""),
            str(record.get("stockName") or ""),
            str(record.get("ztReson") or ""),
            _to_int(record.get("ztlbNum")),
            _to_float(record.get("fbAmount")),
            _to_float(record.get("amo")),
            _to_float(record.get("closePe")),
            _to_float(record.get("realHsRate") or record.get("hsRate")),
            _to_int(record.get("zbNum")),
            json.dumps(record, ensure_ascii=False, sort_keys=True),
            now,
        )
        for record in records
        if record.get("date") and record.get("stockCode")
    ]
    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            """
            INSERT INTO zt_records (
                date, stockCode, stockName, ztReson, ztlbNum, fbAmount,
                amo, closePe, realHsRate, zbNum, payload, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, stockCode) DO UPDATE SET
                stockName=excluded.stockName,
                ztReson=excluded.ztReson,
                ztlbNum=excluded.ztlbNum,
                fbAmount=excluded.fbAmount,
                amo=excluded.amo,
                closePe=excluded.closePe,
                realHsRate=excluded.realHsRate,
                zbNum=excluded.zbNum,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            rows,
        )
    return len(rows)


# ============================================================
# 读缓存
# ============================================================

def read_records(db_path: Path, date: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """从 SQLite 读取某日涨停池"""
    if not db_path.exists():
        return [], None
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            tables = {
                row["name"]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            if "zt_records" not in tables:
                return [], None
            trade_date = normalize_trade_date(date) if date else None
            if not trade_date:
                latest = conn.execute("SELECT MAX(date) AS latest_date FROM zt_records").fetchone()["latest_date"]
                trade_date = latest
            if not trade_date:
                return [], None
            rows = conn.execute(
                "SELECT payload FROM zt_records WHERE date = ? ORDER BY ztlbNum DESC, fbAmount DESC",
                (trade_date,),
            ).fetchall()
    except sqlite3.Error:
        return [], None

    records = []
    for row in rows:
        try:
            records.append(json.loads(row["payload"]))
        except json.JSONDecodeError:
            continue
    return records, trade_date


def cache_stats(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {"exists": False, "path": str(db_path)}
    with sqlite3.connect(str(db_path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM zt_records").fetchone()[0]
        date_range = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(DISTINCT date) FROM zt_records"
        ).fetchone()
    return {
        "exists": True,
        "path": str(db_path),
        "total_records": count,
        "earliest_date": date_range[0],
        "latest_date": date_range[1],
        "trade_days": date_range[2],
    }


# ============================================================
# 顶层：更新 / 读取
# ============================================================

def update_cache(
    db_path: Path = DEFAULT_DB_PATH,
    days: int = DEFAULT_LOOKBACK_DAYS,
    end_date: str | None = None,
) -> dict[str, Any]:
    """增量更新缓存：拉最近 days 天"""
    ensure_db(db_path)
    updated: dict[str, int] = {}
    for trade_date in candidate_trade_dates(end_date, lookback_days=max(days - 1, 0)):
        records = fetch_fupanhezi_web_records(trade_date)
        if records:
            updated[trade_date] = upsert_records(db_path, records)
        time.sleep(0.12)  # 礼貌限流
    return {
        "db_path": str(db_path),
        "updated": updated,
        "total_records": sum(updated.values()),
    }


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="复盘盒子（fupanhezi）涨停数据缓存 + 读取")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_upd = sub.add_parser("update", help="增量更新缓存")
    p_upd.add_argument("--days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    p_upd.add_argument("--end-date", default=None)
    p_upd.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)

    p_rd = sub.add_parser("read", help="读取某日涨停池")
    p_rd.add_argument("--date", default=None, help="YYYY-MM-DD 或 YYYYMMDD")
    p_rd.add_argument("--latest", action="store_true", help="读最近一个交易日")
    p_rd.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    p_rd.add_argument("--limit", type=int, default=0, help="只输出前 N 条")

    p_info = sub.add_parser("info", help="看缓存统计")
    p_info.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)

    args = parser.parse_args()

    if args.cmd == "update":
        result = update_cache(args.db, args.days, args.end_date)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "read":
        target = None if args.latest else args.date
        records, trade_date = read_records(args.db, target)
        if args.limit:
            records = records[:args.limit]
        print(json.dumps({"date": trade_date, "count": len(records), "records": records},
                         ensure_ascii=False, indent=2))
    elif args.cmd == "info":
        print(json.dumps(cache_stats(args.db), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""盘中实时监控脚本 — 每分钟轮询东财行情，落盘 SQLite。

用法:
  # 手动跑一次
  python3 realtime_monitor.py --once

  # 持续监控（盘中自动循环）
  python3 realtime_monitor.py --daemon

  # 指定股票池文件
  python3 realtime_monitor.py --pool /root/wiki/entities/stock-pool.md --daemon
"""
import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("realtime-monitor")

# ── 配置 ──────────────────────────────────────────────
DEFAULT_POOL_FILE = "/root/wiki/entities/stock-pool.md"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "realtime_monitor.db")
EASTMONEY_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"

# 东财字段含义
FIELDS = [
    "f2",   # 最新价
    "f3",   # 涨跌幅 %
    "f4",   # 涨跌额
    "f12",  # 股票代码
    "f14",  # 股票名称
    "f15",  # 最高
    "f16",  # 最低
    "f17",  # 今开
    "f18",  # 昨收
    "f20",  # 总市值
    "f21",  # 流通市值
    "f43",  # 总手
    "f44",  # 换手率
    "f45",  # 量比
    "f47",  # 涨停价
    "f48",  # 跌停价
    "f62",  # 主力净流入
    "f184", # 成交额
    "f100", # 委比
    "f71",  # 市盈率(动)
    "f57",  # 代码(冗余)
]
FIELD_NAMES = ",".join(FIELDS)

# ── 股票池解析 ──────────────────────────────────────────
def parse_stock_pool(filepath: str) -> list[dict]:
    """解析 wiki 股票池 Markdown 表格，返回 [{code, name, group}]"""
    if not os.path.exists(filepath):
        logger.warning("股票池文件不存在: %s", filepath)
        return []

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    stocks = []
    current_group = "未分类"
    lines = content.split("\n")

    for i, line in enumerate(lines):
        # 识别板块标题（## 开头的进攻板块/观察组）
        h_match = re.match(r"^#{2,3}\s+(.+)", line)
        if h_match:
            current_group = h_match.group(1).strip()

        # 识别表格行
        if line.strip().startswith("|") and not line.strip().startswith("|---"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 2:
                code = cells[0].strip()
                name = cells[1].strip()
                # 过滤非股票行（表头、纯数字、大盘指数）
                if re.match(r"^\d{6}$", code) and name and not re.match(r"^代码$|^\d{4,}$", name):
                    # 确定交易所前缀
                    if code.startswith(("6", "9")):
                        secid = f"1.{code}"
                    else:
                        secid = f"0.{code}"
                    stocks.append({
                        "code": code,
                        "name": name,
                        "group": current_group,
                        "secid": secid,
                    })

    logger.info("从股票池解析到 %d 只股票（分组: %s）",
                len(stocks), current_group)
    return stocks


# ── 数据库 ──────────────────────────────────────────────
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            group_name TEXT,
            price REAL,
            change_pct REAL,
            change_amt REAL,
            high REAL,
            low REAL,
            open_ REAL,
            pre_close REAL,
            volume REAL,
            turnover REAL,
            turnover_rate REAL,
            volume_ratio REAL,
            limit_up REAL,
            limit_down REAL,
            main_flow REAL,
            amount REAL,
            market_cap REAL,
            pe REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshots_ts_code
        ON snapshots(ts, code)
    """)
    conn.commit()
    return conn


def save_snapshot(conn, ts: str, stock: dict, data: dict):
    conn.execute("""
        INSERT INTO snapshots (
            ts, code, name, group_name,
            price, change_pct, change_amt,
            high, low, open_, pre_close,
            volume, turnover, turnover_rate,
            volume_ratio, limit_up, limit_down,
            main_flow, amount, market_cap, pe
        ) VALUES (?,?,?,?, ?,?,?, ?,?,?,?, ?,?,?, ?,?,?, ?,?,?,?)
    """, (
        ts, stock["code"], stock.get("name"), stock.get("group"),
        data.get("f2"), data.get("f3"), data.get("f4"),
        data.get("f15"), data.get("f16"), data.get("f17"), data.get("f18"),
        data.get("f43"), data.get("f184"), data.get("f44"),
        data.get("f45"), data.get("f47"), data.get("f48"),
        data.get("f62"), data.get("f20"), data.get("f21"), data.get("f71"),
    ))


# ── 东财 API ────────────────────────────────────────────
def fetch_quotes(stocks: list[dict]) -> dict:
    """批量获取实时行情，返回 {code: data}"""
    secids = ",".join(s["secid"] for s in stocks)
    url = f"{EASTMONEY_URL}?fltt=2&fields={FIELD_NAMES}&secids={secids}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error("东财API请求失败: %s", e)
        return {}

    diff = (result.get("data") or {}).get("diff") or []
    quote_map = {}
    for item in diff:
        code = str(item.get("f12", "")).zfill(6)
        quote_map[code] = item

    return quote_map


# ── 循环逻辑 ────────────────────────────────────────────
def is_market_hours() -> bool:
    """判断是否在交易时段内（含开盘前1分钟）"""
    now = datetime.now()
    t = now.hour * 100 + now.minute
    # 非交易日直接跳过
    if now.weekday() >= 5:  # 周六日
        return False
    # 交易时段：9:25-11:30, 13:00-15:00
    return (925 <= t <= 1130) or (1300 <= t <= 1500)


def next_run_interval() -> int:
    """返回距离下次轮询的秒数，返回60=1分钟"""
    now = datetime.now()
    # 对齐到下一分钟的第5秒（避开整秒拥挤）
    next_min = now.replace(second=5, microsecond=0) + timedelta(minutes=1)
    return max(1, int((next_min - now).total_seconds()))


def run_once(stocks: list[dict], conn: sqlite3.Connection):
    """执行一次采集"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quotes = fetch_quotes(stocks)
    saved = 0
    for s in stocks:
        data = quotes.get(s["code"])
        if data and data.get("f2") is not None:  # f2 有价格才算有效
            save_snapshot(conn, ts, s, data)
            saved += 1
    conn.commit()
    logger.info("[%s] 采集 %d/%d 只", ts, saved, len(stocks))
    return saved


def daemon_loop(stocks: list[dict]):
    conn = init_db()
    logger.info("盘中监控启动 — 股票池 %d 只，数据路径: %s", len(stocks), DB_PATH)

    while True:
        now = datetime.now()
        t = now.hour * 100 + now.minute

        if is_market_hours():
            run_once(stocks, conn)
            interval = next_run_interval()
        else:
            # 收盘10分钟后自动退出
            if t > 1510 or t < 800:
                logger.info("收盘后自动退出，今日采集完成")
                conn.close()
                return
            interval = 300

        time.sleep(interval)


# ── 主入口 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="A股盘中实时监控")
    parser.add_argument("--pool", default=DEFAULT_POOL_FILE, help="股票池文件路径")
    parser.add_argument("--once", action="store_true", help="执行一次后退出")
    parser.add_argument("--daemon", action="store_true", help="持续监控（盘中自动循环）")
    parser.add_argument("--db", help="SQLite 路径（默认: data/realtime_monitor.db）")
    args = parser.parse_args()

    global DB_PATH
    if args.db:
        DB_PATH = args.db

    stocks = parse_stock_pool(args.pool)
    if not stocks:
        logger.error("未解析到任何股票，退出")
        sys.exit(1)

    if args.once:
        conn = init_db()
        saved = run_once(stocks, conn)
        conn.close()
        print(f"采集完成: {saved}/{len(stocks)}")
        return

    if args.daemon:
        daemon_loop(stocks)
        return

    # 默认：一次采集后退出
    conn = init_db()
    run_once(stocks, conn)
    conn.close()


if __name__ == "__main__":
    main()

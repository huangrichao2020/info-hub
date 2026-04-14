"""
Info-Hub SQLite 数据库管理
"""
import sqlite3
from contextlib import contextmanager
from config import INFOHUB_DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_news (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    keywords TEXT,
    published_at TEXT,
    collected_at TEXT NOT NULL,
    heat_score INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ai_news_collected ON ai_news(collected_at);
CREATE INDEX IF NOT EXISTS idx_ai_news_heat ON ai_news(heat_score);

CREATE TABLE IF NOT EXISTS trending_topics (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    heat_score INTEGER,
    category TEXT,
    url TEXT,
    extra_json TEXT,
    collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trending_collected ON trending_topics(collected_at);

CREATE TABLE IF NOT EXISTS viral_content (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    heat_score INTEGER,
    cross_platform_count INTEGER DEFAULT 1,
    viral_template TEXT,
    analysis_json TEXT,
    collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_viral_collected ON viral_content(collected_at);

CREATE TABLE IF NOT EXISTS generated_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    platform TEXT NOT NULL,
    style TEXT,
    content TEXT NOT NULL,
    word_count INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_json TEXT NOT NULL,
    report_content TEXT NOT NULL,
    report_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_draft (
    draft_key TEXT PRIMARY KEY,
    portfolio_json TEXT NOT NULL,
    report_date TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_state (
    job_name TEXT PRIMARY KEY,
    last_run_at TEXT,
    last_status TEXT,
    items_collected INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS turn_strong_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL UNIQUE,
    previous_trade_date TEXT,
    screening_query TEXT NOT NULL,
    status TEXT NOT NULL,
    selection_total INTEGER DEFAULT 0,
    generated_at TEXT NOT NULL,
    refreshed_at TEXT NOT NULL,
    conditions_json TEXT,
    market_snapshot_json TEXT,
    candidates_json TEXT NOT NULL,
    overall_analysis_json TEXT,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_turn_strong_runs_trade_date ON turn_strong_runs(trade_date DESC);

CREATE TABLE IF NOT EXISTS mx_key_usage (
    usage_date TEXT NOT NULL,
    key_name TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    quota_exhausted INTEGER DEFAULT 0,
    last_used_at TEXT,
    last_error TEXT,
    PRIMARY KEY (usage_date, key_name)
);
"""


def init_db():
    """初始化数据库，创建所有表"""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)


@contextmanager
def get_db():
    """获取数据库连接（上下文管理器）"""
    conn = sqlite3.connect(str(INFOHUB_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

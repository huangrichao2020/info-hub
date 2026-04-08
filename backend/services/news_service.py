"""财经新闻服务 - 包装 uwillberich news_collector"""
import asyncio
import math
import re
import sqlite3
import logging
from datetime import datetime, timezone
from config import UWILLBERICH_NEWS_DB

logger = logging.getLogger("info-hub.news")

# 财经热词权重
_FIN_HOT_KEYWORDS = {
    "涨停": 40, "跌停": 35, "暴涨": 30, "暴跌": 30, "利好": 25, "利空": 25,
    "央行": 30, "降息": 30, "加息": 30, "降准": 30, "政策": 20,
    "重磅": 25, "突发": 25, "紧急": 20, "独家": 20, "首次": 15,
    "AI": 20, "芯片": 20, "新能源": 15, "半导体": 15,
    "北向资金": 20, "主力": 15, "机构": 15, "外资": 15,
    "GDP": 20, "CPI": 15, "PMI": 15,
    "茅台": 15, "宁德": 15, "比亚迪": 15, "英伟达": 15,
}

_SOURCE_WEIGHT = {
    "cls": 1.3,       # 财联社快讯时效强
    "eastmoney": 1.1,
    "sina": 1.0,
    "ths": 1.0,
}


def _compute_fin_heat(title: str, summary: str, source: str, collected_at: str) -> int:
    """算财经新闻热度 (1-1000)"""
    text = f"{title} {summary}".lower()

    # 关键词分
    kw_score = 0
    matched = set()
    for kw, pts in _FIN_HOT_KEYWORDS.items():
        if kw.lower() in text and kw.lower() not in matched:
            kw_score += pts
            matched.add(kw.lower())
    kw_score = min(kw_score, 200)

    # 标题特征
    feat = 0
    if re.search(r'\d+%', title):
        feat += 15  # 含百分比
    elif re.search(r'\d+', title):
        feat += 8
    if any(c in title for c in '！!'):
        feat += 5
    if len(title) > 20:
        feat += 5

    # 来源权重
    src_mult = _SOURCE_WEIGHT.get(source, 1.0)

    # 时效衰减 (半衰期8小时, 财经新闻时效更强)
    time_mult = 1.0
    try:
        if collected_at:
            ct = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - ct.astimezone(timezone.utc)).total_seconds() / 3600
            if hours_ago < 0:
                hours_ago = 0
            time_mult = math.exp(-0.087 * hours_ago)  # ln(2)/8 ≈ 0.087
    except Exception:
        pass

    raw = (kw_score + feat) * src_mult * time_mult
    return max(1, min(1000, int(raw * 4.35)))


async def collect_financial_news() -> int:
    """触发一次财经新闻采集，返回采集条数"""
    try:
        import news_collector
        count = await asyncio.to_thread(news_collector.poll_once)
        return count or 0
    except Exception as e:
        logger.error(f"采集失败: {e}")
        return 0


def get_news(source: str = "", keyword: str = "", hours: int = 24, page: int = 1, page_size: int = 50) -> list[dict]:
    """从 uwillberich 新闻库读取财经新闻，按热度排序"""
    if not UWILLBERICH_NEWS_DB.exists():
        return []

    conn = sqlite3.connect(str(UWILLBERICH_NEWS_DB))
    conn.row_factory = sqlite3.Row

    sql = "SELECT * FROM news WHERE 1=1"
    params = []

    if source:
        sql += " AND source = ?"
        params.append(source)
    if keyword:
        sql += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if hours:
        sql += " AND collected_at >= datetime('now', ?)"
        params.append(f"-{hours} hours")

    # 先拉全部，Python 层算分排序
    sql += " ORDER BY collected_at DESC LIMIT 500"

    try:
        rows = conn.execute(sql, params).fetchall()
        items = []
        for r in rows:
            d = dict(r)
            d["heat_score"] = _compute_fin_heat(
                d.get("title", ""), d.get("summary", ""),
                d.get("source", ""), d.get("collected_at", ""),
            )
            items.append(d)

        # 按热度降序
        items.sort(key=lambda x: x["heat_score"], reverse=True)

        # 分页
        start = (page - 1) * page_size
        return items[start:start + page_size]
    finally:
        conn.close()


def get_sources() -> list[str]:
    """获取所有新闻来源"""
    if not UWILLBERICH_NEWS_DB.exists():
        return []
    conn = sqlite3.connect(str(UWILLBERICH_NEWS_DB))
    try:
        rows = conn.execute("SELECT DISTINCT source FROM news").fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()

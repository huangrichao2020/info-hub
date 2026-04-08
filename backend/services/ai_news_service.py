"""AI新闻聚合服务"""
import hashlib
import logging
import math
import re
from datetime import datetime, timezone

import httpx

from database import get_db

logger = logging.getLogger("info-hub.ai_news")

# ── 热度评分配置 ─────────────────────────────────────────

# 高权重关键词 → 基础分
_HOT_KEYWORDS = {
    "OpenAI": 40, "GPT": 35, "Claude": 35, "Anthropic": 30,
    "DeepSeek": 40, "Sora": 30, "Gemini": 30, "Google": 20,
    "大模型": 25, "AGI": 30, "融资": 20, "开源": 20,
    "突破": 15, "发布": 15, "首个": 20, "最新": 10,
    "芯片": 20, "英伟达": 25, "Nvidia": 25, "算力": 15,
    "智能体": 20, "Agent": 20, "AIGC": 15, "机器人": 15,
    "LLM": 15, "AI": 10, "人工智能": 10,
}

# 来源权重倍数
_SOURCE_WEIGHT = {
    "36kr": 1.3,
    "google-ai": 1.0,
}


def _compute_heat_score(title: str, summary: str, source: str, published_at: str) -> int:
    """
    算热度分 (0-1000):
      - 关键词命中累加 (0-200)
      - 来源权重 (x1.0-1.3)
      - 时效衰减: 24h 内满分, 之后指数衰减
      - 标题特征: 数字、引号、感叹号加分
    """
    text = f"{title} {summary}".lower()

    # 1. 关键词分
    kw_score = 0
    matched = set()
    for kw, pts in _HOT_KEYWORDS.items():
        if kw.lower() in text and kw.lower() not in matched:
            kw_score += pts
            matched.add(kw.lower())
    kw_score = min(kw_score, 200)

    # 2. 标题特征分 (0-30)
    feat_score = 0
    if re.search(r'\d+', title):
        feat_score += 10  # 含数字
    if any(c in title for c in '""「」'):
        feat_score += 5   # 含引号
    if any(c in title for c in '！!？?'):
        feat_score += 5   # 含感叹/问号
    if len(title) > 15:
        feat_score += 5   # 标题有信息量
    if '独家' in title or '首发' in title or '重磅' in title:
        feat_score += 10

    # 3. 来源权重
    src_mult = _SOURCE_WEIGHT.get(source, 1.0)

    # 4. 时效衰减
    time_mult = 1.0
    try:
        if published_at:
            # 尝试多种格式
            for fmt in ["%Y-%m-%d %H:%M:%S  %z", "%Y-%m-%dT%H:%M:%S%z",
                        "%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"]:
                try:
                    pub_dt = datetime.strptime(published_at.strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                pub_dt = None

            if pub_dt:
                hours_ago = (datetime.now(timezone.utc) - pub_dt.astimezone(timezone.utc)).total_seconds() / 3600
                if hours_ago < 0:
                    hours_ago = 0
                # 半衰期 12 小时
                time_mult = math.exp(-0.058 * hours_ago)  # ln(2)/12 ≈ 0.058
    except Exception:
        pass

    raw = (kw_score + feat_score) * src_mult * time_mult
    return max(1, min(1000, int(raw * 4.35)))  # 归一化到 1-1000


# ── 翻译 ─────────────────────────────────────────────────

def _is_chinese(text: str) -> bool:
    if not text:
        return True
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    return cjk / max(len(text), 1) > 0.3


async def _translate_to_chinese(title: str, summary: str) -> tuple[str, str]:
    try:
        from llm.qwen_client import chat
        prompt = (
            "将以下新闻标题和摘要翻译成中文，保持新闻语体，简洁准确。\n"
            "只输出翻译结果，格式：\n标题：<翻译>\n摘要：<翻译>\n\n"
            f"Title: {title}\nSummary: {summary[:300]}"
        )
        result = await chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        lines = result.strip().split("\n")
        t_title, t_summary = title, summary
        for line in lines:
            if line.startswith("标题：") or line.startswith("标题:"):
                t_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("摘要：") or line.startswith("摘要:"):
                t_summary = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        return t_title, t_summary
    except Exception as e:
        logger.warning(f"翻译失败，保留原文: {e}")
        return title, summary


# ── 采集 ─────────────────────────────────────────────────

AI_KEYWORDS = ["AI", "人工智能", "大模型", "LLM", "GPT", "Claude", "机器人", "芯片",
               "算力", "AIGC", "Sora", "OpenAI", "Anthropic", "DeepSeek", "智能体", "Agent"]

AI_RSS_FEEDS = [
    ("https://news.google.com/rss/search?q=AI+artificial+intelligence&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "google-ai"),
    ("https://36kr.com/feed", "36kr"),
]


async def collect_ai_news() -> int:
    count = 0
    async with httpx.AsyncClient(timeout=30) as client:
        for feed_url, source in AI_RSS_FEEDS:
            try:
                resp = await client.get(feed_url)
                if resp.status_code == 200:
                    items = _parse_rss(resp.text, source)
                    for item in items:
                        if not _is_chinese(item["title"]):
                            t, s = await _translate_to_chinese(item["title"], item["summary"])
                            item["title"] = t
                            item["summary"] = s
                        item["heat_score"] = _compute_heat_score(
                            item["title"], item["summary"],
                            item["source"], item["published_at"],
                        )
                    count += _save_items(items)
            except Exception as e:
                logger.warning(f"RSS采集失败 [{source}]: {e}")
    return count


def _parse_rss(xml_text: str, source: str) -> list[dict]:
    import xml.etree.ElementTree as ET
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title = item.findtext("title", "")
            if not any(kw.lower() in title.lower() for kw in AI_KEYWORDS):
                continue
            items.append({
                "id": hashlib.md5(f"{source}:{title}".encode()).hexdigest(),
                "source": source,
                "title": title,
                "summary": item.findtext("description", "")[:500],
                "url": item.findtext("link", ""),
                "keywords": ",".join(kw for kw in AI_KEYWORDS if kw.lower() in title.lower()),
                "published_at": item.findtext("pubDate", ""),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
    except ET.ParseError:
        logger.warning(f"RSS XML解析失败: {source}")
    return items


# ── 存储 ─────────────────────────────────────────────────

def _save_items(items: list[dict]) -> int:
    count = 0
    with get_db() as conn:
        for item in items:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO ai_news (id, source, title, summary, url, keywords, published_at, collected_at, heat_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item["id"], item["source"], item["title"], item["summary"],
                     item["url"], item["keywords"], item["published_at"],
                     item["collected_at"], item.get("heat_score", 0)),
                )
                count += 1
            except Exception:
                pass
    return count


# ── 查询 ─────────────────────────────────────────────────

def get_ai_news(keyword: str = "", page: int = 1, page_size: int = 50) -> list[dict]:
    with get_db() as conn:
        sql = "SELECT * FROM ai_news WHERE 1=1"
        params = []
        if keyword:
            sql += " AND (title LIKE ? OR keywords LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        sql += " ORDER BY heat_score DESC, collected_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

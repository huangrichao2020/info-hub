"""热搜采集服务 - 百度/微博/知乎/头条/抖音/小红书"""
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from database import get_db

logger = logging.getLogger("info-hub.trending")

# ── 通用平台 (简单 GET 即可) ──────────────────────────────
PLATFORM_APIS = {
    "baidu": "https://top.baidu.com/board?tab=realtime",
    "weibo": "https://weibo.com/ajax/side/hotSearch",
    "zhihu": "https://www.zhihu.com/api/v3/feed/topstory/hot-list-web?limit=50&desktop=true",
    "toutiao": "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
}

# 各平台需要的额外请求头
PLATFORM_HEADERS: dict[str, dict[str, str]] = {
    "weibo": {
        "Referer": "https://weibo.com/",
    },
    "zhihu": {
        "Referer": "https://www.zhihu.com/hot",
    },
}

# ── 小红书 headers (逆向 iOS 客户端, 硬编码 shield 令牌) ──
_XHS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                  "MicroMessenger/8.0.7(0x18000733) NetType/WIFI Language/zh_CN",
    "referer": "https://app.xhs.cn/",
    "xy-direction": "22",
    "shield": "XYAAAAAQAAAAEAAABTAAAAUzUWEe4xG1IYD9/c+qCLOlKGmTtFa+lG434Oe+FTRag"
              "xxoaz6rUWSZ3+juJYz8RZqct+oNMyZQxLEBaBEL+H3i0RhOBVGrauzVSARchIWFYwbwkV",
    "xy-platform-info": "platform=iOS&version=8.7&build=8070515"
                        "&deviceId=C323D3A5-6A27-4CE6-AA0E-51C9D4C26A24"
                        "&bundle=com.xingin.discover",
    "xy-common-params": "app_id=ECFAAF02&build=8070515&channel=AppStore"
                        "&deviceId=C323D3A5-6A27-4CE6-AA0E-51C9D4C26A24"
                        "&device_fingerprint=20230920120211bd7b71a80778509cf4211099ea911000010d2f20f6050264"
                        "&device_fingerprint1=20230920120211bd7b71a80778509cf4211099ea911000010d2f20f6050264"
                        "&device_model=phone"
                        "&fid=1695182528-0-0-63b29d709954a1bb8c8733eb2fb58f29"
                        "&gid=7dc4f3d168c355f1a886c54a898c6ef21fe7b9a847359afc77fc24ad"
                        "&identifier_flag=0&lang=zh-Hans&launch_id=716882697"
                        "&platform=iOS&project_id=ECFAAF"
                        "&sid=session.1695189743787849952190"
                        "&t=1695190591&teenager=0&tz=Asia/Shanghai&uis=light&version=8.7",
}


async def collect_trending() -> int:
    """采集六平台热搜，返回新增条数"""
    count = 0
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, trust_env=False) as client:
        # 通用四平台
        for platform, url in PLATFORM_APIS.items():
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    **PLATFORM_HEADERS.get(platform, {}),
                }
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    items = _parse_platform(platform, resp.text)
                    count += _save_trending(items)
                else:
                    logger.warning(f"热搜采集 [{platform}] HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"热搜采集失败 [{platform}]: {e}")

        # 抖音 (Mobile SDK, 零认证)
        try:
            resp = await client.get(
                "https://aweme.snssdk.com/aweme/v1/hot/search/list/",
                params={"device_platform": "android", "version_name": "13.2.0",
                        "version_code": "130200", "aid": "1128"},
                headers={"User-Agent": "okhttp3"},
            )
            if resp.status_code == 200:
                items = _parse_douyin(resp.json())
                count += _save_trending(items)
            else:
                logger.warning(f"热搜采集 [douyin] HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"热搜采集失败 [douyin]: {e}")

        # 小红书 (iOS 逆向 headers)
        try:
            resp = await client.get(
                "https://edith.xiaohongshu.com/api/sns/v1/search/hot_list",
                headers=_XHS_HEADERS,
            )
            if resp.status_code == 200:
                items = _parse_xiaohongshu(resp.json())
                count += _save_trending(items)
            else:
                logger.warning(f"热搜采集 [xiaohongshu] HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"热搜采集失败 [xiaohongshu]: {e}")

    return count


# ── 解析器 ────────────────────────────────────────────────

def _parse_platform(platform: str, text: str) -> list[dict]:
    """按平台解析热搜数据 (百度/微博/知乎/头条)"""
    now = datetime.now(timezone.utc).isoformat()
    items = []

    try:
        if platform == "weibo":
            data = json.loads(text)
            for item in data.get("data", {}).get("realtime", [])[:50]:
                items.append({
                    "id": hashlib.md5(f"weibo:{item.get('word', '')}".encode()).hexdigest(),
                    "platform": "weibo",
                    "title": item.get("word", ""),
                    "heat_score": item.get("num", 0),
                    "category": item.get("category", ""),
                    "url": f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
                    "collected_at": now,
                })
        elif platform == "toutiao":
            data = json.loads(text)
            for item in data.get("data", [])[:50]:
                items.append({
                    "id": hashlib.md5(f"toutiao:{item.get('Title', '')}".encode()).hexdigest(),
                    "platform": "toutiao",
                    "title": item.get("Title", ""),
                    "heat_score": item.get("HotValue", 0),
                    "category": "",
                    "url": item.get("Url", ""),
                    "collected_at": now,
                })
        elif platform == "zhihu":
            data = json.loads(text)
            for item in data.get("data", [])[:50]:
                target = item.get("target", {})
                title_area = target.get("title_area", {})
                metrics_area = target.get("metrics_area", {})
                link = target.get("link", {})
                title = title_area.get("text", "") or target.get("title", "")
                heat_text = metrics_area.get("text", "0")
                heat_score = _parse_heat_text(heat_text)
                url_str = link.get("url", "") or f"https://www.zhihu.com/question/{target.get('id', '')}"
                items.append({
                    "id": hashlib.md5(f"zhihu:{title}".encode()).hexdigest(),
                    "platform": "zhihu",
                    "title": title,
                    "heat_score": heat_score,
                    "category": "",
                    "url": url_str,
                    "collected_at": now,
                })
        elif platform == "baidu":
            match = re.search(r'<!--s-data:(.*?)-->', text)
            if match:
                data = json.loads(match.group(1))
                for item in data.get("data", {}).get("cards", [{}])[0].get("content", [])[:50]:
                    items.append({
                        "id": hashlib.md5(f"baidu:{item.get('word', '')}".encode()).hexdigest(),
                        "platform": "baidu",
                        "title": item.get("word", ""),
                        "heat_score": item.get("hotScore", 0),
                        "category": item.get("tag", ""),
                        "url": item.get("url", ""),
                        "collected_at": now,
                    })
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"解析 {platform} 数据失败: {e}")

    return items


def _parse_douyin(data: dict) -> list[dict]:
    """解析抖音热搜"""
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for item in data.get("data", {}).get("word_list", [])[:50]:
        word = item.get("word", "")
        items.append({
            "id": hashlib.md5(f"douyin:{word}".encode()).hexdigest(),
            "platform": "douyin",
            "title": word,
            "heat_score": item.get("hot_value", 0),
            "category": "",
            "url": f"https://www.douyin.com/search/{quote(word)}",
            "collected_at": now,
        })
    return items


def _parse_xiaohongshu(data: dict) -> list[dict]:
    """解析小红书热搜"""
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for item in data.get("data", {}).get("items", []):
        title = item.get("title", "")
        score_text = item.get("score", "0")
        heat_score = _parse_heat_text(score_text)
        items.append({
            "id": hashlib.md5(f"xiaohongshu:{title}".encode()).hexdigest(),
            "platform": "xiaohongshu",
            "title": title,
            "heat_score": heat_score,
            "category": item.get("word_type", ""),
            "url": f"https://www.xiaohongshu.com/search_result?keyword={quote(title)}&type=51",
            "collected_at": now,
        })
    return items


def _parse_heat_text(text: str) -> int:
    """解析热度文本: '234.5万' -> 2345000, '944.3w' -> 9443000, '12345' -> 12345"""
    if not text:
        return 0
    m = re.search(r'([\d.]+)\s*[万w]', text, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r'[\d]+', text)
    return int(m.group(0)) if m else 0


# ── 存储 & 查询 ──────────────────────────────────────────

def _save_trending(items: list[dict]) -> int:
    """保存热搜到数据库"""
    count = 0
    with get_db() as conn:
        for item in items:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO trending_topics (id, platform, title, heat_score, category, url, collected_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (item["id"], item["platform"], item["title"], item["heat_score"], item["category"], item["url"], item["collected_at"]),
                )
                count += 1
            except Exception:
                pass
    return count


def get_trending(platform: str = "", page: int = 1, page_size: int = 50) -> list[dict]:
    """查询热搜数据"""
    with get_db() as conn:
        sql = "SELECT * FROM trending_topics WHERE 1=1"
        params = []
        if platform:
            sql += " AND platform = ?"
            params.append(platform)
        sql += " ORDER BY heat_score DESC, collected_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

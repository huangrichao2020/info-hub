"""涨停分析服务 - 基于本地Baostock真实数据"""
import json
import os
import time
import logging
from datetime import datetime

logger = logging.getLogger("info-hub.zt")

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache', 'full_market_3m.json')
_cache = None
_cache_time = 0
_TTL = 300


def _load_cache():
    global _cache, _cache_time
    now = time.time()
    if _cache is None or (now - _cache_time) > _TTL:
        try:
            with open(CACHE_PATH, 'r') as f:
                _cache = json.load(f)
            _cache_time = now
        except Exception as e:
            logger.error(f"加载涨停缓存失败: {e}")
            _cache = {'zt_stocks': [], 'dt_stocks': [], 'all_stocks': [], 'sectors': []}
            _cache_time = now
    return _cache


async def get_zt_today():
    """获取今日涨停股"""
    cache = _load_cache()
    zt_stocks = cache.get('zt_stocks', [])

    results = []
    for s in zt_stocks:
        # 从行业信息推断涨停原因
        industry = s.get('industry', '')
        reason = f"{industry}板块" if industry else "个股异动"

        results.append({
            'code': s['code'],
            'name': s['name'],
            'change_pct': s['change_pct'],
            'reason': reason,
            'lianban_count': 1,  # baostock无法直接获取连板数，默认为1
            'seal_amount': 'N/A',  # 需要Level-2数据
            'volume': s.get('volume', 0),
            'close': s['close'],
            'market_value': '',
            'popularity_score': 50,
            'industry': industry,
            'date': s.get('date', ''),
        })

    return results


async def get_lianban():
    """获取连板股（从涨停股中筛选）"""
    # 简化版：涨幅>=19.8%视为连板（主板2天涨停）
    cache = _load_cache()
    all_stocks = cache.get('all_stocks', [])

    lianban = [s for s in all_stocks if s.get('change_pct', 0) >= 19.8]
    results = []
    for s in lianban:
        industry = s.get('industry', '')
        results.append({
            'code': s['code'],
            'name': s['name'],
            'change_pct': s['change_pct'],
            'lianban_count': 2,
            'reason': f"{industry}板块强势" if industry else "连续涨停",
            'date': s.get('date', ''),
        })

    return results


async def get_recent_zt(days=7):
    """获取近期涨停股（简化：返回当前涨停列表）"""
    return await get_zt_today()


async def get_zt_report(days=7):
    """生成涨停复盘报告"""
    zt = await get_zt_today()
    dt_cache = _load_cache()
    dt = dt_cache.get('dt_stocks', [])

    lines = [
        f"## 涨停复盘 ({datetime.now().strftime('%Y-%m-%d')})",
        f"涨停 {len(zt)} 家, 跌停 {len(dt)} 家",
        ""
    ]

    # 按行业统计
    industry_counts = {}
    for s in zt:
        ind = s.get('industry', '未知')
        industry_counts[ind] = industry_counts.get(ind, 0) + 1

    if industry_counts:
        lines.append("### 涨停行业分布")
        for ind, cnt in sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"- {ind}: {cnt}只")
        lines.append("")

    lines.append("### 涨停个股")
    for i, s in enumerate(zt[:20]):
        lines.append(f"{i+1}. {s['name']} ({s['code']}) {s['change_pct']:+.2f}% {s.get('reason','')}")

    return "\n".join(lines)


async def get_dt_today():
    """获取今日跌停股"""
    cache = _load_cache()
    dt_stocks = cache.get('dt_stocks', [])

    results = []
    for s in dt_stocks:
        industry = s.get('industry', '')
        results.append({
            'code': s['code'],
            'name': s['name'],
            'change_pct': s['change_pct'],
            'reason': f"{industry}板块走弱" if industry else "个股利空",
            'volume': s.get('volume', 0),
            'close': s['close'],
            'industry': industry,
        })

    return results

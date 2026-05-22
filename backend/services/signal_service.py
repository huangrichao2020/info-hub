"""
信号层服务 — 集成 a-stock-data V2.1 核心能力
覆盖：龙虎榜、行业对比、解禁日历、百度概念/资金流、同花顺热点
"""
import logging
import requests
import math
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("info-hub.signal")

# ── 通用 Header ──
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36"

# ═══════════════════════════════════════════════
# 1. 全市场龙虎榜（东财 datacenter 直连）
# ═══════════════════════════════════════════════

def daily_dragon_tiger(trade_date: str = None, min_net_buy: float = None) -> dict:
    """
    全市场龙虎榜。
    trade_date: YYYY-MM-DD（默认当日）
    min_net_buy: 净买入下限（万元），None 不过滤
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
        "columns": "ALL",
        "filter": f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
        "pageNumber": "1",
        "pageSize": "500",
        "sortTypes": "-1",
        "sortColumns": "BILLBOARD_NET_AMT",
        "source": "WEB",
        "client": "WEB",
    }
    headers = {"User-Agent": _UA, "Referer": "https://data.eastmoney.com/"}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        d = r.json()
        if not d.get("success") or not d.get("result") or not d["result"].get("data"):
            return {"date": trade_date, "total": 0, "stocks": [], "note": "无数据"}
        
        data = d["result"]["data"]
        actual_date = data[0].get("TRADE_DATE", "")[:10] if data else trade_date
        stocks = []
        for row in data:
            net_buy = (row.get("BILLBOARD_NET_AMT") or 0) / 10000
            if min_net_buy is not None and net_buy < min_net_buy:
                continue
            stocks.append({
                "code": row.get("SECURITY_CODE", ""),
                "name": row.get("SECURITY_NAME_ABBR", ""),
                "reason": row.get("EXPLANATION", ""),
                "close": row.get("CLOSE_PRICE") or 0,
                "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
                "net_buy_wan": round(net_buy, 1),
                "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
                "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
                "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
            })
        return {"date": actual_date, "total": len(stocks), "stocks": stocks}
    except Exception as e:
        logger.warning("龙虎榜获取失败: %s", e)
        return {"error": str(e)}


def dragon_tiger_stock(code: str, trade_date: str = None, look_back: int = 30) -> dict:
    """
    个股龙虎榜历史 + 席位明细 + 机构统计
    """
    import akshare as ak
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    
    start = datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)
    
    # 1. 上榜记录
    records = []
    try:
        df = ak.stock_lhb_detail_em(
            start_date=start.strftime("%Y%m%d"),
            end_date=trade_date.replace("-", "")
        )
        if not df.empty:
            df_stock = df[df["代码"] == code]
            for _, row in df_stock.iterrows():
                records.append({
                    "date": str(row.get("上榜日", "")),
                    "reason": row.get("上榜原因", ""),
                    "interpret": row.get("解读", ""),
                    "net_buy": row.get("龙虎榜净买额", 0),
                    "turnover": row.get("换手率", 0),
                })
    except Exception as e:
        logger.debug("龙虎榜记录获取失败: %s", e)
    
    # 2. 最近上榜的买卖席位
    seats = {"buy": [], "sell": []}
    if records:
        latest = records[0]["date"]
        if isinstance(latest, str):
            latest_date = latest.replace("-", "")[:8]
        else:
            latest_date = latest.strftime("%Y%m%d")
        for flag in ["买入", "卖出"]:
            key = "buy" if flag == "买入" else "sell"
            try:
                df_detail = ak.stock_lhb_stock_detail_em(
                    symbol=code, date=latest_date, flag=flag
                )
                if not df_detail.empty:
                    for _, row in df_detail.head(5).iterrows():
                        seats[key].append({
                            "name": row.get("交易营业部名称", ""),
                            "buy_amt": row.get("买入金额", 0),
                            "sell_amt": row.get("卖出金额", 0),
                            "net": row.get("净额", 0),
                        })
            except Exception as e:
                logger.debug("龙虎榜%s席位获取失败: %s", flag, e)
    
    # 3. 机构买卖统计（从席位数据中统计）
    institution = {"buy_count": 0, "sell_count": 0, "net_amount": 0}
    for s in seats["buy"]:
        if "机构专用" in s["name"]:
            institution["buy_count"] += 1
            institution["net_amount"] += s.get("net", 0)
    for s in seats["sell"]:
        if "机构专用" in s["name"]:
            institution["sell_count"] += 1
            institution["net_amount"] -= s.get("net", 0)
    
    # 清理 NaN 值确保 JSON 可序列化
    def _clean_nan(obj):
        if isinstance(obj, dict):
            return {k: _clean_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean_nan(v) for v in obj]
        if isinstance(obj, float) and math.isnan(obj):
            return 0.0
        return obj
    
    return _clean_nan({
        "code": code, 
        "records": records,
        "seats": seats,
        "institution": institution
    })


# ═══════════════════════════════════════════════
# 2. 行业横向对比（同花顺 90 行业）
# ═══════════════════════════════════════════════

def industry_comparison(top_n: int = 20) -> dict:
    """
    全行业涨跌幅排名（同花顺 ~90 个行业）
    """
    import akshare as ak
    try:
        df = ak.stock_board_industry_summary_ths()
        if df.empty:
            return {"top": [], "bottom": [], "total": 0}
        
        rows = []
        for i, row in df.iterrows():
            rows.append({
                "rank": i + 1,
                "name": row.get("板块", ""),
                "change_pct": row.get("涨跌幅", 0),
                "turnover_yi": row.get("总成交额", 0),
                "up_count": row.get("上涨家数", 0),
                "down_count": row.get("下跌家数", 0),
                "leader": row.get("领涨股", ""),
            })
        
        return {
            "top": rows[:top_n],
            "bottom": rows[-top_n:],
            "total": len(rows),
        }
    except Exception as e:
        logger.warning("行业对比获取失败: %s", e)
        return {"error": str(e)}


# ═══════════════════════════════════════════════
# 3. 限售解禁日历
# ═══════════════════════════════════════════════

def lockup_expiry(code: str, trade_date: str = None, forward_days: int = 90) -> dict:
    """
    限售解禁日历：历史 + 未来预警
    """
    import akshare as ak
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    
    history = []
    try:
        df = ak.stock_restricted_release_queue_em(symbol=code)
        if not df.empty:
            for _, row in df.head(15).iterrows():
                history.append({
                    "date": str(row.get("解禁时间", "")),
                    "type": row.get("限售股类型", ""),
                    "shares": row.get("解禁数量", 0),
                    "ratio": row.get("实际解禁市值占总市值比例", 0),
                })
    except Exception as e:
        logger.debug("历史解禁获取失败: %s", e)
    
    upcoming = []
    end_date = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=forward_days)
    try:
        df = ak.stock_restricted_release_detail_em(
            date=trade_date.replace("-", "")
        )
        if not df.empty:
            df_stock = df[df["股票代码"] == code]
            for _, row in df_stock.iterrows():
                d = str(row.get("解禁日期", ""))
                if trade_date.replace("-", "") <= d <= end_date.strftime("%Y%m%d"):
                    upcoming.append({
                        "date": d,
                        "type": row.get("限售股类型", ""),
                        "shares": row.get("解禁数量", 0),
                        "float_ratio": row.get("占流通股比例", 0),
                    })
    except Exception as e:
        logger.debug("未来解禁获取失败: %s", e)
    
    return {
        "code": code,
        "history": history[:10],
        "upcoming": upcoming,
        "warning": bool(upcoming),
    }


# ═══════════════════════════════════════════════
# 4. 百度股市通概念板块
# ═══════════════════════════════════════════════

_BAIDU_PAE_HEADERS = {
    "Host": "finance.pae.baidu.com",
    "User-Agent": _UA,
    "Accept": "application/vnd.finance-web.v1+json",
    "Origin": "https://gushitong.baidu.com",
    "Referer": "https://gushitong.baidu.com/",
}

def baidu_concept_blocks(code: str) -> dict:
    """
    百度股市通概念板块归属（行业/概念/地域）
    """
    try:
        url = f"https://finance.pae.baidu.com/api/getrelatedblock?code={code}&market=ab&typeCode=all&finClientType=pc"
        r = requests.get(url, headers=_BAIDU_PAE_HEADERS, timeout=10)
        d = r.json()
        if str(d.get("ResultCode", -1)) != "0":
            return {"error": "ResultCode != 0"}
        
        result = {"industry": [], "concept": [], "region": [], "concept_tags": []}
        for block in d.get("Result", []):
            block_type = block.get("type", "")
            for item in block.get("list", []):
                entry = {
                    "name": item.get("name", ""),
                    "change_pct": item.get("increase", ""),
                    "desc": item.get("desc", ""),
                }
                if "行业" in block_type:
                    result["industry"].append(entry)
                elif "概念" in block_type:
                    result["concept"].append(entry)
                    result["concept_tags"].append(entry["name"])
                elif "地域" in block_type:
                    result["region"].append(entry)
        return {"code": code, **result}
    except Exception as e:
        logger.warning("百度概念获取失败: %s", e)
        return {"error": str(e)}


# ═══════════════════════════════════════════════
# 5. 同花顺热点（当日强势股 + 题材归因）
# ═══════════════════════════════════════════════

def ths_hot_reason(date: str = None) -> dict:
    """
    同花顺当日强势股归因（题材 reason tags）
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date}/orderby/date/orderway/desc/charset/GBK/"
        headers = {"User-Agent": _UA}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if data.get("errocode", 0) != 0:
            return {"error": data.get("errormsg", "")}
        
        rows = data.get("data") or []
        # 词频统计题材
        from collections import Counter
        all_tags = []
        for row in rows:
            reason = row.get("reason", "")
            if reason:
                tags = [t.strip() for t in str(reason).split("+") if t.strip()]
                all_tags.extend(tags)
        
        top_tags = dict(Counter(all_tags).most_common(15))
        
        return {
            "date": date,
            "count": len(rows),
            "top_tags": top_tags,
            "stocks": rows[:50],  # 返回前 50 只
        }
    except Exception as e:
        logger.warning("同花顺热点获取失败: %s", e)
        return {"error": str(e)}

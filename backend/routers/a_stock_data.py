"""
a_stock_data.py — A股全栈数据路由

集成 a-stock-data 21 端点能力，覆盖：
- 行情层：mootdx K线/五档/逐笔 + 腾讯 PE/PB/市值
- 研报层：东财研报列表/PDF + 同花顺一致预期 + iwencai NL搜索
- 信号层：同花顺热点/北向/百度资金流/龙虎榜/解禁/行业对比
- 新闻层：akshare 个股新闻/财联社/全球资讯
- 基础数据：mootdx 财务快照/F10 + akshare 基本面
- 公告层：巨潮公告 + mootdx 公告摘要

作者：Simon Lin (a-stock-data) + Hermes Agent 集成
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("info-hub")
router = APIRouter(tags=["A股全栈数据"])

# ── 市场前缀 ──
def _get_prefix(code: str) -> str:
    if code.startswith(("6", "9")): return "sh"
    elif code.startswith("8"): return "bj"
    else: return "sz"

def _normalize_code(code: str) -> str:
    """归一化为纯6位数字"""
    return code.upper().replace("SH", "").replace("SZ", "").replace("BJ", "").replace(".", "")

# ═══════════════════════════════════════
# Layer 1: 行情层
# ═══════════════════════════════════════

@router.get("/quote/tencent")
def tencent_quote(codes: str = Query(..., description="股票代码，逗号分隔，如 688017,300476")):
    """腾讯实时行情 — PE/PB/市值/换手率/涨跌停"""
    import urllib.request
    code_list = [c.strip() for c in codes.split(",")]
    prefixed = []
    for c in code_list:
        c = _normalize_code(c)
        prefixed.append(f"{_get_prefix(c)}{c}")

    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read().decode("gbk")

    result = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]
        result[code] = {
            "name": vals[1],
            "price": float(vals[3]) if vals[3] else 0,
            "last_close": float(vals[4]) if vals[4] else 0,
            "open": float(vals[5]) if vals[5] else 0,
            "change_amt": float(vals[31]) if vals[31] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
            "high": float(vals[33]) if vals[33] else 0,
            "low": float(vals[34]) if vals[34] else 0,
            "amount_wan": float(vals[37]) if vals[37] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm": float(vals[39]) if vals[39] else 0,
            "amplitude_pct": float(vals[43]) if vals[43] else 0,
            "mcap_yi": float(vals[44]) if vals[44] else 0,
            "float_mcap_yi": float(vals[45]) if vals[45] else 0,
            "pb": float(vals[46]) if vals[46] else 0,
            "limit_up": float(vals[47]) if vals[47] else 0,
            "limit_down": float(vals[48]) if vals[48] else 0,
            "vol_ratio": float(vals[49]) if vals[49] else 0,
            "pe_static": float(vals[52]) if vals[52] else 0,
        }
    return result


@router.get("/quote/mootdx/kline")
def mootdx_kline(code: str = Query(...), category: int = Query(4, description="4=日线,5=周线,6=月线,7=1min,8=5min"), offset: int = 10):
    """mootdx K线数据"""
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market='std')
        code = _normalize_code(code)
        klines = client.bars(symbol=code, category=category, offset=offset)
        return {"code": code, "category": category, "data": klines.to_dict("records") if hasattr(klines, 'to_dict') else klines}
    except Exception as e:
        raise HTTPException(500, f"mootdx K线获取失败: {e}")


@router.get("/quote/mootdx/quotes")
def mootdx_quotes(codes: str = Query(..., description="股票代码，逗号分隔")):
    """mootdx 实时报价（46字段）"""
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market='std')
        code_list = [_normalize_code(c.strip()) for c in codes.split(",")]
        quotes = client.quotes(symbol=code_list)
        return {"data": quotes.to_dict("records") if hasattr(quotes, 'to_dict') else quotes}
    except Exception as e:
        raise HTTPException(500, f"mootdx 报价获取失败: {e}")


# ═══════════════════════════════════════
# Layer 2: 研报层
# ═══════════════════════════════════════

@router.get("/research/eastmoney")
def eastmoney_reports(code: str = Query(...), max_pages: int = Query(3)):
    """东财研报列表 + PDF 下载链接"""
    import requests
    code = _normalize_code(code)
    REPORT_API = "https://reportapi.eastmoney.com/report/list"
    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Referer": "https://data.eastmoney.com/"})
    all_records = []

    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*", "pageSize": "50", "industry": "*",
            "rating": "*", "ratingChange": "*",
            "beginTime": "2025-01-01", "endTime": "2030-01-01",
            "pageNo": str(page), "qType": "0",
            "orgCode": "", "code": code, "rcode": "",
            "p": str(page), "pageNum": str(page), "pageNumber": str(page),
        }
        r = session.get(REPORT_API, params=params, timeout=15)
        d = r.json()
        rows = d.get("data") or []
        if not rows:
            break
        all_records.extend(rows)
        if page >= (d.get("TotalPage", 1) or 1):
            break

    # 添加 PDF 链接
    for rec in all_records:
        info_code = rec.get("infoCode", "")
        if info_code:
            rec["pdf_url"] = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"

    return {"code": code, "count": len(all_records), "reports": all_records[:50]}


@router.get("/research/consensus")
def consensus_eps(code: str = Query(...)):
    """同花顺机构一致预期 EPS"""
    try:
        import akshare as ak
        code = _normalize_code(code)
        df = ak.stock_profit_forecast_ths(symbol=code, indicator="预测年报每股收益")
        return {"code": code, "data": df.to_dict("records")}
    except Exception as e:
        raise HTTPException(500, f"一致预期获取失败: {e}")


# ═══════════════════════════════════════
# Layer 3: 信号层
# ═══════════════════════════════════════

@router.get("/signal/hot-stocks")
def ths_hot_stocks(date: str = Query(None)):
    """同花顺当日强势股 + 题材归因 reason tags"""
    import requests
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date}/orderby/date/orderway/desc/charset/GBK/"
    headers = {"User-Agent": "Mozilla/5.0 Chrome/117.0.0.0"}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("errocode", 0) != 0:
        raise HTTPException(500, f"同花顺热点错误: {data.get('errormsg', '')}")

    rows = data.get("data") or []
    rename_map = {
        "name": "名称", "code": "代码", "reason": "题材归因",
        "close": "收盘价", "zhangdie": "涨跌额", "zhangfu": "涨幅%",
        "huanshou": "换手率%", "chengjiaoe": "成交额",
        "chengjiaoliang": "成交量", "ddejingliang": "大单净量", "market": "市场",
    }
    result = []
    for row in rows:
        renamed = {}
        for k, v in row.items():
            renamed[rename_map.get(k, k)] = v
        result.append(renamed)
    return {"date": date, "count": len(result), "stocks": result}


@router.get("/signal/northbound")
def northbound_flow():
    """同花顺北向资金实时分钟流向"""
    import requests
    url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
    headers = {
        "User-Agent": "Mozilla/5.0 Chrome/117.0.0.0",
        "Host": "data.hexin.cn",
        "Referer": "https://data.hexin.cn/",
    }
    r = requests.get(url, headers=headers, timeout=10)
    d = r.json()
    times = d.get("time", [])
    hgt = d.get("hgt", [])
    sgt = d.get("sgt", [])
    n = len(times)
    return {
        "points": n,
        "latest": {
            "time": times[-1] if times else None,
            "hgt_yi": hgt[-1] if hgt else None,
            "sgt_yi": sgt[-1] if sgt else None,
        },
        "data": [{"time": times[i], "hgt_yi": hgt[i] if i < len(hgt) else None, "sgt_yi": sgt[i] if i < len(sgt) else None} for i in range(n)],
    }


@router.get("/signal/fund-flow")
def baidu_fund_flow(code: str = Query(...), date: str = Query(None)):
    """百度股市通个股资金流向（分钟级+日级）"""
    import requests
    code = _normalize_code(code)
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    else:
        date = date.replace("-", "")

    headers = {
        "Host": "finance.pae.baidu.com",
        "User-Agent": "Mozilla/5.0 Chrome/117.0.0.0",
        "Accept": "application/vnd.finance-web.v1+json",
        "Origin": "https://gushitong.baidu.com",
        "Referer": "https://gushitong.baidu.com/",
    }

    # 实时
    url_rt = f"https://finance.pae.baidu.com/vapi/v1/fundflow?code={code}&market=ab&date={date}&finClientType=pc"
    r_rt = requests.get(url_rt, headers=headers, timeout=10)
    d_rt = r_rt.json()

    # 历史
    url_hist = f"https://finance.pae.baidu.com/vapi/v1/fundsortlist?code={code}&market=ab&pn=0&rn=20&finClientType=pc"
    r_hist = requests.get(url_hist, headers=headers, timeout=10)
    d_hist = r_hist.json()

    return {"code": code, "realtime": d_rt.get("Result", {}), "history": d_hist.get("Result", {})}


@router.get("/signal/dragon-tiger")
def dragon_tiger(code: str = Query(...), trade_date: str = Query(None), look_back: int = 30):
    """龙虎榜席位数据"""
    try:
        import akshare as ak
        from datetime import datetime as dt
        code = _normalize_code(code)
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        start = dt.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)
        start_str = start.strftime("%Y%m%d")
        end_str = trade_date.replace("-", "")

        # 上榜记录
        records = []
        df = ak.stock_lhb_detail_em(start_date=start_str, end_date=end_str)
        if not df.empty:
            df_stock = df[df["代码"] == code]
            for _, row in df_stock.iterrows():
                records.append({
                    "date": str(row.get("日期", "")),
                    "reason": row.get("解读", ""),
                    "net_buy": row.get("龙虎榜净买额", 0),
                    "turnover": row.get("换手率", 0),
                })

        return {"code": code, "records": records}
    except Exception as e:
        raise HTTPException(500, f"龙虎榜数据获取失败: {e}")


@router.get("/signal/lockup")
def lockup_expiry(code: str = Query(...)):
    """限售解禁日历"""
    try:
        import akshare as ak
        code = _normalize_code(code)
        df = ak.stock_changes_em(symbol=code)
        return {"code": code, "data": df.to_dict("records")[:20]}
    except Exception as e:
        raise HTTPException(500, f"解禁数据获取失败: {e}")


@router.get("/signal/sector-compare")
def sector_compare():
    """行业横向对比（涨跌排名）"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        return {"count": len(df), "sectors": df.to_dict("records")[:30]}
    except Exception as e:
        raise HTTPException(500, f"行业对比数据获取失败: {e}")


# ═══════════════════════════════════════
# Layer 4: 新闻层
# ═══════════════════════════════════════

@router.get("/news/stock")
def stock_news(code: str = Query(...)):
    """个股新闻（东财）"""
    try:
        import akshare as ak
        code = _normalize_code(code)
        df = ak.stock_news_em(symbol=code)
        return {"code": code, "count": len(df), "news": df.to_dict("records")[:20]}
    except Exception as e:
        raise HTTPException(500, f"个股新闻获取失败: {e}")


@router.get("/news/cls")
def cls_news():
    """财联社快讯"""
    try:
        import akshare as ak
        df = ak.stock_info_global_cls()
        return {"count": len(df), "news": df.to_dict("records")[:30]}
    except Exception as e:
        raise HTTPException(500, f"财联社快讯获取失败: {e}")


# ═══════════════════════════════════════
# Layer 5: 基础数据层
# ═══════════════════════════════════════

@router.get("/fundamentals/mootdx")
def mootdx_finance(code: str = Query(...)):
    """mootdx 财务快照（37字段季报）"""
    try:
        from mootdx.quotes import Quotes
        code = _normalize_code(code)
        client = Quotes.factory(market='std')
        fin = client.finance(symbol=code)
        return {"code": code, "data": fin.to_dict("records") if hasattr(fin, 'to_dict') else fin}
    except Exception as e:
        raise HTTPException(500, f"财务数据获取失败: {e}")


@router.get("/fundamentals/basic")
def stock_basic_info(code: str = Query(...)):
    """akshare 个股基本面"""
    try:
        import akshare as ak
        code = _normalize_code(code)
        df = ak.stock_individual_info_em(symbol=code)
        return {"code": code, "data": df.to_dict("records")}
    except Exception as e:
        raise HTTPException(500, f"基本面数据获取失败: {e}")


# ═══════════════════════════════════════
# Layer 6: 公告层
# ═══════════════════════════════════════

@router.get("/announcement/cninfo")
def cninfo_announcements(code: str = Query(...)):
    """巨潮公告"""
    try:
        import akshare as ak
        code = _normalize_code(code)
        market = "沪市" if code.startswith("6") else ("北交所" if code.startswith("8") else "深市")
        df = ak.stock_zh_a_disclosure_report_cninfo(symbol=code, market=market)
        return {"code": code, "market": market, "count": len(df), "announcements": df.to_dict("records")[:20]}
    except Exception as e:
        raise HTTPException(500, f"公告获取失败: {e}")


@router.get("/concept-blocks")
def concept_blocks(code: str = Query(...)):
    """百度股市通概念板块归属"""
    import requests
    code = _normalize_code(code)
    headers = {
        "Host": "finance.pae.baidu.com",
        "User-Agent": "Mozilla/5.0 Chrome/117.0.0.0",
        "Accept": "application/vnd.finance-web.v1+json",
        "Origin": "https://gushitong.baidu.com",
        "Referer": "https://gushitong.baidu.com/",
    }
    url = f"https://finance.pae.baidu.com/api/getrelatedblock?code={code}&market=ab&typeCode=all&finClientType=pc"
    r = requests.get(url, headers=headers, timeout=10)
    d = r.json()
    if str(d.get("ResultCode", -1)) != "0":
        raise HTTPException(500, f"百度PAE错误: {d}")

    result = {"industry": [], "concept": [], "region": [], "concept_tags": []}
    for block in d.get("Result", []):
        block_type = block.get("type", "")
        for item in block.get("list", []):
            entry = {"name": item.get("name", ""), "change_pct": item.get("increase", "")}
            if "行业" in block_type:
                result["industry"].append(entry)
            elif "概念" in block_type:
                result["concept"].append(entry)
                result["concept_tags"].append(entry["name"])
            elif "地域" in block_type:
                result["region"].append(entry)
    return {"code": code, "blocks": result}

"""
市场数据服务（akshare 驱动）
实时行情采集：指数/板块/涨停/主力流向
"""
import json
import logging
import time
from datetime import datetime, time as dtime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("info-hub.marketdata")

# A股交易时间
TRADE_MORNING_START = dtime(9, 30)
TRADE_MORNING_END = dtime(11, 30)
TRADE_AFTERNOON_START = dtime(13, 0)
TRADE_AFTERNOON_END = dtime(15, 0)


def is_trade_time() -> bool:
    """判断当前是否在交易时间"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (
        (TRADE_MORNING_START <= t <= TRADE_MORNING_END) or
        (TRADE_AFTERNOON_START <= t <= TRADE_AFTERNOON_END)
    )


def is_pre_market() -> bool:
    """判断是否在集合竞价时间（09:15-09:25）"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return dtime(9, 15) <= t <= dtime(9, 25)


def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════
# 一、指数快照
# ═══════════════════════════════════════════════════════

def fetch_index_snapshot() -> Dict[str, Any]:
    """获取主要指数快照（走新浪直连，不需代理）"""
    try:
        import akshare as ak

        indices = {
            "shanghai": "上证指数",
            "chuangye": "创业板指",
            "shenzhen": "深证成指",
            "kechuang": "科创50",
            "hs300": "沪深300",
        }

        df = ak.stock_zh_index_spot_sina()  # 新浪直连
        if df is None or df.empty:
            return {}

        result = {}
        for key, name in indices.items():
            try:
                row = df[df["名称"] == name]
                if not row.empty:
                    price = float(row["最新价"].values[0])
                    change = float(row["涨跌幅"].values[0])
                    result[key] = {"name": name, "price": price, "change_pct": change}
            except Exception:
                result[key] = {"name": name, "price": 0, "change_pct": 0}

        return result
    except Exception as e:
        logger.error(f"fetch_index_snapshot failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════
# 二、涨停/跌停统计
# ═══════════════════════════════════════════════════════

def fetch_zt_dt_stats() -> Dict[str, Any]:
    """获取今日涨停/跌停/炸板统计（直连新浪全市场，本地算）"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot()
        if df is None or df.empty:
            return {"zt_count": 0, "zt_codes": [], "dt_count": 0, "break_count": 0, "break_rate": 0}

        # 过滤 ST 和停牌
        df = df[(df["名称"].str.contains("ST|退", na=False) == False) & (df["成交量"] > 1000)]

        # 涨停：主板 ≥9.5（10cm），创业板/科创板/北交所 ≥19.5（20cm）
        is_zt_10 = (df["涨跌幅"] >= 9.5) & (df["涨跌幅"] < 19.5)
        is_zt_20 = df["涨跌幅"] >= 19.5
        zt_mask = is_zt_10 | is_zt_20
        zt_count = int(zt_mask.sum())
        zt_codes = df.loc[zt_mask, "代码"].tolist()[:30]

        # 跌停
        is_dt_10 = (df["涨跌幅"] <= -9.5) & (df["涨跌幅"] > -19.5)
        is_dt_20 = df["涨跌幅"] <= -19.5
        dt_mask = is_dt_10 | is_dt_20
        dt_count = int(dt_mask.sum())

        # 炸板率暂用 0（需要昨日数据，本地计算无法获得昨日）
        break_count = 0
        break_rate = 0.0

        return {
            "zt_count": zt_count,
            "zt_codes": zt_codes,
            "dt_count": dt_count,
            "break_count": break_count,
            "break_rate": break_rate,
        }
    except Exception as e:
        logger.error(f"fetch_zt_dt_stats failed: {e}")
        return {"zt_count": 0, "zt_codes": [], "dt_count": 0, "break_count": 0, "break_rate": 0}


# ═══════════════════════════════════════════════════════
# 三、板块数据（涨幅榜 + 热门板块）
# ═══════════════════════════════════════════════════════

def fetch_sector_data() -> Dict[str, Any]:
    """获取板块涨跌和热门板块"""
    try:
        import akshare as ak
        import time as _time

        # 行业板块涨幅榜（代理容易被踢，retry 3 次）
        ind_df = None
        for _attempt in range(3):
            try:
                ind_df = ak.stock_board_industry_name_em()
                if ind_df is not None and not ind_df.empty:
                    break
            except Exception:
                _time.sleep(2)
        if ind_df is not None and not ind_df.empty:
            ind_df = ind_df.sort_values("涨跌幅", ascending=False)
            top_sectors = ind_df.head(15).to_dict("records")
        else:
            top_sectors = []

        # 概念板块
        concept_df = None
        for _attempt in range(3):
            try:
                concept_df = ak.stock_board_concept_name_em()
                if concept_df is not None and not concept_df.empty:
                    break
            except Exception:
                _time.sleep(2)
        if concept_df is not None and not concept_df.empty:
            concept_df = concept_df.sort_values("涨跌幅", ascending=False)
            top_concepts = concept_df.head(15).to_dict("records")
        else:
            top_concepts = []

        # 概念板块
        concept_df = None
        for _attempt in range(3):
            try:
                concept_df = ak.stock_board_concept_name_em()
                if concept_df is not None and not concept_df.empty:
                    break
            except Exception:
                _time.sleep(2)
        if concept_df is not None and not concept_df.empty:
            concept_df = concept_df.sort_values("涨跌幅", ascending=False)
            top_concepts = concept_df.head(15).to_dict("records")
        else:
            top_concepts = []

        # 金融三级表数据（证券/多元金融/银行）
        bank_df = ind_df if ind_df is not None and not ind_df.empty else None
        sec_strength = 0.0
        multi_fin_strength = 0.0
        bank_strength = 0.0

        if bank_df is not None:
            sec_row = bank_df[bank_df["板块名称"].str.contains("证券")]
            if not sec_row.empty:
                sec_strength = float(sec_row["涨跌幅"].values[0])

            multi_rows = bank_df[bank_df["板块名称"].str.contains("多元金融|多元|金融")]
            if not multi_rows.empty:
                multi_fin_strength = float(multi_rows["涨跌幅"].values[0])

            bank_row = bank_df[bank_df["板块名称"].str.contains("银行")]
            if not bank_row.empty:
                bank_strength = float(bank_row["涨跌幅"].values[0])

        return {
            "top_industry_sectors": top_sectors,
            "top_concept_sectors": top_concepts,
            "financial_tier": {
                "sec": sec_strength,
                "multi_fin": multi_fin_strength,
                "bank": bank_strength,
            },
            "hot_sector_count": len(ind_df[ind_df["涨跌幅"] > 2]) if ind_df is not None and not ind_df.empty else 0,
            "sector_concentration": _calc_concentration(ind_df) if ind_df is not None and not ind_df.empty else 0,
        }
    except Exception as e:
        logger.error(f"fetch_sector_data failed: {e}")
        return {
            "top_industry_sectors": [],
            "top_concept_sectors": [],
            "financial_tier": {"sec": 0, "multi_fin": 0, "bank": 0},
            "hot_sector_count": 0,
            "sector_concentration": 0,
        }


def _calc_concentration(sectors) -> float:
    """计算板块集中度（前五占比）— 接受 list 或 DataFrame"""
    try:
        if sectors is None:
            return 0
        if isinstance(sectors, list):
            if not sectors:
                return 0
            top5 = sectors[:5]
            top_sum = sum(s.get("涨跌幅", 0) for s in top5)
            all_sum = sum(abs(s.get("涨跌幅", 0)) for s in sectors)
            return round(top_sum / max(1, all_sum), 3)
        # DataFrame
        if sectors.empty:
            return 0
        top3_change = sectors.head(3)["涨跌幅"].sum()
        total_change = sectors["涨跌幅"].sum()
        if total_change == 0:
            return 0
        return round(abs(top3_change / total_change), 3)
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════
# 四、主力资金流向
# ═══════════════════════════════════════════════════════

def fetch_main_flow() -> Dict[str, Any]:
    """获取主力资金流向（直连新浪：成交额×涨跌幅近似）"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot()
        if df is None or df.empty:
            return {"main_net_flow": 0, "main_net_pct": 0, "top_flow_sectors": [], "top_flow_stocks": []}

        # 资金近似 = 成交额 × 涨跌幅 / 100
        df = df.copy()
        df["资金近似"] = df["成交额"] * df["涨跌幅"] / 100
        main_net = float(df["资金近似"].sum())

        top_stocks = df.nlargest(20, "资金近似")[[
            "代码", "名称", "最新价", "涨跌幅", "成交额", "资金近似"
        ]].to_dict("records")

        return {
            "main_net_flow": round(main_net / 1e8, 2),
            "main_net_pct": round((df["涨跌幅"] > 0).mean() * 100, 2),
            "top_flow_sectors": [],
            "top_flow_stocks": top_stocks,
        }
    except Exception as e:
        logger.error(f"fetch_main_flow failed: {e}")
        return {"main_net_flow": 0, "main_net_pct": 0, "top_flow_sectors": [], "top_flow_stocks": []}


# ═══════════════════════════════════════════════════════
# 五、广度（上涨家数）
# ═══════════════════════════════════════════════════════

def fetch_breadth() -> Dict[str, Any]:
    """获取市场广度（直连新浪全市场，本地计算）"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot()
        if df is None or df.empty:
            return {"total": 0, "rise": 0, "fall": 0, "flat": 0, "breadth": 0,
                    "breadth_ratio": 50, "rise_fall_ratio": 1.0,
                    "zt": 0, "dt": 0}

        # 过滤 ST 和停牌（成交量 < 1000 手）
        df = df[(df["名称"].str.contains("ST|退", na=False) == False) & (df["成交量"] > 1000)]

        rise = int((df["涨跌幅"] > 0).sum())
        fall = int((df["涨跌幅"] < 0).sum())
        flat = int((df["涨跌幅"] == 0).sum())
        total = rise + fall + flat

        # 涨停：主板 ≥9.5（10cm），创业板/科创板/北交所 ≥19.5（20cm）
        zt = int(((df["涨跌幅"] >= 9.5) & (df["涨跌幅"] < 19.5)).sum() +
                 (df["涨跌幅"] >= 19.5).sum())
        dt = int(((df["涨跌幅"] <= -9.5) & (df["涨跌幅"] > -19.5)).sum() +
                 (df["涨跌幅"] <= -19.5).sum())

        breadth_ratio = round(rise / max(1, total) * 100, 1)
        rise_fall_ratio = round(rise / max(1, fall), 2)

        return {
            "total": total,
            "rise": rise,
            "fall": fall,
            "flat": flat,
            "breadth": rise,
            "breadth_ratio": breadth_ratio,
            "rise_fall_ratio": rise_fall_ratio,
            "zt": zt,
            "dt": dt,
        }
    except Exception as e:
        logger.error(f"fetch_breadth failed: {e}")
        return {"total": 0, "rise": 0, "fall": 0, "flat": 0, "breadth": 0,
                "breadth_ratio": 50, "rise_fall_ratio": 1.0,
                "zt": 0, "dt": 0}


# ═══════════════════════════════════════════════════════
# 六、连板股池
# ═══════════════════════════════════════════════════════

def fetch_lianban_pool() -> List[Dict]:
    """获取连板股池"""
    try:
        import akshare as ak
        today = datetime.now().strftime("%Y%m%d")

        try:
            zt_df = ak.stock_zt_pool_em(date=today)
            # 简单处理：取涨停池中成交额较大、换手率较高的
            if not zt_df.empty:
                zt_df = zt_df.sort_values("成交额", ascending=False)
                result = zt_df.head(30).rename(columns={
                    "代码": "code", "名称": "name", "涨停统计": "zt_days",
                    "连板数": "lianban_days"
                }).to_dict("records")
                return result
        except Exception:
            pass

        return []
    except Exception as e:
        logger.error(f"fetch_lianban_pool failed: {e}")
        return []


# ═══════════════════════════════════════════════════════
# 七、完整市场快照（并行采集）
# ═══════════════════════════════════════════════════════

def fetch_full_snapshot() -> Dict[str, Any]:
    """
    单次拉取全市场数据（直连新浪 stock_zh_a_spot），所有指标本地计算。
    避免 5 次独立调用的 23s × 5 = 115s 累积。
    """
    import akshare as ak

    snapshot = {
        "snapshot_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade_date": get_today_str(),
    }

    try:
        # 1. 全市场数据（23s，新浪直连，不需代理）
        t0 = time.time()
        all_df = ak.stock_zh_a_spot()
        logger.info(f"snapshot: stock_zh_a_spot took {time.time()-t0:.1f}s, {len(all_df)} rows")
        if all_df is None or all_df.empty:
            return snapshot

        # 过滤 ST 和停牌
        active_df = all_df[
            (all_df["名称"].str.contains("ST|退", na=False) == False) &
            (all_df["成交量"] > 1000)
        ].copy()

        # 2. 指数（新浪直连 3.5s，可与全市场并行）
        t0 = time.time()
        try:
            idx_df = ak.stock_zh_index_spot_sina()
            logger.info(f"snapshot: index took {time.time()-t0:.1f}s")
        except Exception as e:
            logger.error(f"snapshot: index failed: {e}")
            idx_df = None

        for key, name in [("shanghai", "上证指数"), ("chuangye", "创业板指"),
                          ("shenzhen", "深证成指"), ("kechuang", "科创50"), ("hs300", "沪深300")]:
            try:
                if idx_df is not None and not idx_df.empty:
                    row = idx_df[idx_df["名称"] == name]
                    if not row.empty:
                        snapshot[key] = {
                            "name": name,
                            "price": float(row["最新价"].values[0]),
                            "change_pct": float(row["涨跌幅"].values[0]),
                        }
                    else:
                        snapshot[key] = {"name": name, "price": 0, "change_pct": 0}
                else:
                    snapshot[key] = {"name": name, "price": 0, "change_pct": 0}
            except Exception:
                snapshot[key] = {"name": name, "price": 0, "change_pct": 0}

        snapshot["shanghai_close"] = snapshot["shanghai"].get("price", 0)
        snapshot["shanghai_change_pct"] = snapshot["shanghai"].get("change_pct", 0)
        snapshot["chuangye_close"] = snapshot["chuangye"].get("price", 0)
        snapshot["chuangye_change_pct"] = snapshot["chuangye"].get("change_pct", 0)

        # 3. 涨停/跌停本地计算
        is_zt_10 = (active_df["涨跌幅"] >= 9.5) & (active_df["涨跌幅"] < 19.5)
        is_zt_20 = active_df["涨跌幅"] >= 19.5
        zt_mask = is_zt_10 | is_zt_20
        snapshot["zt_count"] = int(zt_mask.sum())
        snapshot["zt_codes"] = active_df.loc[zt_mask, "代码"].tolist()[:30]
        is_dt_10 = (active_df["涨跌幅"] <= -9.5) & (active_df["涨跌幅"] > -19.5)
        is_dt_20 = active_df["涨跌幅"] <= -19.5
        dt_mask = is_dt_10 | is_dt_20
        snapshot["dt_count"] = int(dt_mask.sum())
        snapshot["break_count"] = 0  # 需要昨日数据，暂用 0
        snapshot["break_rate"] = 0.0

        # 4. 广度
        rise = int((active_df["涨跌幅"] > 0).sum())
        fall = int((active_df["涨跌幅"] < 0).sum())
        flat = int((active_df["涨跌幅"] == 0).sum())
        snapshot["breadth"] = rise
        snapshot["breadth_ratio"] = round(rise / max(1, rise + fall + flat) * 100, 1)
        snapshot["rise_fall_ratio"] = round(rise / max(1, fall), 2)

        # 5. 资金流近似（成交额 × 涨跌幅）
        active_df["资金近似"] = active_df["成交额"] * active_df["涨跌幅"] / 100
        snapshot["main_net_flow"] = round(float(active_df["资金近似"].sum()) / 1e8, 2)
        top_stocks = active_df.nlargest(20, "资金近似")[[
            "代码", "名称", "最新价", "涨跌幅", "成交额"
        ]].to_dict("records")
        snapshot["top_flow_stocks"] = top_stocks

        # 6. 板块（新浪 stock_sector_spot 直连）
        t0 = time.time()
        try:
            sec_df = ak.stock_sector_spot()
            logger.info(f"snapshot: sectors took {time.time()-t0:.1f}s, {len(sec_df)} rows")
            if sec_df is not None and not sec_df.empty:
                sec_df = sec_df.sort_values("涨跌幅", ascending=False)
                top_sectors = []
                for _, r in sec_df.iterrows():
                    top_sectors.append({
                        "板块代码": r.get("label", ""),
                        "板块名称": r.get("板块", ""),
                        "涨跌幅": float(r.get("涨跌幅", 0) or 0),
                        "公司家数": int(r.get("公司家数", 0) or 0),
                        "领涨股票": r.get("股票名称", ""),
                        "领涨股票代码": r.get("股票代码", ""),
                        "领涨股票-涨跌幅": float(r.get("个股-涨跌幅", 0) or 0),
                        "总成交额": float(r.get("总成交额", 0) or 0),
                    })
                snapshot["top_industry_sectors"] = top_sectors[:30]
            else:
                snapshot["top_industry_sectors"] = []
        except Exception as e:
            logger.error(f"snapshot: sectors failed: {e}")
            snapshot["top_industry_sectors"] = []

        # 金融三级表（证券/保险/银行）
        sec_strength = 0.0
        multi_fin_strength = 0.0
        bank_strength = 0.0
        for s in snapshot["top_industry_sectors"]:
            name = s.get("板块名称", "")
            chg = s.get("涨跌幅", 0)
            if "证券" in name and sec_strength == 0:
                sec_strength = chg
            if ("多元金融" in name or "保险" in name) and multi_fin_strength == 0:
                multi_fin_strength = chg
            if "银行" in name and bank_strength == 0:
                bank_strength = chg
        snapshot["financial_tier"] = {
            "sec": sec_strength,
            "multi_fin": multi_fin_strength,
            "bank": bank_strength,
        }
        snapshot["hot_sector_count"] = len([s for s in snapshot["top_industry_sectors"]
                                           if s.get("涨跌幅", 0) > 2])
        snapshot["sector_concentration"] = _calc_concentration(snapshot["top_industry_sectors"])

        # 概念板块（SW 三级行业，1.5s 直连）
        try:
            sw3 = ak.sw_index_third_info()
            if sw3 is not None and not sw3.empty:
                snapshot["top_concept_sectors"] = sw3.head(20).to_dict("records")
            else:
                snapshot["top_concept_sectors"] = []
        except Exception:
            snapshot["top_concept_sectors"] = []

        # 把全市场数据存为临时缓存，给 fetch_sector_top_stocks 等复用
        snapshot["_all_stocks_cache"] = active_df.to_dict("records")

        return snapshot
    except Exception as e:
        logger.error(f"fetch_full_snapshot failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return snapshot


# ═══════════════════════════════════════════════════════
# 八、个股详情查询
# ═══════════════════════════════════════════════════════

def fetch_stock_detail(code: str) -> Dict[str, Any]:
    """查询单只股票详情"""
    try:
        import akshare as ak

        if code.startswith("6"):
            market = "sh"
        else:
            market = "sz"

        symbol = f"{market}{code}"
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return {}

        r = row.iloc[0]
        return {
            "code": code,
            "name": r.get("名称", ""),
            "price": float(r.get("最新价", 0) or 0),
            "change_pct": float(r.get("涨跌幅", 0) or 0),
            "volume": float(r.get("成交量", 0) or 0),
            "amount": float(r.get("成交额", 0) or 0),
            "turnover_rate": float(r.get("换手率", 0) or 0),
            "amplitude": float(r.get("振幅", 0) or 0),
            "high": float(r.get("最高", 0) or 0),
            "low": float(r.get("最低", 0) or 0),
            "open": float(r.get("今开", 0) or 0),
            "prev_close": float(r.get("昨收", 0) or 0),
            "volume_ratio": float(r.get("量比", 0) or 0),
            "main_net": float(r.get("主力净流入", 0) or 0) / 1e4,
        }
    except Exception as e:
        logger.error(f"fetch_stock_detail {code} failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════
# 九、历史K线（用于回测）
# ═══════════════════════════════════════════════════════

def fetch_historical_kline(code: str, days: int = 250) -> List[Dict]:
    """获取历史K线（用于回测）"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                 start_date="20230101",
                                 end_date=datetime.now().strftime("%Y%m%d"),
                                 adjust="qfq")
        df = df.tail(days)
        return df.to_dict("records")
    except Exception as e:
        logger.error(f"fetch_historical_kline {code} failed: {e}")
        return []


# ═══════════════════════════════════════════════════════
# 十、板块成分股龙头挖掘（主升浪细分）
# ═══════════════════════════════════════════════════════

def fetch_sector_top_stocks(sector_code_or_label: str, top_n: int = 5) -> List[Dict]:
    """
    挖板块的成分股龙头（直连模式）：
    用板块名做关键词，在全市场数据中匹配同行业股票。
    不依赖东财板块成分股接口（被 GFW 拦）。
    返回: [{code, name, price, change_pct, turnover_rate, amount, is_zt, is_dt}, ...]
    """
    try:
        # 优先从 snapshot 缓存拿全市场数据
        all_stocks = _get_all_stocks_cache()

        if not all_stocks:
            # 缓存未命中（如 sector-leaders 单接口调用），单独拉一次
            import akshare as ak
            df = ak.stock_zh_a_spot()
            if df is None or df.empty:
                return []
            all_stocks = df.to_dict("records")

        # 把 sector_code_or_label 转换成板块中文名
        sector_name = sector_code_or_label
        if sector_code_or_label.startswith("new_"):
            # 查 stock_sector_spot 的 label→中文映射
            try:
                import akshare as ak
                sec_df = ak.stock_sector_spot()
                row = sec_df[sec_df["label"] == sector_code_or_label]
                if not row.empty:
                    sector_name = row.iloc[0]["板块"]
            except Exception:
                pass

        # 提取板块关键词做匹配
        keywords = _extract_sector_keywords(sector_name)
        if not keywords:
            return []

        # 在全市场匹配
        results = []
        for r in all_stocks:
            name = str(r.get("名称", ""))
            if not name:
                continue
            try:
                change_pct = float(r.get("涨跌幅", 0) or 0)
                price = float(r.get("最新价", 0) or 0)
                amount = float(r.get("成交额", 0) or 0)
            except (ValueError, TypeError):
                continue

            # 关键词匹配（任一关键词命中即视为同板块）
            if not any(kw in name for kw in keywords):
                continue

            # 过滤：剔除新股首日（涨幅>30%异常）、停牌股（成交额<100万）
            if abs(change_pct) > 30:
                continue
            if amount < 1e6:
                continue

            # 标记涨停/跌停
            is_zt = change_pct >= 9.5
            is_dt = change_pct <= -9.5

            # 新浪没有换手率字段，用"成交额/成交量"近似
            try:
                volume = float(r.get("成交量", 0) or 0)
                turnover_rate = round(amount / volume * 100, 2) if volume > 0 else 0
            except Exception:
                turnover_rate = 0

            results.append({
                "code": str(r.get("代码", "")),
                "name": name,
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "turnover_rate": turnover_rate,
                "amount": round(amount / 1e8, 2),
                "is_zt": is_zt,
                "is_dt": is_dt,
            })

        # 排序：先涨停 > 涨幅 > 换手率
        results.sort(key=lambda x: (
            not x["is_zt"],
            -x["change_pct"],
            -x["turnover_rate"],
        ))
        return results[:top_n]
    except Exception as e:
        logger.error(f"fetch_sector_top_stocks {sector_code_or_label} failed: {e}")
        return []


def _extract_sector_keywords(sector_name: str) -> List[str]:
    """从板块名提取关键词用于全市场匹配。
    例："激光设备" -> ["激光", "设备", "激光设备"]
    例："化纤行业" -> ["化纤", "化纤行业"]  （去掉"行业"后缀）
    例："金融行业" -> ["金融", "金融行业"]
    """
    name = sector_name.strip()
    if not name:
        return []

    # 去除通用后缀
    suffixes = ["行业", "板块", "概念", "板块"]
    clean = name
    for s in suffixes:
        if clean.endswith(s):
            clean = clean[:-len(s)]
            break

    keywords = set()

    # 整体名（最准）
    if clean:
        keywords.add(clean)
    if name != clean:
        keywords.add(name)  # 也保留原始全名

    # 拆 2 字关键词（按从左到右）
    for i in range(len(clean) - 1):
        kw = clean[i:i+2]
        if len(kw) == 2 and kw.strip():
            keywords.add(kw)

    # 过滤明显的无效词
    stop = {"的", "了", "是", "在", "和", "与", "或"}
    keywords = {k for k in keywords if k not in stop and len(k) >= 2}

    return list(keywords)[:8]


# 模块级缓存：fetch_full_snapshot 调一次，所有接口复用
_ALL_STOCKS_CACHE = {"data": None, "fetched_at": None}
_CACHE_TTL_SECONDS = 90  # 1.5 分钟

def _get_all_stocks_cache():
    """获取全市场数据缓存（90s TTL）"""
    if _ALL_STOCKS_CACHE["data"] is None:
        return None
    age = (datetime.now() - _ALL_STOCKS_CACHE["fetched_at"]).total_seconds()
    if age > _CACHE_TTL_SECONDS:
        return None
    return _ALL_STOCKS_CACHE["data"]

def _set_all_stocks_cache(records):
    _ALL_STOCKS_CACHE["data"] = records
    _ALL_STOCKS_CACHE["fetched_at"] = datetime.now()


def fetch_main_line_leaders(top_n_sectors: int = 5, leaders_per_sector: int = 3) -> Dict:
    """
    取 Top N 主线板块 + 每板块 top K 龙头股。
    走直连新浪数据（不需代理）。
    """
    try:
        import akshare as ak

        # 1. 板块涨幅榜（新浪直连 0.2s）
        sec_df = ak.stock_sector_spot()
        if sec_df is None or sec_df.empty:
            return {"fetched_at": "", "leaders": [], "total_sectors": 0, "total_stocks": 0}

        sec_df = sec_df.sort_values("涨跌幅", ascending=False)
        top_sectors = sec_df.head(top_n_sectors)

        # 2. 全市场数据（23s，但只调一次，写入缓存）
        all_stocks = _get_all_stocks_cache()
        if all_stocks is None:
            all_df = ak.stock_zh_a_spot()
            if all_df is not None and not all_df.empty:
                # 过滤 ST 和停牌
                all_df = all_df[
                    (all_df["名称"].str.contains("ST|退", na=False) == False) &
                    (all_df["成交量"] > 1000)
                ]
                all_stocks = all_df.to_dict("records")
                _set_all_stocks_cache(all_stocks)

        if not all_stocks:
            return {"fetched_at": "", "leaders": [], "total_sectors": 0, "total_stocks": 0}

        leaders_list = []
        for _, sec in top_sectors.iterrows():
            sector_label = sec.get("label", "")
            sector_name = sec.get("板块", "")
            sector_chg = float(sec.get("涨跌幅", 0) or 0)

            if not sector_label:
                continue

            # 关键词匹配
            keywords = _extract_sector_keywords(sector_name)
            if not keywords:
                continue

            candidates = []
            for r in all_stocks:
                name = str(r.get("名称", ""))
                if not name or not any(kw in name for kw in keywords):
                    continue
                try:
                    change_pct = float(r.get("涨跌幅", 0) or 0)
                    amount = float(r.get("成交额", 0) or 0)
                except (ValueError, TypeError):
                    continue

                if abs(change_pct) > 30 or amount < 1e6:
                    continue

                is_zt = change_pct >= 9.5
                try:
                    volume = float(r.get("成交量", 0) or 0)
                    turnover_rate = round(amount / volume * 100, 2) if volume > 0 else 0
                except Exception:
                    turnover_rate = 0

                candidates.append({
                    "code": str(r.get("代码", "")),
                    "name": name,
                    "price": round(float(r.get("最新价", 0) or 0), 2),
                    "change_pct": round(change_pct, 2),
                    "turnover_rate": turnover_rate,
                    "amount": round(amount / 1e8, 2),
                    "is_zt": is_zt,
                    "is_dt": change_pct <= -9.5,
                })

            # 排序：涨停 > 涨幅 > 换手
            candidates.sort(key=lambda x: (
                not x["is_zt"],
                -x["change_pct"],
                -x["turnover_rate"],
            ))
            top_stocks = candidates[:leaders_per_sector]
            if top_stocks:
                leaders_list.append({
                    "sector_name": sector_name,
                    "sector_code": sector_label,
                    "sector_change_pct": sector_chg,
                    "leaders": top_stocks,
                })

        return {
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "leaders": leaders_list,
            "total_sectors": len(leaders_list),
            "total_stocks": sum(len(x["leaders"]) for x in leaders_list),
        }
    except Exception as e:
        logger.error(f"fetch_main_line_leaders failed: {e}")
        return {"fetched_at": "", "leaders": [], "total_sectors": 0, "total_stocks": 0}

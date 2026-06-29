"""
信号引擎 — 超哥交易方法论核心
住相五维破裂检测 + 金融三级表 + 执念六阶段量化
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("info-hub.signal")

# ═══════════════════════════════════════════════════════
# 一、住相五维破裂检测
# ═══════════════════════════════════════════════════════

class ZhuxiangDetector:
    """住相五维破裂检测器"""

    # 量化阈值（可配置）
    THRESHOLDS = {
        "zt_count_weak": 30,          # 涨停数 < 30 → 龙头乏力
        "break_rate_danger": 0.40,    # 炸板率 > 40% → 龙头乏力
        "rise_fall_ratio_danger": 0.5, # 涨跌比 < 0.5 → 跟风先跑
        "hot_sector_min": 5,           # 热门板块 < 5 → 扩散停止
        "concentration_max": 0.70,     # 集中度 > 70% → 扩散停止
        "zt_index_divergence": 30,     # 指数涨但涨停 < 30 → 情绪背离
        "main_net_outflow": 100,       # 主力净流出 > 100亿 → 资金转向
    }

    def __init__(self, market_data: Dict[str, Any]):
        self.data = market_data

    def check(self) -> Tuple[List[str], Dict[str, bool], int]:
        """
        返回：
        - lit_signals: 点亮的信号列表
        - signal_flags: {信号名: True/False}
        - signal_count: 点亮数量
        """
        zt_count = self.data.get("zt_count", 0)
        break_rate = self.data.get("break_rate", 0)
        rise_fall_ratio = self.data.get("rise_fall_ratio", 1.0)
        hot_sectors = self.data.get("hot_sector_count", 99)
        concentration = self.data.get("sector_concentration", 0)
        shs_change = self.data.get("shanghai_change_pct", 0)
        main_net_flow = self.data.get("main_net_flow", 0)

        flags = {}

        # 1. 龙头乏力
        flags["龙头乏力"] = (
            zt_count < self.THRESHOLDS["zt_count_weak"] or
            break_rate > self.THRESHOLDS["break_rate_danger"]
        )

        # 2. 跟风先跑
        flags["跟风先跑"] = rise_fall_ratio < self.THRESHOLDS["rise_fall_ratio_danger"]

        # 3. 扩散停止
        flags["扩散停止"] = (
            hot_sectors < self.THRESHOLDS["hot_sector_min"] or
            concentration > self.THRESHOLDS["concentration_max"]
        )

        # 4. 情绪背离
        flags["情绪背离"] = (
            shs_change > 0.5 and zt_count < self.THRESHOLDS["zt_index_divergence"]
        )

        # 5. 资金转向
        flags["资金转向"] = main_net_flow < -self.THRESHOLDS["main_net_outflow"]

        lit = [k for k, v in flags.items() if v]
        return lit, flags, len(lit)


# ═══════════════════════════════════════════════════════
# 二、金融三级表
# ═══════════════════════════════════════════════════════

class FinancialTierDetector:
    """金融三级表 — 大盘情绪快判"""

    def __init__(self, sector_data: Dict[str, Any]):
        self.data = sector_data

    def check(self) -> Tuple[str, str, str]:
        """
        返回：
        - tier: 't1_证券' / 't2_多元金融' / 't3_银行' / 't3_防御' / 't123_牛市'
        -定性: 中文定性描述
        - 策略: 策略建议
        """
        sec_strength = self.data.get("sec", 0)           # 证券板块强度
        multi_strength = self.data.get("multi_fin", 0)    # 多元金融
        bank_strength = self.data.get("bank", 0)          # 银行
        zt_count = self.data.get("zt_count", 0)

        STRONG_THRESHOLD = 1.0   # 涨幅 > 1% 视为走强

        results = []
        if sec_strength > STRONG_THRESHOLD:
            results.append("sec")
        if multi_strength > STRONG_THRESHOLD:
            results.append("multi_fin")
        if bank_strength > STRONG_THRESHOLD:
            results.append("bank")

        if len(results) == 3:
            return "t123_牛市", "流动性泛滥（牛市）", "满仓进攻"
        elif "sec" in results:
            return "t1_证券", "大进攻行情", "重仓进攻，追主线龙"
        elif "multi_fin" in results:
            return "t2_多元金融", "小突破行情", "轻仓跟进，做独立龙"
        elif "bank" in results:
            return "t3_防御", "纯防御行情", "空仓观望"
        else:
            return "t3_防御", "无明显方向", "轻仓观望，缩短周期"


# ═══════════════════════════════════════════════════════
# 三、执念六阶段判断
# ═══════════════════════════════════════════════════════

class ObsessionPhaseDetector:
    """执念六阶段 — 量化定位"""

    PHASES = [
        "少数先知期",
        "机构试错期",
        "游资点火期",
        "散户共识期",
        "全民住相期",
        "派发期",
    ]

    def __init__(self, market_data: Dict[str, Any], zhuxiang_count: int = 0):
        self.data = market_data
        self.zhuxiang_count = zhuxiang_count

    def detect(self) -> Tuple[str, str, str]:
        """
        返回：
        - phase: 阶段名
        - label: 中文标签
        - action: 操作建议
        """
        zt = self.data.get("zt_count", 0)
        breadth = self.data.get("breadth", 0)
        lianban_count = self.data.get("lianban_count", 0)
        market_cap_leader = self.data.get("top_market_cap_leader", False)
        shs_change = self.data.get("shanghai_change_pct", 0)
        breadth_ratio = self.data.get("breadth_ratio", 0)
        break_rate = self.data.get("break_rate", 0)

        # 派发期信号：住相 ≥ 3 或者 龙头横盘 + 小票乱舞
        if self.zhuxiang_count >= 3:
            return "派发期", "⚠️ 住相破裂信号激活", "清仓走人，借人性出货"

        # 全面高潮：涨停极多 + 广度极宽 + 连板多
        if zt >= 80 and breadth >= 3000 and lianban_count >= 15:
            return "全民住相期", "🔥 全民看多，叙事固化", "最危险阶段，准备下车"

        # 散户共识：涨停中高 + 广度宽 + 换手率高
        if zt >= 50 and breadth >= 2500 and self.data.get("avg_turnover_rate", 0) > 5:
            return "散户共识期", "📢 讨论激增，后排泛滥", "成本高，开始警惕，持有前排"

        # 游资点火：涨停有量 + 板块扩散 + 龙头辨识度高
        if zt >= 30 and breadth >= 2000 and lianban_count >= 8 and shs_change > 1.0:
            return "游资点火期", "⚡ 龙头打出辨识度", "可见赚钱效应，可加仓前排"

        # 机构试错：涨停有一定 + 广度尚可 + 研报出现
        if zt >= 20 and breadth >= 1500 and self.data.get("research_count", 0) > 5:
            return "机构试错期", "🏛️ 中军放量，机构试探", "龙头+2只跟风，试仓 5-10%"

        # 少数先知：涨停少 + 广度低 + 板块集中
        return "少数先知期", "🌱 筹码便宜，逻辑初现", "最难买也最值得买，轻仓试"

    def get_position_limit(self) -> int:
        """根据阶段返回仓位上限（%）"""
        phase = self.detect()[0]
        limits = {
            "少数先知期": 30,
            "机构试错期": 50,
            "游资点火期": 80,
            "散户共识期": 70,
            "全民住相期": 40,
            "派发期": 0,
        }
        return limits.get(phase, 30)


# ═══════════════════════════════════════════════════════
# 四、确信度评分
# ═══════════════════════════════════════════════════════

class ConfidenceScorer:
    """确信度评分 — 综合评估交易机会"""

    def __init__(self, market_data: Dict[str, Any], zhuxiang_count: int,
                 phase: str, fin_tier: str):
        self.data = market_data
        self.zhuxiang_count = zhuxiang_count
        self.phase = phase
        self.fin_tier = fin_tier

    def score(self) -> Tuple[int, str, Dict[str, Any]]:
        """
        返回：
        - total_score: 总分 (0-100)
        - grade: A/B/C/D
        - breakdown: 分项得分
        """
        breakdown = {}

        # 执念阶段适配 25%
        phase_scores = {
            "少数先知期": 60,
            "机构试错期": 80,
            "游资点火期": 95,
            "散户共识期": 70,
            "全民住相期": 40,
            "派发期": 10,
        }
        breakdown["执念阶段适配"] = phase_scores.get(self.phase, 0)

        # 住相信号安全 25%
        zhuxiang_scores = {
            0: 95, 1: 80, 2: 60, 3: 30, 4: 10, 5: 0
        }
        breakdown["住相信号安全"] = zhuxiang_scores.get(self.zhuxiang_count, 0)

        # STW温度匹配 20%
        fin_scores = {
            "t123_牛市": 95, "t1_证券": 80, "t2_多元金融": 60,
            "t3_防御": 20
        }
        breakdown["STW温度匹配"] = fin_scores.get(self.fin_tier, 20)

        # 广度验证 15%
        breadth = self.data.get("breadth", 0)
        if breadth >= 3000:
            breadth_score = 95
        elif breadth >= 2500:
            breadth_score = 80
        elif breadth >= 1500:
            breadth_score = 50
        elif breadth >= 800:
            breadth_score = 30
        else:
            breadth_score = 10
        breakdown["广度验证"] = breadth_score

        # 板块结构 15%
        zt = self.data.get("zt_count", 0)
        lianban = self.data.get("lianban_count", 0)
        if zt >= 50 and lianban >= 10:
            sector_score = 90
        elif zt >= 30 and lianban >= 5:
            sector_score = 70
        elif zt >= 20:
            sector_score = 50
        else:
            sector_score = 20
        breakdown["板块结构"] = sector_score

        # 加权总分
        total = (
            breakdown["执念阶段适配"] * 0.25 +
            breakdown["住相信号安全"] * 0.25 +
            breakdown["STW温度匹配"] * 0.20 +
            breakdown["广度验证"] * 0.15 +
            breakdown["板块结构"] * 0.15
        )
        total_int = int(total)

        if total_int >= 78:
            grade = "A"
        elif total_int >= 60:
            grade = "B"
        elif total_int >= 40:
            grade = "C"
        else:
            grade = "D"

        return total_int, grade, breakdown


# ═══════════════════════════════════════════════════════
# 五、顶层信号分析器
# ═══════════════════════════════════════════════════════

class SignalEngine:
    """顶层信号分析器 — 整合所有模块"""

    def __init__(self, market_data: Dict[str, Any], sector_data: Dict[str, Any]):
        self.market_data = market_data
        self.sector_data = sector_data

    def analyze(self) -> Dict[str, Any]:
        """执行完整信号分析"""
        # 1. 住相五维
        zhuxiang = ZhuxiangDetector(self.market_data)
        lit_signals, signal_flags, signal_count = zhuxiang.check()

        # 2. 执念阶段
        obsession = ObsessionPhaseDetector(self.market_data, signal_count)
        phase, phase_label, action = obsession.detect()
        position_limit = obsession.get_position_limit()

        # 3. 金融三级表
        fin_detector = FinancialTierDetector(self.sector_data)
        fin_tier, fin定性, fin_strategy = fin_detector.check()

        # 4. 确信度评分
        scorer = ConfidenceScorer(self.market_data, signal_count, phase, fin_tier)
        total_score, grade, breakdown = scorer.score()

        # 5. 综合动作
        final_action = self._merge_action(action, fin_strategy, grade, signal_count)

        # 6. 市场状态
        market_status = self._judge_market_status(
            fin_tier, self.market_data.get("breadth", 0), signal_count
        )

        return {
            "signal_count": signal_count,
            "lit_signals": lit_signals,
            "signal_flags": signal_flags,
            "obsession_phase": phase,
            "phase_label": phase_label,
            "phase_action": action,
            "position_limit_pct": position_limit,
            "financial_tier": fin_tier,
            "financial定性": fin定性,
            "financial_strategy": fin_strategy,
            "confidence_score": total_score,
            "confidence_grade": grade,
            "confidence_breakdown": breakdown,
            "market_status": market_status,
            "final_action": final_action,
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _judge_market_status(self, fin_tier: str, breadth: int, signal_count: int) -> str:
        """判断市场状态"""
        if signal_count >= 4:
            return "派发/高危"
        if fin_tier in ("t123_牛市", "t1_证券") and breadth >= 2500 and signal_count <= 1:
            return "主线行情"
        if fin_tier == "t2_多元金融" and breadth >= 1500:
            return "独立龙头"
        return "震荡防御"

    def _merge_action(self, phase_action: str, fin_action: str,
                      grade: str, signal_count: int) -> str:
        """合并两套动作建议"""
        if signal_count >= 4:
            return "⚠️ 强制清仓，住相破裂"
        if grade == "D":
            return "❌ D档，不参与"
        if grade == "C":
            return "👀 C档，观望"
        # A/B 档以阶段动作为主
        return phase_action


# ═══════════════════════════════════════════════════════
# 六、持仓信号检查
# ═══════════════════════════════════════════════════════

def check_position_signals(positions: List[Dict], market_data: Dict) -> List[Dict]:
    """
    对持仓逐只检查住相破裂信号
    返回每只票的状态和建议
    """
    zhuxiang = ZhuxiangDetector(market_data)
    _, flags, count = zhuxiang.check()

    results = []
    for pos in positions:
        stock_code = pos.get("stock_code", "")
        current_price = pos.get("current_price", 0)
        avg_cost = pos.get("avg_cost", 0)
        stop_loss = pos.get("stop_loss_price", avg_cost * 0.85)

        profit_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

        # 个股止损检查
        action = "持有"
        urgent = False

        if current_price < stop_loss:
            action = "🚨 止损出局"
            urgent = True
        elif count >= 3:
            action = "⚠️ 住相破裂，减仓"
            urgent = True
        elif count >= 2:
            action = "👀 住相警告，控仓"
        elif profit_pct >= 15:
            action = "🎯 止盈目标，可分批"

        results.append({
            **pos,
            "profit_pct": round(profit_pct, 2),
            "signal_action": action,
            "urgent": urgent,
            "global_signal_count": count,
        })

    return results


# ═══════════════════════════════════════════════════════
# 七、买点信号（转强确认）
# ═══════════════════════════════════════════════════════

class BuySignalDetector:
    """买点信号 — 三种允许的跟随"""

    def check(self, stock_data: Dict, market_data: Dict) -> Dict[str, Any]:
        """
        检测是否符合三种允许买入条件：
        1. 主线龙头的首次确认
        2. 主线从龙头向中军扩散的确认
        3. 分歧后的回流确认
        """
        phase = ObsessionPhaseDetector(market_data, 0).detect()[0]
        zhuxiang_count = ZhuxiangDetector(market_data).check()[2]

        if zhuxiang_count >= 3:
            return {"allowed": False, "reason": "住相破裂，不买入", "tier": "X"}

        zt_days = stock_data.get("lianban_days", 0)
        turnover = stock_data.get("turnover_rate", 0)
        price_limit_active = stock_data.get("zt_active", False)
        sector_rank = stock_data.get("sector_rank", 99)
        sector_leader = stock_data.get("sector_leader", False)
        flow_rank = stock_data.get("main_flow_rank", 99)

        # 条件1：主线龙头首次确认
        if (
            phase in ("游资点火期", "机构试错期")
            and zt_days >= 1
            and sector_rank <= 5
            and flow_rank <= 20
        ):
            return {
                "allowed": True,
                "condition": "主线龙头首次确认",
                "tier": "A",
                "action": "竞价/开盘买入，首板或二板",
            }

        # 条件2：龙头向中军扩散
        if (
            phase == "游资点火期"
            and zt_days == 0
            and turnover >= 8
            and sector_rank <= 10
            and not sector_leader
        ):
            return {
                "allowed": True,
                "condition": "主线扩散至中军",
                "tier": "B",
                "action": "回调至MA5附近买入",
            }

        # 条件3：分歧后回流
        if (
            phase in ("散户共识期", "游资点火期")
            and zt_days >= 2
            and price_limit_active
            and flow_rank <= 10
        ):
            return {
                "allowed": True,
                "condition": "分歧后回流再封板",
                "tier": "B+",
                "action": "回封时买入，MA20止损",
            }

        return {
            "allowed": False,
            "reason": "不满足任一允许买入条件",
            "tier": "C",
            "phase": phase,
            "zt_days": zt_days,
        }

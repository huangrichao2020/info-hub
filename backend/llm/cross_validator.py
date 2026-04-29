"""
A股多视角交叉验证框架 (Cross-Validation Framework)

借鉴 GodMode ULTRAPLINIAN 多模型赛马思路：
同一市场数据，用5个独立视角并行分析，交叉验证找共识与分歧。

使用：
    from llm.cross_validator import CrossValidator
    validator = CrossValidator()
    result = validator.analyze(market_data)
"""

from __future__ import annotations

import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class PerspectiveResult:
    """单个视角的分析结果"""
    name: str
    verdict: str          # "看多" / "看空" / "中性" / "结构性机会"
    confidence: float     # 0.0 ~ 1.0
    reasoning: str        # 核心推理
    signals: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    timestamp: str
    consensus: str
    consensus_strength: float
    disagreements: List[Dict] = field(default_factory=list)
    perspective_results: List[PerspectiveResult] = field(default_factory=list)
    final_verdict: str = ""
    action_plan: str = ""


class CrossValidator:
    """A股多视角交叉验证器"""
    
    def __init__(self):
        self.perspectives = ["供需", "执念", "住相", "龙头", "宏观"]
    
    def analyze(self, market_data: Dict[str, Any]) -> CrossValidationResult:
        """执行多视角交叉验证"""
        results = []
        for p in self.perspectives:
            result = self._run_perspective(p, market_data)
            results.append(result)
        return self._cross_validate(results, market_data)
    
    def _run_perspective(self, name: str, data: Dict) -> PerspectiveResult:
        if name == "供需":
            return self._supply_demand(data)
        elif name == "执念":
            return self._obsession(data)
        elif name == "住相":
            return self._pattern(data)
        elif name == "龙头":
            return self._dragon_head(data)
        elif name == "宏观":
            return self._macro(data)
    
    def _supply_demand(self, data: Dict) -> PerspectiveResult:
        """供需视角：资金面 + 筹码供需"""
        volume = data.get("volume_change", 0)
        north_flow = data.get("north_flow", 0)
        limit_up = data.get("limit_up", 0)
        limit_down = data.get("limit_down", 0)
        
        signals = []
        risks = []
        
        if volume > 10:
            signals.append(f"放量{volume}%，增量资金入场")
        elif volume < -10:
            risks.append(f"缩量{abs(volume)}%，存量博弈加剧")
        
        if north_flow > 50:
            signals.append(f"北向大幅流入{north_flow}亿")
        elif north_flow < -50:
            risks.append(f"北向大幅流出{abs(north_flow)}亿")
        
        if limit_up > 80:
            signals.append(f"涨停{limit_up}家，赚钱效应好")
        if limit_down > 20:
            risks.append(f"跌停{limit_down}家，亏钱效应扩散")
        
        if len(signals) >= 2 and len(risks) <= 1:
            verdict, confidence = "看多", 0.75
        elif len(risks) >= 2 and len(signals) <= 1:
            verdict, confidence = "看空", 0.70
        else:
            verdict, confidence = "结构性机会", 0.55
        
        return PerspectiveResult(
            name="供需", verdict=verdict, confidence=confidence,
            reasoning=f"资金面{'偏多' if verdict == '看多' else '承压'}，"
                      f"涨停/跌停比={limit_up}/{limit_down}，成交量变化{volume}%",
            signals=signals, risks=risks,
        )
    
    def _obsession(self, data: Dict) -> PerspectiveResult:
        """执念视角：情绪周期 + 心理锚定"""
        sentiment = data.get("sentiment", "neutral")
        consecutive_ban = data.get("consecutive_ban", 0)
        yesterday_premium = data.get("yesterday_premium", 0)
        
        signals = []
        risks = []
        
        if consecutive_ban >= 7:
            signals.append(f"{consecutive_ban}连板打开高度")
            risks.append("高度板接近情绪极值，警惕退潮")
        elif consecutive_ban >= 4:
            signals.append(f"{consecutive_ban}连板，情绪修复中")
        else:
            risks.append(f"连板仅{consecutive_ban}板，情绪冰点")
        
        if yesterday_premium > 3:
            signals.append(f"昨日涨停溢价{yesterday_premium}%")
        elif yesterday_premium < -2:
            risks.append(f"昨日涨停倒亏{abs(yesterday_premium)}%")
        
        verdict_map = {
            "extreme_greed": "看空", "greed": "中性",
            "neutral": "结构性机会",
            "fear": "看多", "extreme_fear": "看多",
        }
        verdict = verdict_map.get(sentiment, "中性")
        confidence = 0.65 if sentiment in ("extreme_greed", "extreme_fear") else 0.50
        
        return PerspectiveResult(
            name="执念", verdict=verdict, confidence=confidence,
            reasoning=f"情绪周期处于{sentiment}状态，连板高度{consecutive_ban}",
            signals=signals, risks=risks,
        )
    
    def _pattern(self, data: Dict) -> PerspectiveResult:
        """住相视角：K线形态 + 量价关系"""
        index_trend = data.get("index_trend", "sideways")
        ma_alignment = data.get("ma_alignment", False)
        divergence = data.get("divergence", False)
        
        signals = []
        risks = []
        
        if index_trend == "up" and ma_alignment:
            signals.append("指数趋势向上+均线多头排列")
        elif index_trend == "down":
            risks.append("指数趋势向下")
        
        if divergence:
            risks.append("量价背离，上涨动能衰减")
        
        if index_trend == "up" and ma_alignment and not divergence:
            verdict, confidence = "看多", 0.70
        elif index_trend == "down" and divergence:
            verdict, confidence = "看空", 0.65
        else:
            verdict, confidence = "中性", 0.50
        
        return PerspectiveResult(
            name="住相", verdict=verdict, confidence=confidence,
            reasoning=f"指数趋势{index_trend}，均线{'多头' if ma_alignment else '紊乱'}，"
                      f"{'存在' if divergence else '无'}量价背离",
            signals=signals, risks=risks,
        )
    
    def _dragon_head(self, data: Dict) -> PerspectiveResult:
        """龙头视角：主线确认 + 梯队完整性"""
        main_theme = data.get("main_theme", "")
        theme_limit_up = data.get("theme_limit_up", 0)
        theme_tiers = data.get("theme_tiers", 0)
        dragon_head_status = data.get("dragon_head_status", "strong")
        
        signals = []
        risks = []
        
        if main_theme and theme_limit_up >= 5:
            signals.append(f"主线「{main_theme}」{theme_limit_up}家涨停")
        if theme_tiers >= 3:
            signals.append(f"梯队完整（{theme_tiers}层）")
        elif theme_tiers < 2:
            risks.append("梯队断层，主线持续性存疑")
        
        if dragon_head_status == "strong":
            signals.append("龙头强势，锚定效应强")
        elif dragon_head_status == "weak":
            risks.append("龙头走弱，主线可能切换")
        
        if main_theme and theme_limit_up >= 5 and theme_tiers >= 3:
            verdict, confidence = "结构性机会", 0.75
        elif not main_theme or theme_limit_up < 3:
            verdict, confidence = "看空", 0.60
        else:
            verdict, confidence = "中性", 0.55
        
        return PerspectiveResult(
            name="龙头", verdict=verdict, confidence=confidence,
            reasoning=f"主线「{main_theme or '未确认'}」，涨停{theme_limit_up}家，"
                      f"梯队{theme_tiers}层，龙头{dragon_head_status}",
            signals=signals, risks=risks,
        )
    
    def _macro(self, data: Dict) -> PerspectiveResult:
        """宏观视角：政策 + 外盘 + 汇率"""
        policy = data.get("policy", "neutral")
        us_market = data.get("us_market", "flat")
        exchange_rate = data.get("exchange_rate_change", 0)
        
        signals = []
        risks = []
        
        if policy == "positive":
            signals.append("政策面偏暖")
        elif policy == "negative":
            risks.append("政策面收紧")
        
        if us_market == "up":
            signals.append("隔夜美股上涨")
        elif us_market == "down":
            risks.append("隔夜美股下跌")
        
        if exchange_rate < -0.5:
            signals.append("人民币升值")
        elif exchange_rate > 0.5:
            risks.append("人民币贬值压力")
        
        if policy == "positive" and us_market == "up":
            verdict, confidence = "看多", 0.65
        elif policy == "negative" and us_market == "down":
            verdict, confidence = "看空", 0.60
        else:
            verdict, confidence = "中性", 0.50
        
        return PerspectiveResult(
            name="宏观", verdict=verdict, confidence=confidence,
            reasoning=f"政策{policy}，外盘{us_market}，汇率变化{exchange_rate}%",
            signals=signals, risks=risks,
        )
    
    def _cross_validate(self, results: List[PerspectiveResult], 
                        data: Dict) -> CrossValidationResult:
        """交叉验证：找共识、判分歧、出结论"""
        verdict_counts = {}
        for r in results:
            verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1
        
        consensus = max(verdict_counts, key=verdict_counts.get)
        consensus_strength = verdict_counts[consensus] / len(results)
        
        disagreements = []
        for r in results:
            if r.verdict != consensus:
                disagreements.append({
                    "perspective": r.name,
                    "verdict": r.verdict,
                    "reasoning": r.reasoning,
                })
        
        weights = {"看多": 1.0, "看空": -1.0, "中性": 0.0, "结构性机会": 0.5}
        weighted_score = sum(weights.get(r.verdict, 0) * r.confidence for r in results) / len(results)
        
        if consensus_strength >= 0.8:
            final = f"强烈{consensus}" if consensus in ("看多", "看空") else consensus
        elif consensus_strength >= 0.6:
            final = f"偏向{consensus}" if consensus in ("看多", "看空") else consensus
        else:
            final = "多空分歧大，观望为主"
        
        action = self._generate_action(final, disagreements)
        
        return CrossValidationResult(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            consensus=consensus,
            consensus_strength=consensus_strength,
            disagreements=disagreements,
            perspective_results=results,
            final_verdict=final,
            action_plan=action,
        )
    
    def _generate_action(self, verdict: str, disagreements: List[Dict]) -> str:
        if "强烈看多" in verdict:
            return "加大仓位，主线龙头优先，回避后排"
        elif "偏向看多" in verdict:
            return "逢低布局，控制仓位5-7成，关注分歧视角提示的风险"
        elif "强烈看空" in verdict:
            return "降低仓位至3成以下，防守为主，等待情绪冰点"
        elif "偏向看空" in verdict:
            return "收缩战线，持有现金，观察分歧点是否恶化"
        elif "多空分歧" in verdict:
            items = "、".join([f"{d['perspective']}提示的{d['verdict']}" 
                              for d in disagreements[:2]])
            return f"观望，等待分歧收敛。重点关注：{items}" if items else "观望，等待分歧收敛"
        else:
            return "结构性行情，轻仓参与主线，快进快出"

    def to_dict(self, result: CrossValidationResult) -> Dict[str, Any]:
        """将结果转为可序列化字典（供 API/JSON 输出）"""
        return {
            "timestamp": result.timestamp,
            "consensus": result.consensus,
            "consensus_strength": round(result.consensus_strength, 2),
            "final_verdict": result.final_verdict,
            "action_plan": result.action_plan,
            "disagreements": result.disagreements,
            "perspectives": [
                {
                    "name": r.name,
                    "verdict": r.verdict,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                    "signals": r.signals,
                    "risks": r.risks,
                }
                for r in result.perspective_results
            ],
        }

"""
Serenity 卡脖子 + Prism 三棱镜 分析器
集成自：
  - github.com/fadewalk/serenity-stock-choke
  - github.com/destiny520537work-lab/fate-skill

调用方式：
    from services.choke_point_analyzer import ChokePointAnalyzer, ThreeLensAnalyzer
    analyzer = ChokePointAnalyzer()
    result = analyzer.analyze("688146")  # 中船特气
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("info-hub.choke-point")

# Serenity 框架：已知 A 股卡脖子标的样本库
# 数据来源：knowhub/.../methodology/serenity-choke-point.md + 公开信息综合
# 维护说明：用 Mavis 手动补充新标的；高频标的写硬编码样本，低频用 ask_user 触发手工分析
KNOWN_CHOKE_POINTS: Dict[str, Dict[str, Any]] = {
    "603986": {  # 兆易创新
        "stock_name": "兆易创新",
        "supply_chain_position": "NOR Flash + 利基 DRAM",
        "choke_score": 8,
        "supplier_count": 3,  # 全球三巨头：华邦/旺宏/兆易
        "replacement_difficulty": 9,  # 45nm 量产 + 310 亿颗出货
        "expansion_cycle_months": 18,
        "big_capital_signal": "GIC + 葛卫东 + 博时重仓；机构密集调研",
        "exit_signal": "海外巨头回归利基 / 国内出现第二个兆易级别对手",
        "framework_judgment": "卡脖子逻辑成立",
        "confidence": 5,
        "source_url": "methodology/serenity-choke-point.md",
        "data_as_of": "2026-06-29",
    },
    "688146": {  # 中船特气
        "stock_name": "中船特气",
        "supply_chain_position": "六氟化钨（电子特气，用于先进制程/存储薄膜沉积）",
        "choke_score": 7,
        "supplier_count": 2,  # 国内能生产 6N 级以上企业极少
        "replacement_difficulty": 9,  # 钨粉成本占 60-70%，中国管制出口
        "expansion_cycle_months": 24,
        "big_capital_signal": "前期涨 813.75%，资金抱团；现特停核查",
        "exit_signal": "国产替代完成 / PE 573 倍估值回归",
        "framework_judgment": "卡脖子逻辑成立，但估值已严重透支",
        "confidence": 4,
        "source_url": "methodology/serenity-choke-point.md",
        "data_as_of": "2026-06-29",
    },
    "688498": {  # 源杰科技
        "stock_name": "源杰科技",
        "supply_chain_position": "CPO / EAM 激光器",
        "choke_score": 7,
        "supplier_count": 3,  # CPO 激光器全球少数厂商
        "replacement_difficulty": 8,
        "expansion_cycle_months": 18,
        "big_capital_signal": "AI 算力需求驱动",
        "exit_signal": "国际巨头大规模降价",
        "framework_judgment": "卡脖子逻辑成立",
        "confidence": 4,
        "source_url": "methodology/serenity-choke-point.md",
        "data_as_of": "2026-06-29",
    },
    "688017": {  # 绿的谐波
        "stock_name": "绿的谐波",
        "supply_chain_position": "谐波减速器（机器人核心零部件）",
        "choke_score": 7,
        "supplier_count": 5,  # 国际巨头哈默纳科主导高端
        "replacement_difficulty": 8,
        "expansion_cycle_months": 24,
        "big_capital_signal": "机器人主题驱动",
        "exit_signal": "国际巨头大规模降价",
        "framework_judgment": "卡脖子逻辑部分成立",
        "confidence": 4,
        "source_url": "methodology/serenity-choke-point.md",
        "data_as_of": "2026-06-29",
    },
    "002747": {  # 埃斯顿
        "stock_name": "埃斯顿",
        "supply_chain_position": "工业机器人本体",
        "choke_score": 6,
        "supplier_count": 10,  # 国产化率中等
        "replacement_difficulty": 6,
        "expansion_cycle_months": 12,
        "big_capital_signal": "国产替代主题",
        "exit_signal": "国产化率饱和",
        "framework_judgment": "卡脖子逻辑部分成立",
        "confidence": 3,
        "source_url": "methodology/serenity-choke-point.md",
        "data_as_of": "2026-06-29",
    },
}


class ChokePointAnalyzer:
    """Serenity 卡脖子分析器（v1：基于已知样本库）"""

    def analyze(self, stock_code: str) -> Dict[str, Any]:
        """返回指定股票代码的卡脖子定位"""
        code = stock_code.strip()
        if code in KNOWN_CHOKE_POINTS:
            return {
                "status": "ok",
                "stock_code": code,
                "source": "known_library",
                "framework": "Serenity 卡脖子 v2.0",
                **KNOWN_CHOKE_POINTS[code],
            }
        else:
            return {
                "status": "ok",
                "stock_code": code,
                "source": "default",
                "framework": "Serenity 卡脖子 v2.0",
                "stock_name": None,
                "supply_chain_position": "暂无数据（建议手工分析）",
                "choke_score": 0,
                "supplier_count": None,
                "replacement_difficulty": None,
                "expansion_cycle_months": None,
                "big_capital_signal": "未识别",
                "exit_signal": "未识别",
                "framework_judgment": "未识别",
                "confidence": 0,
                "note": "该股票不在已知卡脖子样本库。触发短语：「用 Seri 框架分析 [股票代码]」，由 Mavis 调用完整方法论做手工分析。",
            }

    def batch_analyze(self, stock_codes: List[str]) -> Dict[str, Any]:
        """批量分析，返回 {code: result}"""
        results = {}
        for code in stock_codes:
            results[code] = self.analyze(code)
        return {
            "status": "ok",
            "framework": "Serenity 卡脖子 v2.0",
            "count": len(results),
            "results": results,
        }


class ThreeLensAnalyzer:
    """Prism 三棱镜分析器（v1：基于已知宏观状态模板）"""

    # 简化版宏观状态模板（基于 2026-06-29 已知信息）
    CURRENT_MACRO = {
        "fed_cycle": "暂停，9 月加息概率约 80%（CME FedWatch）",
        "liquidity": "国内宽松（MLF 续作 5000 亿），海外收紧（PCE 3.4%）",
        "geo_risk": "美伊 6/30 恢复技术性谈判，但 6/26 美军已空袭伊朗，脆弱",
        "market_sentiment": "避险 + 半年末资金紧 + 机构集中兑现",
        "judgment": "逆风期，降低仓位，等 7/29-30 美联储议息",
        "data_as_of": "2026-06-29",
    }

    def analyze(
        self,
        stock_code: str,
        choke_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """返回三视角联合分析"""
        # 如果没传 choke_result，自动跑一次
        if choke_result is None:
            choke_result = ChokePointAnalyzer().analyze(stock_code)

        return {
            "status": "ok",
            "stock_code": stock_code,
            "framework": "Prism 三棱镜 v3.1.0",
            "daoshi": self.CURRENT_MACRO,
            "seri": {
                "supply_chain_position": choke_result.get("supply_chain_position"),
                "choke_score": choke_result.get("choke_score"),
                "framework_judgment": choke_result.get("framework_judgment"),
                "big_capital_signal": choke_result.get("big_capital_signal"),
                "exit_signal": choke_result.get("exit_signal"),
            },
            "cat": {
                "judgment": "条件不满足（半自动模式）",
                "reason": "需要 K 线 / 成交量 / ATR 等实时数据；建议用户提供 TradingView 截图",
                "trigger_signals": [
                    "价格回调到 5 月平台",
                    "7/29-30 美联储议息后明朗",
                    "Q2 业绩披露催化",
                ],
            },
            "disclaimer": "以上为框架推演，不构成投资建议。",
            "data_as_of": "2026-06-29",
        }


# 单例（避免每次都创建）
_choke_analyzer: Optional[ChokePointAnalyzer] = None
_three_lens_analyzer: Optional[ThreeLensAnalyzer] = None


def get_choke_analyzer() -> ChokePointAnalyzer:
    global _choke_analyzer
    if _choke_analyzer is None:
        _choke_analyzer = ChokePointAnalyzer()
    return _choke_analyzer


def get_three_lens_analyzer() -> ThreeLensAnalyzer:
    global _three_lens_analyzer
    if _three_lens_analyzer is None:
        _three_lens_analyzer = ThreeLensAnalyzer()
    return _three_lens_analyzer
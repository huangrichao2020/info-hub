"""
Info-Hub 最终分析决策引擎 (Decision Engine)
=============================================
融合 info-hub 实时数据 + Stock-Trading-Wisdom 方法论 + 本地Skill数据源
产出三种报告：盘前报告 / 盘中快报 / 盘后复盘

核心理念：不预测，只跟随；不博弈，只确认。
决策顺序：市场分类 → 概率情景 → 时间门纪律 → 证据补强
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger("info-hub.decision")

CN_TZ = ZoneInfo("Asia/Shanghai")
REPORT_DIR = Path(__file__).parent.parent.parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "http://127.0.0.1:8765/api"


# ═══════════════════════════════════════════════════════════
# 核心方法论常量（来自 Stock-Trading-Wisdom + info-hub methodology）
# ═══════════════════════════════════════════════════════════

# 情绪周期阈值
EMOTION_THRESHOLDS = {
    "ice": {"zt_count": 20, "lianban": 3},        # 冰点
    "recovery": {"zt_count": 50, "lianban": 4},    # 复苏
    "climax": {"zt_count": 80, "lianban": 7},       # 高潮
    "retreat_volume": 6000,  # 亿，低于此空仓
    "attack_volume": 15000,  # 亿，高于此积极
    "defend_zt": 50,         # 涨停<50降仓
}

# 风控参数
RISK_PARAMS = {
    "single_stock_max": 0.15,     # 单票≤15%
    "same_theme_max": 2,          # 同题材最多2只
    "total_max": 0.80,            # 总仓位≤80%
    "stop_loss_pct": -0.08,       # 无条件止损-8%
    "short_stop_pct": -0.05,      # 短线止损-5%
    "break_ma5_exit": True,       # 破5日线退出
    "break_ma20_3day_exit": True, # 破20日线3日不收回退出
    "engines_required": 2,        # 买入前至少2引擎看多
}

# 板块梯队定义
TIER_RULES = {
    "T0": {"desc": "情绪龙头", "criteria": "最高板/最先涨停/小市值高弹性"},
    "T1": {"desc": "核心中军", "criteria": "趋势龙头/大市值机构票/沿5日线"},
    "T2": {"desc": "强势跟涨", "criteria": "涨幅5%-8%/量能放大/日内套利"},
    "T3": {"desc": "补涨龙", "criteria": "龙头滞涨后低位启动"},
}

# 住相阶段操作映射
OBSESSION_ACTIONS = {
    0: "继续观察，正常交易",
    1: "开始盯盘，提高警惕",
    2: "考虑减仓，降低敞口",
    3: "必须减仓，保护利润",
    4: "清仓准备，现金为王",
    5: "远离该板块，不接飞刀",
}


# ═══════════════════════════════════════════════════════════
# 数据采集层
# ═══════════════════════════════════════════════════════════

async def _fetch(endpoint: str, timeout: float = 30) -> dict | list:
    """统一API调用"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(f"{API_BASE}{endpoint}")
        resp.raise_for_status()
        return resp.json()


async def collect_market_data() -> dict:
    """采集全市场数据"""
    data = {}
    tasks = {
        "zt": "/zt/today",
        "obsession": "/obsession-phase/status",
        "sectors": "/sectors/hot",
        "fin_news": "/fin-news/latest?limit=20",
        "cross_valid": "/stock/cross-validation",
    }
    
    for key, endpoint in tasks.items():
        try:
            data[key] = await _fetch(endpoint)
        except Exception as e:
            logger.warning(f"数据采集失败 [{key}]: {e}")
            data[key] = None
    
    return data


# ═══════════════════════════════════════════════════════════
# 分析计算层
# ═══════════════════════════════════════════════════════════

def analyze_emotion_cycle(zt_data: dict | None, obsession: dict | None) -> dict:
    """分析当前情绪周期阶段"""
    zt_count = 0
    lianban_max = 0
    if zt_data and "items" in zt_data:
        items = zt_data["items"]
        zt_count = len(items)
        lianban_max = max((i.get("lianban_count", 1) for i in items), default=1)
    
    # 判定周期阶段
    if zt_count < EMOTION_THRESHOLDS["ice"]["zt_count"]:
        cycle = "冰点期"
        action = "空仓或轻仓试错首板"
    elif zt_count < EMOTION_THRESHOLDS["recovery"]["zt_count"]:
        cycle = "复苏期"
        action = "加仓核心股，关注连板晋级"
    elif zt_count >= EMOTION_THRESHOLDS["climax"]["zt_count"]:
        cycle = "高潮期"
        action = "持股待涨，去弱留强，警惕退潮"
    else:
        cycle = "正常期"
        action = "正常交易，关注轮动节奏"
    
    # 退潮信号（来自住相系统）
    if obsession and obsession.get("signal_count", 0) >= 3:
        cycle = "⚠️ 退潮预警"
        action = "清仓空仓，管住手"
    
    return {
        "cycle": cycle,
        "action": action,
        "zt_count": zt_count,
        "lianban_max": lianban_max,
        "obsession_signals": obsession.get("signal_count", 0) if obsession else 0,
        "obsession_phase": obsession.get("phase_label", "未知") if obsession else "未知",
    }


def analyze_zt_distribution(zt_data: dict | None) -> dict:
    """分析涨停行业分布"""
    if not zt_data or "items" not in zt_data:
        return {"top_industries": [], "total": 0}
    
    items = zt_data["items"]
    industry_count = {}
    for item in items:
        industry = item.get("industry", "未知")
        industry_count[industry] = industry_count.get(industry, 0) + 1
    
    sorted_industries = sorted(industry_count.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total": len(items),
        "top_industries": [
            {"industry": ind, "count": cnt}
            for ind, cnt in sorted_industries[:10]
        ],
    }


def analyze_sectors(sectors_data: dict | list | None) -> dict:
    """分析板块强弱"""
    if not sectors_data:
        return {"hot": [], "cold": []}
    
    sectors = sectors_data if isinstance(sectors_data, list) else sectors_data.get("sectors", [])
    
    hot = []
    for s in sectors[:5] if isinstance(sectors, list) else []:
        if isinstance(s, dict):
            hot.append({
                "name": s.get("name", s.get("sector", "")),
                "change": s.get("change_pct", s.get("change", 0)),
                "lead_stock": s.get("lead_stock", ""),
            })
    
    return {"hot": hot, "count": len(sectors)}


def compute_risk_assessment(emotion: dict, zt_dist: dict) -> dict:
    """综合风险评估"""
    risks = []
    risk_level = "low"
    
    # 情绪周期风险
    if emotion["cycle"] in ("退潮预警", "冰点期"):
        risks.append(f"情绪周期处于{emotion['cycle']}，风险较高")
        risk_level = "high"
    elif emotion["cycle"] == "高潮期":
        risks.append("涨停家数高位，注意退潮风险")
        risk_level = "medium"
    
    # 住相信号风险
    if emotion["obsession_signals"] >= 3:
        risks.append(f"住相破裂信号{emotion['obsession_signals']}个，叙事可能崩塌")
        risk_level = "high"
    elif emotion["obsession_signals"] >= 1:
        risks.append(f"住相预警信号{emotion['obsession_signals']}个，需关注")
        risk_level = max(risk_level, "medium")
    
    return {
        "level": risk_level,
        "risks": risks,
        "position_advice": {
            "high": "降至3成以下或空仓",
            "medium": "控制在5成以内",
            "low": "可积极操作，总仓位≤80%",
        }.get(risk_level, "正常"),
    }


# ═══════════════════════════════════════════════════════════
# 报告生成层
# ═══════════════════════════════════════════════════════════

def _now_str() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M")


def _today_str() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d")


def generate_pre_market_report(data: dict) -> str:
    """生成盘前报告 (09:00)"""
    emotion = data.get("emotion", {})
    zt_dist = data.get("zt_dist", {})
    sectors = data.get("sectors", {})
    risk = data.get("risk", {})
    obsession = data.get("obsession", {})
    
    lines = []
    lines.append(f"# 📊 Info-Hub 盘前作战报告")
    lines.append(f"> 生成时间：{_now_str()} | 交易日：{_today_str()}")
    lines.append("")
    
    # 1. 市场情绪
    lines.append("## 🎭 市场情绪")
    lines.append(f"- **情绪周期**：{emotion.get('cycle', '未知')}")
    lines.append(f"- **昨日涨停**：{emotion.get('zt_count', 0)}家")
    lines.append(f"- **最高连板**：{emotion.get('lianban_max', 0)}板")
    lines.append(f"- **住相阶段**：{emotion.get('obsession_phase', '未知')}（{emotion.get('obsession_signals', 0)}个信号）")
    lines.append(f"- **操作建议**：{emotion.get('action', '待定')}")
    lines.append("")
    
    # 2. 风险评估
    lines.append("## ⚠️ 风险评估")
    lines.append(f"- **风险等级**：{risk.get('level', 'unknown')}")
    lines.append(f"- **仓位建议**：{risk.get('position_advice', '待定')}")
    for r in risk.get("risks", []):
        lines.append(f"  - {r}")
    lines.append("")
    
    # 3. 涨停行业分布
    lines.append("## 🔥 昨日涨停分布")
    lines.append(f"- **涨停总数**：{zt_dist.get('total', 0)}家")
    lines.append("")
    lines.append("| 排名 | 行业 | 涨停数 |")
    lines.append("|------|------|--------|")
    for i, ind in enumerate(zt_dist.get("top_industries", [])[:8], 1):
        lines.append(f"| {i} | {ind['industry']} | {ind['count']} |")
    lines.append("")
    
    # 4. 今日关注
    lines.append("## 🎯 今日关注方向")
    top3 = zt_dist.get("top_industries", [])[:3]
    for i, ind in enumerate(top3, 1):
        lines.append(f"{i}. **{ind['industry']}**（{ind['count']}家涨停）")
    if not top3:
        lines.append("> 暂无明确主线，等待盘中信号")
    lines.append("")
    
    # 5. 操作策略
    lines.append("## 📋 今日操作策略")
    lines.append("")
    lines.append("### 进攻")
    lines.append("- 关注涨停集中度最高的板块，优先T0龙头和T1中军")
    lines.append("- 竞价高开>3%且量比>2的标的重点关注")
    lines.append("- 新题材首板批量出现（≥5家）可视为新周期信号")
    lines.append("")
    lines.append("### 防守")
    lines.append("- 单票仓位≤15%，同题材≤2只")
    lines.append("- 涨停家数<50时降至5成以下")
    lines.append("- 高位澄清/减持公告股坚决回避")
    lines.append("")
    lines.append("### 止损纪律")
    lines.append("- 打板炸板立即走 | 低吸破5日线止损 | 亏损≥5%无条件离场")
    lines.append("")
    
    # 6. 方法论提示
    lines.append("## 🧠 今日心法")
    lines.append("> \"市场是情绪的集合，技术是情绪的载体。不预测，只跟随；不博弈，只确认。\"")
    lines.append(f"> 当前处于**{emotion.get('cycle', '')}**，{emotion.get('action', '')}")
    if obsession and obsession.get("signal_count", 0) > 0:
        signals_triggered = [s["name"] for s in obsession.get("signals", []) if s.get("triggered")]
        if signals_triggered:
            lines.append(f"> ⚠️ 触发的住相信号：{', '.join(signals_triggered)}")
    lines.append("")
    
    lines.append("---")
    lines.append(f"*报告由 Info-Hub Decision Engine 自动生成*")
    
    return "\n".join(lines)


def generate_intraday_alert(data: dict) -> str:
    """生成盘中快报（每5分钟）"""
    emotion = data.get("emotion", {})
    zt_dist = data.get("zt_dist", {})
    risk = data.get("risk", {})
    
    lines = []
    lines.append(f"# ⚡ 盘中快报")
    lines.append(f"> {_now_str()}")
    lines.append("")
    lines.append(f"**情绪周期**：{emotion.get('cycle', '-')} | **涨停**：{emotion.get('zt_count', 0)}家 | **连板**：{emotion.get('lianban_max', 0)}板")
    lines.append(f"**住相**：{emotion.get('obsession_phase', '-')}({emotion.get('obsession_signals', 0)}信号) | **风险**：{risk.get('level', '-')}")
    lines.append("")
    
    # 快速信号
    signals = []
    if emotion.get("obsession_signals", 0) >= 3:
        signals.append("🔴 住相破裂信号≥3，注意减仓")
    elif emotion.get("obsession_signals", 0) >= 1:
        signals.append("🟡 住相预警信号触发，提高警惕")
    
    if zt_dist.get("total", 0) >= EMOTION_THRESHOLDS["climax"]["zt_count"]:
        signals.append("🟢 涨停家数高位，情绪积极")
    elif zt_dist.get("total", 0) < EMOTION_THRESHOLDS["defend_zt"]:
        signals.append("🔴 涨停不足50家，注意防守")
    
    if emotion.get("lianban_max", 0) >= 7:
        signals.append("⚠️ 连板高度≥7板，高潮期警惕退潮")
    
    for s in signals:
        lines.append(f"- {s}")
    
    lines.append("")
    lines.append(f"> 仓位建议：{risk.get('position_advice', '正常')}")
    
    return "\n".join(lines)


def generate_post_market_report(data: dict) -> str:
    """生成盘后复盘报告 (15:30)"""
    emotion = data.get("emotion", {})
    zt_dist = data.get("zt_dist", {})
    sectors = data.get("sectors", {})
    risk = data.get("risk", {})
    obsession = data.get("obsession", {})
    
    lines = []
    lines.append(f"# 📈 Info-Hub 盘后复盘报告")
    lines.append(f"> 生成时间：{_now_str()} | 交易日：{_today_str()}")
    lines.append("")
    
    # 1. 市场全景
    lines.append("## 一、市场全景")
    lines.append(f"- **情绪周期**：{emotion.get('cycle', '-')}")
    lines.append(f"- **涨停家数**：{zt_dist.get('total', 0)}家")
    lines.append(f"- **最高连板**：{emotion.get('lianban_max', 0)}板")
    lines.append(f"- **住相阶段**：{emotion.get('obsession_phase', '-')}（{emotion.get('obsession_signals', 0)}信号）")
    lines.append(f"- **风险等级**：{risk.get('level', '-')}")
    lines.append("")
    
    # 2. 涨停深度分析
    lines.append("## 二、涨停深度分析")
    lines.append("")
    lines.append("### 行业分布 Top 10")
    lines.append("| 排名 | 行业 | 涨停数 | 占比 |")
    lines.append("|------|------|--------|------|")
    total = zt_dist.get("total", 1) or 1
    for i, ind in enumerate(zt_dist.get("top_industries", [])[:10], 1):
        pct = ind["count"] / total * 100
        lines.append(f"| {i} | {ind['industry']} | {ind['count']} | {pct:.1f}% |")
    lines.append("")
    
    # 3. 主线识别
    lines.append("## 三、主线识别")
    top_industries = zt_dist.get("top_industries", [])
    if top_industries and top_industries[0]["count"] >= 5:
        main = top_industries[0]
        lines.append(f"**主线确认**：{main['industry']}（{main['count']}家涨停）")
        lines.append(f"- 梯队完整性：待盘中验证")
        lines.append(f"- 操作策略：聚焦主线龙头，T0打板/T1低吸5日线")
    else:
        lines.append("**无明确主线**：涨停分散，轮动为主")
        lines.append("- 操作策略：轻仓试错，等待主线确认")
    lines.append("")
    
    # 4. 住相信号详情
    lines.append("## 四、住相信号链")
    if obsession and obsession.get("signals"):
        for s in obsession["signals"]:
            icon = "🔴" if s.get("triggered") else "🟢"
            lines.append(f"- {icon} **{s.get('name', '')}**：{s.get('description', '')}")
    lines.append(f"\n**当前阶段**：{emotion.get('obsession_phase', '-')}")
    lines.append(f"**操作建议**：{OBSESSION_ACTIONS.get(emotion.get('obsession_signals', 0), '待定')}")
    lines.append("")
    
    # 5. 明日预判
    lines.append("## 五、明日预判")
    lines.append("")
    lines.append("### 两种剧本")
    lines.append("**剧本A（延续）**：主线板块竞价高开→龙头强封→跟风扩散→加仓主线")
    lines.append("**剧本B（分歧）**：龙头断板→板块分化→资金切低位→去弱留强降仓")
    lines.append("")
    
    # 6. 下周展望（仅周五）
    if datetime.now(CN_TZ).weekday() == 4:
        lines.append("## 六、下周事件前瞻")
        lines.append("> 周末关注：政策面消息、外盘走势、行业大事件")
        lines.append("> 周一策略：利好前排一字不追，利空核按钮观望")
        lines.append("")
    
    # 7. 方法论沉淀
    lines.append("## 🧠 今日方法论沉淀")
    lines.append(f"> 当前市场处于**{emotion.get('cycle', '')}**")
    lines.append(f"> {emotion.get('action', '')}")
    lines.append("")
    lines.append("### 今日核心教训")
    lines.append("- 记录今日操作中的得失，特别是：")
    lines.append("  - 是否遵守了仓位纪律？")
    lines.append("  - 是否有情绪化交易？")
    lines.append("  - 信号是否符合预期？")
    lines.append("")
    
    lines.append("---")
    lines.append(f"*报告由 Info-Hub Decision Engine 自动生成 | 数据来源：腾讯行情/东方财富/同花顺*")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

async def run_full_analysis(report_type: str = "pre_market") -> str:
    """
    运行完整分析流程
    
    Args:
        report_type: "pre_market" | "intraday" | "post_market"
    
    Returns:
        生成的报告 Markdown 文本
    """
    logger.info(f"[Decision] 开始生成 {report_type} 报告...")
    
    # 1. 采集数据
    raw = await collect_market_data()
    
    # 2. 分析计算
    emotion = analyze_emotion_cycle(raw.get("zt"), raw.get("obsession"))
    zt_dist = analyze_zt_distribution(raw.get("zt"))
    sectors = analyze_sectors(raw.get("sectors"))
    risk = compute_risk_assessment(emotion, zt_dist)
    
    data = {
        "emotion": emotion,
        "zt_dist": zt_dist,
        "sectors": sectors,
        "risk": risk,
        "obsession": raw.get("obsession"),
        "raw": raw,
    }
    
    # 3. 生成报告
    if report_type == "pre_market":
        report = generate_pre_market_report(data)
    elif report_type == "intraday":
        report = generate_intraday_alert(data)
    elif report_type == "post_market":
        report = generate_post_market_report(data)
    else:
        report = generate_pre_market_report(data)
    
    # 4. 保存报告
    filename = f"{_today_str()}_{report_type}.md"
    filepath = REPORT_DIR / filename
    filepath.write_text(report, encoding="utf-8")
    logger.info(f"[Decision] 报告已保存: {filepath}")
    
    return report


async def run_pre_market() -> str:
    """盘前分析（09:00）"""
    return await run_full_analysis("pre_market")


async def run_intraday() -> str:
    """盘中快报（每5分钟）"""
    return await run_full_analysis("intraday")


async def run_post_market() -> str:
    """盘后复盘（15:30）"""
    return await run_full_analysis("post_market")


# ═══════════════════════════════════════════════════════════
# CLI入口（用于定时任务调用）
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    report_type = sys.argv[1] if len(sys.argv) > 1 else "pre_market"
    report = asyncio.run(run_full_analysis(report_type))
    print(report)

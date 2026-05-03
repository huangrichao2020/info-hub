"""
个股综合分析服务 - 13提示词框架 + 执念/供需视角
融合LLM定性分析 + 本地量化数据
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

import pandas as pd

from services.valuation_service import get_current_valuation, calculate_percentile, get_pe_history
from services.market_service import _load_cache as load_market_cache
from llm.qwen_client import chat

logger = logging.getLogger("info-hub.stock_analysis")

# 13个提示词框架定义
PROMPTS = {
    1: {
        "name": "业务定性",
        "desc": "这家公司做什么的？靠什么赚钱？生意模式是什么？",
    },
    2: {
        "name": "行业地位",
        "desc": "行业龙头？细分冠军？还是边缘跟风？",
    },
    3: {
        "name": "财务健康",
        "desc": "营收增速、净利润、现金流、资产负债率",
    },
    4: {
        "name": "估值分析",
        "desc": "PE五年百分位、PB百分位、是否低估/高估",
    },
    5: {
        "name": "产业链位置",
        "desc": "上游原材料？中游制造？下游终端？议价能力如何？",
    },
    6: {
        "name": "催化剂",
        "desc": "近期有无事件驱动？政策利好？订单利好？业绩预增？",
    },
    7: {
        "name": "财务排雷",
        "desc": "有无财务粉饰迹象？应收账款异常？商誉减值风险？",
    },
    8: {
        "name": "供应链依赖",
        "desc": "是否依赖单一客户/供应商？集中度风险？",
    },
    9: {
        "name": "内幕排查",
        "desc": "大股东增减持？高管变动？监管问询？",
    },
    10: {
        "name": "技术面",
        "desc": "均线位置、MACD、量价关系",
    },
    11: {
        "name": "支撑压力",
        "desc": "关键支撑位和压力位在哪里？",
    },
    12: {
        "name": "情景推演",
        "desc": "乐观/中性/悲观三种情景下的走势推演",
    },
    13: {
        "name": "决策建议",
        "desc": "综合以上信息，给出操作建议（买/卖/观望）及仓位建议",
    },
}


def _load_stock_kline(code: str) -> Optional[pd.DataFrame]:
    """从本地parquet加载K线数据，如果parquet数据不足则从baostock实时查询"""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'historical'
    )
    
    # 标准化代码格式 - 提取数字
    code_digits = ''.join(c for c in code if c.isdigit())
    candidates = list(set([
        f"sh_{code_digits}",
        f"sz_{code_digits}",
        code_digits,
    ]))
    
    for suffix in candidates:
        path = os.path.join(data_dir, f"{suffix}.parquet")
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path)
                valid_idx = df[df['close'].notna()].index
                if len(valid_idx) >= 10:
                    last_valid = valid_idx[-1]
                    start_idx = max(0, last_valid - 59)
                    result = df.loc[start_idx:last_valid].copy()
                    result = result.dropna(subset=['close'])
                    if len(result) >= 2:
                        return result
            except:
                continue
    
    # 从baostock实时查询近60天
    try:
        import baostock as bs
        from datetime import datetime, timedelta
        
        bs_code = code.replace('_', '.').upper()
        if '.' not in bs_code:
            bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        bs.login()
        rs = bs.query_history_k_data_plus(
            bs_code, "date,close,volume,turn",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="2"
        )
        df = rs.get_data()
        df = df.replace('', pd.NA)
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['turn'] = pd.to_numeric(df['turn'], errors='coerce')
        df = df.dropna(subset=['close'])
        bs.logout()
        
        if len(df) >= 2:
            return df.tail(60).reset_index(drop=True)
    except Exception as e:
        logger.debug(f"baostock查询{code}失败: {e}")
    
    return None


def _build_data_context(code: str) -> Dict[str, Any]:
    """构建分析所需的全部数据上下文"""
    context = {"code": code, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}
    
    # 1. 本地K线数据
    kline = _load_stock_kline(code)
    if kline is not None and len(kline) > 0:
        context["kline"] = {
            "latest_date": str(kline['date'].iloc[-1])[:10],
            "latest_close": round(float(kline['close'].iloc[-1]), 2),
            "change_pct": round((kline['close'].iloc[-1] / kline['close'].iloc[-2] - 1) * 100, 2) if len(kline) >= 2 else 0,
            "ma5": round(float(kline['close'].rolling(5).mean().iloc[-1]), 2),
            "ma10": round(float(kline['close'].rolling(10).mean().iloc[-1]), 2),
            "ma20": round(float(kline['close'].rolling(20).mean().iloc[-1]), 2),
            "ma60": round(float(kline['close'].rolling(60).mean().iloc[-1]), 2) if len(kline) >= 60 else None,
            "volume_latest": round(float(kline['volume'].iloc[-1]), 0),
            "volume_ma20": round(float(kline['volume'].rolling(20).mean().iloc[-1]), 0),
        }
    
    # 2. 估值数据
    valuation = get_current_valuation(code)
    if valuation:
        context["valuation"] = valuation
        # 计算PE百分位
        if valuation.get("pe_ttm"):
            pe_pct = calculate_percentile(code, valuation["pe_ttm"], "pe_ttm")
            context["valuation"]["pe_percentile"] = pe_pct
        if valuation.get("pb"):
            pb_pct = calculate_percentile(code, valuation["pb"], "pb")
            context["valuation"]["pb_percentile"] = pb_pct
    
    # 3. 行业信息
    market = load_market_cache()
    all_stocks = {s['code']: s for s in market.get('all_stocks', [])}
    
    # 尝试多种code格式匹配行业
    code_digits = ''.join(c for c in code if c.isdigit())
    code_variants = [
        code,
        f"sh.{code_digits}",
        f"sz.{code_digits}",
        f"sh_{code_digits}",
        f"sz_{code_digits}",
    ]
    for cv in code_variants:
        if cv in all_stocks:
            context["industry"] = all_stocks[cv].get('industry', '')
            break
    
    if context.get("industry") is None and valuation and valuation.get('name'):
        context["company_name"] = valuation['name']
    
    return context


def _build_analysis_prompt(code: str, context: Dict[str, Any]) -> str:
    """构建综合分析 prompt，遵循结构化、防幻觉原则"""
    kline_data = json.dumps(context.get('kline', {}), ensure_ascii=False, indent=2)
    valuation_data = json.dumps(context.get('valuation', {}), ensure_ascii=False, indent=2)
    
    return f"""## 角色与任务
你是一位拥有 20 年实战经验的资深 A 股交易员，擅长趋势跟踪与主升浪挖掘。请根据提供的量化数据，对【{code}】进行多维深度分析。

## 输入数据
### 1. 基础信息
- 股票代码：{code}
- 最新价：{context.get('kline', {}).get('latest_close', 'N/A')}
- 涨跌幅：{context.get('kline', {}).get('change_pct', 'N/A')}%
- 所属行业：{context.get('industry', '未知')}

### 2. 技术面 (K 线数据)
```json
{kline_data}
```

### 3. 估值面
```json
{valuation_data}
```

## 分析步骤
请严格按以下步骤进行推理，不要跳过：
1. **基本面定锚**：基于估值和行业信息，判断当前股价处于历史相对位置（低估/合理/高估）。
2. **趋势判断**：结合均线数据（MA5/10/20/60），明确当前是上升/下降/震荡趋势。重点关注 25 日线（近似 MA20）的支撑/压力作用。
3. **量价验证**：对比最新成交量与 MA20 均量，判断资金态度（放量突破/缩量回调/缩量阴跌等）。
4. **执念/供需分析**：结合情绪与筹码面，判断主力意图。
5. **综合结论**：给出明确的评级和操作策略。

## 约束（防幻觉）
- **严禁编造数据**：所有结论必须有上述输入数据作为依据。如果数据缺失（如无估值数据），请直接标注“数据不足”，绝对不要猜测。
- **客观中立**：不要受一般性股评观点影响，完全基于量价事实说话。

## 输出格式
请严格输出以下 JSON 格式，不要包含任何 Markdown 标记或其他文字：
{{
    "rating": "看多/看空/震荡",
    "confidence": "高/中/低",
    "reasoning_summary": "一句话总结核心逻辑",
    "technical_view": {{
        "trend": "上升/下降/震荡",
        "support_level": 具体数值,
        "pressure_level": 具体数值
    }},
    "capital_flow": "资金流入/流出/平衡",
    "action_plan": {{
        "buy_condition": "触发买入的具体信号",
        "stop_loss": "明确的止损位数值"
    }}
}}
"""


async def analyze_stock(code: str, use_llm: bool = True) -> Dict[str, Any]:
    """执行个股综合分析"""
    start = time.time()
    context = _build_data_context(code)
    
    result = {
        "code": code,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_context": {
            "kline": context.get("kline"),
            "valuation": context.get("valuation"),
            "industry": context.get("industry"),
        },
    }
    
    if use_llm:
        try:
            prompt = _build_analysis_prompt(code, context)
            messages = [{"role": "user", "content": prompt}]
            response = await chat(messages, temperature=0.3, max_tokens=4096)
            
            # 尝试解析JSON
            try:
                # 提取JSON部分
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    analysis = json.loads(response[json_start:json_end])
                    result["analysis"] = analysis
                    result["llm_raw"] = response
                else:
                    result["analysis"] = {"error": "LLM返回格式异常"}
                    result["llm_raw"] = response
            except json.JSONDecodeError:
                result["analysis"] = {"error": "LLM返回解析失败", "raw": response[:500]}
                result["llm_raw"] = response
            
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            result["analysis"] = {"error": f"LLM调用失败: {str(e)}"}
    else:
        # 无LLM模式：仅返回量化分析
        result["analysis"] = _quantitative_only(context)
    
    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


def _quantitative_only(context: Dict[str, Any]) -> Dict[str, Any]:
    """纯量化分析（不调用LLM）"""
    kline = context.get("kline", {})
    valuation = context.get("valuation", {})
    
    # 自动判断
    ma_trend = "多头" if kline.get("ma5", 0) > kline.get("ma20", 0) else "空头"
    pe_level = "低估" if (valuation.get("pe_percentile", 50) or 50) < 30 else "高估" if (valuation.get("pe_percentile", 50) or 50) > 70 else "合理"
    
    return {
        "技术面": f"均线{ma_trend}排列，MA5={kline.get('ma5')} MA20={kline.get('ma20')}",
        "估值": f"PE百分位{valuation.get('pe_percentile', 'N/A')}%，处于{pe_level}区间",
        "量价": f"最新量能{valuation.get('volume_latest', 'N/A')}，20日均量{valuation.get('volume_ma20', 'N/A')}",
        "综合判断": f"{'偏多' if ma_trend == '多头' and pe_level == '低估' else '观望'}",
    }

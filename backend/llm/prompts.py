"""
各场景提示词模板
"""
import json

from llm.methodology import VIRAL_METHODOLOGY
from llm.uwillberich import build_review_system_prompt, build_turn_strong_system_prompt


def article_messages(topic: str, platform: str, reference: str = "", word_count: int = 2000) -> list[dict]:
    """生成文章的 messages"""
    platform_names = {"wechat": "微信公众号", "toutiao": "今日头条", "zhihu": "知乎"}
    pname = platform_names.get(platform, platform)

    user_content = f"请围绕以下话题，为【{pname}】平台撰写一篇爆款文章。\n\n话题：{topic}\n目标字数：约{word_count}字\n"
    if reference:
        user_content += f"\n参考素材：\n{reference}\n"
    user_content += "\n请严格按照方法论中对应平台的适配规则来写，包括标题、开头、结构、结尾都要符合要求。直接输出文章内容，不需要额外解释。"

    return [
        {"role": "system", "content": VIRAL_METHODOLOGY},
        {"role": "user", "content": user_content},
    ]


def review_messages(portfolio_data: list[dict], market_context: str, date: str = "", sector_summary: str = "") -> list[dict]:
    """生成复盘报告的 messages"""
    # 构建持仓明细，明确显示标的物
    portfolio_text = "\n".join(
        f"- **{s['name']}**（{s['code']}）：{s['shares']}股，成本价 {s['cost_price']} 元"
        for s in portfolio_data
    )

    user_content = f"""请对以下持仓进行全面复盘分析。

## 持仓明细（标的物）
{portfolio_text}

## 市场数据
{market_context}

## 板块整体情况
{sector_summary}

{"## 日期: " + date if date else ""}

请严格按照以下顺序和格式进行复盘分析：

### 一、【市场分类与大盘定性】
1. 先判断当前市场属于：主线市场 / 独立龙头市场 / 区间防御市场
2. 必须给出明确判断理由（资金流向、赚钱效应、涨停高度、连板梯队等）
3. 不要回避"无明确主线"的判断

### 二、【板块整体情况分析】
基于上述板块数据，分析：
1. 今日领涨板块是谁？领涨逻辑是什么？（政策/业绩/题材/重组）
2. 今日领跌板块是谁？为什么领跌？是短期调整还是趋势反转？
3. 板块轮动节奏：今天是普涨/普跌/分化？分化时谁强谁弱？
4. 涨停板分析：涨停数量、连板高度、涨停原因归类
5. 当前市场风格：大盘股强还是小盘股强？价值强还是成长强？
6. 持仓股所属板块今日表现如何？在板块内是领涨/跟涨/领跌/抗跌？

### 三、【持仓逐项评估】（每只持仓必须单独一段）
对每只持仓股必须给出：
1. **标的物**：股票代码和名称（加粗显示）
2. **当前状态**：技术面（均线/支撑/压力/量价关系）
3. **所属板块表现**：该板块今天整体表现如何？板块内地位如何？
4. **同方向标的**：该板块内还有哪些股票值得关注？（必须给出至少 2-3 只同板块股票，附代码和名称，方便加入自选观察）
5. **操作建议**：明确给出持有/加仓/减仓/清仓建议，并说明原因
6. **关键价位**：止损位、目标价各是多少？

### 四、【基准/乐观/风险三种情景】
- 基准情景（概率最大）：明日大概率怎么走？持仓应该怎么应对？
- 乐观情景：如果超预期走强，应该加仓哪些票？
- 风险情景：如果走弱，哪些票必须止损？止损位在哪里？

### 五、【时间门纪律】
- 09:00-09:25 集合竞价关注什么？
- 09:30-10:00 开盘半小时观察什么信号？
- 14:00 之后如何决定是否留倉过夜？

### 六、【总结：可做与避免】
明确列出：
- ✅ 可以做的操作（具体到股票代码和方向）
- ❌ 必须避免的操作（具体到股票代码和风险点）

### 七、【自选观察池】
基于今日盘面，给出一个"自选观察池"：
- 列出 5-10 只值得加入自选观察的股票（同方向标的）
- 每只股票注明：代码、名称、所属板块、关注理由
- 方便后续同方向跟踪观察

注意：
- 如果某项证据不足，明确写"证据不足"，不要强行下结论
- 所有判断必须基于客观数据，不要主观臆测
- 给出的同方向标的必须有代码和名称，方便后续加入自选
- 持仓股名称和代码必须加粗显示，确保醒目"""

    return [
        {"role": "system", "content": build_review_system_prompt()},
        {"role": "user", "content": user_content},
    ]


def turn_strong_messages(candidates: list[dict], market_snapshot: dict) -> list[dict]:
    user_content = f"""请根据以下转强候选池做盘前交易分析，并严格返回 JSON。

## 市场快照
{json.dumps(market_snapshot, ensure_ascii=False, indent=2)}

## 转强候选池
{json.dumps(candidates, ensure_ascii=False, indent=2)}

请重点回答：
1. 今日这个转强池的整体特征和市场风格。
2. 每只股票的逻辑支撑、消息支撑、方法论结论。
3. 如果不建议买入，必须明确写出原因。
"""

    return [
        {"role": "system", "content": build_turn_strong_system_prompt()},
        {"role": "user", "content": user_content},
    ]

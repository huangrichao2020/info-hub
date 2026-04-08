"""
各场景提示词模板
"""
from llm.methodology import VIRAL_METHODOLOGY, TRADING_METHODOLOGY


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


def review_messages(portfolio_data: list[dict], market_context: str, date: str = "") -> list[dict]:
    """生成复盘报告的 messages"""
    portfolio_text = "\n".join(
        f"- {s['name']}({s['code']})：{s['shares']}股，成本价 {s['cost_price']} 元"
        for s in portfolio_data
    )

    user_content = f"""请对以下持仓进行全面复盘分析。

## 持仓明细
{portfolio_text}

## 市场数据
{market_context}

{"## 日期: " + date if date else ""}

请严格按照复盘分析框架，从市场环境、个股技术、消息面、板块联动、持仓评估、总结策略六个维度进行分析。对每只持仓股都要给出明确的操作建议。"""

    return [
        {"role": "system", "content": TRADING_METHODOLOGY},
        {"role": "user", "content": user_content},
    ]

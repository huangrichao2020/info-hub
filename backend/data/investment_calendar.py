"""投资日历事件数据 - A股重要会议/政策/经济数据发布日程

支持多数据源聚合：
1. 静态事件库（硬编码的固定事件）
2. 动态事件（可通过 API 拉取的外部数据源）
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger("info-hub.investment-calendar")

# ===== 静态事件库 =====
# 固定事件：两会、财报季、固定经济数据发布日等
INVESTMENT_CALENDAR_STATIC = [
    # ===== 2026年4月 =====
    {
        "date": "2026-04-15",
        "title": "一季度GDP数据发布",
        "type": "economic_data",
        "level": "major",
        "description": "国家统计局发布一季度GDP增速、工业增加值、固定资产投资等核心数据",
        "benefit_sectors": ["顺周期板块", "金融", "地产"],
        "leading_stocks": [
            {"name": "招商银行", "code": "600036.SH", "reason": "经济复苏预期利好银行"},
            {"name": "保利发展", "code": "600048.SH", "reason": "GDP超预期利好地产"},
        ],
    },
    {
        "date": "2026-04-15",
        "title": "3月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "3月消费者物价指数和生产者物价指数发布",
        "benefit_sectors": ["消费", "农业", "资源品"],
        "leading_stocks": [
            {"name": "贵州茅台", "code": "600519.SH", "reason": "通胀预期利好白酒"},
            {"name": "海天味业", "code": "603288.SH", "reason": "CPI上行利好调味品"},
        ],
    },
    {
        "date": "2026-04-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "央行公布最新一期LPR（贷款市场报价利率），关注是否降息",
        "benefit_sectors": ["地产", "券商", "高负债行业"],
        "leading_stocks": [
            {"name": "万科A", "code": "000002.SZ", "reason": "降息利好地产"},
            {"name": "中信证券", "code": "600030.SH", "reason": "流动性宽松利好券商"},
        ],
    },
    {
        "date": "2026-04-25",
        "title": "政治局会议（4月）",
        "type": "meeting",
        "level": "major",
        "description": "4月中央政治局会议，分析研究当前经济形势，部署下一阶段经济工作",
        "benefit_sectors": ["政策受益板块", "新质生产力"],
        "leading_stocks": [
            {"name": "中芯国际", "code": "688981.SH", "reason": "科技自立自强政策利好"},
            {"name": "北方华创", "code": "002371.SZ", "reason": "半导体设备国产替代"},
        ],
    },
    {
        "date": "2026-04-30",
        "title": "4月PMI数据",
        "type": "economic_data",
        "level": "moderate",
        "description": "4月制造业PMI和非制造业PMI发布",
        "benefit_sectors": ["制造", "基建"],
        "leading_stocks": [
            {"name": "中国中车", "code": "601766.SH", "reason": "PMI扩张利好轨交"},
            {"name": "三一重工", "code": "600031.SH", "reason": "制造业回暖利好工程机械"},
        ],
    },
    # ===== 2026年5月 =====
    {
        "date": "2026-05-07",
        "title": "五一假期后首个交易日",
        "type": "market",
        "level": "moderate",
        "description": "五一长假后开盘，关注假期消费数据和外盘表现",
        "benefit_sectors": ["旅游酒店", "航空", "影视"],
        "leading_stocks": [
            {"name": "中国中免", "code": "601888.SH", "reason": "假期消费数据利好免税"},
            {"name": "春秋航空", "code": "601021.SH", "reason": "出行需求旺盛"},
        ],
    },
    {
        "date": "2026-05-11",
        "title": "4月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "4月物价数据发布",
        "benefit_sectors": ["消费", "农业"],
        "leading_stocks": [
            {"name": "伊利股份", "code": "600887.SH", "reason": "消费复苏"},
        ],
    },
    {
        "date": "2026-05-15",
        "title": "一季度财报披露截止",
        "type": "earnings",
        "level": "major",
        "description": "A股上市公司2026年一季度报披露截止日",
        "benefit_sectors": ["业绩超预期板块"],
        "leading_stocks": [],
    },
    {
        "date": "2026-05-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "5月LPR公布",
        "benefit_sectors": ["地产", "券商"],
        "leading_stocks": [
            {"name": "招商蛇口", "code": "001979.SZ", "reason": "降息周期利好地产"},
        ],
    },
    {
        "date": "2026-05-25",
        "title": "政治局会议（5月）",
        "type": "meeting",
        "level": "major",
        "description": "5月政治局会议，年中经济政策定调",
        "benefit_sectors": ["政策受益板块"],
        "leading_stocks": [],
    },
    {
        "date": "2026-05-31",
        "title": "5月PMI数据",
        "type": "economic_data",
        "level": "moderate",
        "description": "5月制造业PMI",
        "benefit_sectors": ["制造"],
        "leading_stocks": [],
    },
    # ===== 2026年6月 =====
    {
        "date": "2026-06-01",
        "title": "6月1日儿童节消费",
        "type": "market",
        "level": "minor",
        "description": "儿童节消费旺季",
        "benefit_sectors": ["零售", "教育", "娱乐"],
        "leading_stocks": [
            {"name": "泡泡玛特", "code": "09992.HK", "reason": "潮玩消费旺季"},
        ],
    },
    {
        "date": "2026-06-10",
        "title": "5月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "5月物价数据",
        "benefit_sectors": ["消费"],
        "leading_stocks": [],
    },
    {
        "date": "2026-06-15",
        "title": "MLF续作+LPR决议",
        "type": "policy",
        "level": "major",
        "description": "央行MLF到期续作，同时公布LPR",
        "benefit_sectors": ["金融", "地产"],
        "leading_stocks": [
            {"name": "平安银行", "code": "000001.SZ", "reason": "货币政策宽松利好银行"},
        ],
    },
    {
        "date": "2026-06-18",
        "title": "618购物节",
        "type": "market",
        "level": "moderate",
        "description": "年中电商大促，关注消费数据",
        "benefit_sectors": ["电商", "物流", "消费电子"],
        "leading_stocks": [
            {"name": "阿里巴巴", "code": "09988.HK", "reason": "618GMV增长"},
            {"name": "顺丰控股", "code": "002352.SZ", "reason": "物流需求激增"},
        ],
    },
    {
        "date": "2026-06-20",
        "title": "政治局会议（6月）",
        "type": "meeting",
        "level": "major",
        "description": "半年度政治局会议，重磅政策窗口",
        "benefit_sectors": ["政策受益板块"],
        "leading_stocks": [],
    },
    {
        "date": "2026-06-30",
        "title": "半年度收官",
        "type": "market",
        "level": "moderate",
        "description": "上半年最后一个交易日，关注机构调仓和半年度策略",
        "benefit_sectors": [],
        "leading_stocks": [],
    },
    # ===== 2026年7月 =====
    {
        "date": "2026-07-01",
        "title": "建党节",
        "type": "meeting",
        "level": "minor",
        "description": "建党纪念日，关注相关政策表述",
        "benefit_sectors": ["军工", "国企"],
        "leading_stocks": [],
    },
    {
        "date": "2026-07-10",
        "title": "6月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "6月物价数据",
        "benefit_sectors": ["消费"],
        "leading_stocks": [],
    },
    {
        "date": "2026-07-15",
        "title": "二季度GDP数据",
        "type": "economic_data",
        "level": "major",
        "description": "上半年GDP增速发布，关注经济复苏力度",
        "benefit_sectors": ["顺周期", "金融", "消费"],
        "leading_stocks": [
            {"name": "中国平安", "code": "601318.SH", "reason": "经济复苏利好保险"},
        ],
    },
    {
        "date": "2026-07-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "7月LPR公布",
        "benefit_sectors": ["地产", "券商"],
        "leading_stocks": [],
    },
    {
        "date": "2026-07-25",
        "title": "政治局会议（7月）",
        "type": "meeting",
        "level": "major",
        "description": "年中最重要的政治局会议，部署下半年经济工作",
        "benefit_sectors": ["政策受益板块"],
        "leading_stocks": [],
    },
    # ===== 2026年8月 =====
    {
        "date": "2026-08-01",
        "title": "建军节",
        "type": "meeting",
        "level": "minor",
        "description": "建军纪念日，关注军工政策",
        "benefit_sectors": ["军工"],
        "leading_stocks": [
            {"name": "航发动力", "code": "600893.SH", "reason": "军工订单预期"},
        ],
    },
    {
        "date": "2026-08-10",
        "title": "7月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "7月物价数据",
        "benefit_sectors": ["消费"],
        "leading_stocks": [],
    },
    {
        "date": "2026-08-15",
        "title": "MLF续作",
        "type": "policy",
        "level": "moderate",
        "description": "央行MLF续作",
        "benefit_sectors": ["金融"],
        "leading_stocks": [],
    },
    {
        "date": "2026-08-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "8月LPR公布",
        "benefit_sectors": ["地产"],
        "leading_stocks": [],
    },
    {
        "date": "2026-08-31",
        "title": "中报披露截止",
        "type": "earnings",
        "level": "major",
        "description": "A股上市公司2026年半年报披露截止日",
        "benefit_sectors": ["业绩超预期板块"],
        "leading_stocks": [],
    },
    # ===== 2026年9月 =====
    {
        "date": "2026-09-03",
        "title": "抗战胜利纪念日",
        "type": "meeting",
        "level": "minor",
        "description": "纪念活动，关注军工板块",
        "benefit_sectors": ["军工"],
        "leading_stocks": [],
    },
    {
        "date": "2026-09-10",
        "title": "8月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "8月物价数据",
        "benefit_sectors": ["消费"],
        "leading_stocks": [],
    },
    {
        "date": "2026-09-15",
        "title": "三季度GDP预告",
        "type": "economic_data",
        "level": "moderate",
        "description": "三季度经济数据前瞻",
        "benefit_sectors": ["顺周期"],
        "leading_stocks": [],
    },
    {
        "date": "2026-09-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "9月LPR公布",
        "benefit_sectors": ["地产"],
        "leading_stocks": [],
    },
    # ===== 2026年10月 =====
    {
        "date": "2026-10-01",
        "title": "国庆节",
        "type": "market",
        "level": "major",
        "description": "国庆长假，关注假期消费数据和政策动向",
        "benefit_sectors": ["旅游", "零售", "影视"],
        "leading_stocks": [
            {"name": "宋城演艺", "code": "300144.SZ", "reason": "假期旅游旺季"},
        ],
    },
    {
        "date": "2026-10-15",
        "title": "三季度GDP数据",
        "type": "economic_data",
        "level": "major",
        "description": "前三季度GDP增速发布",
        "benefit_sectors": ["金融", "消费", "制造"],
        "leading_stocks": [],
    },
    {
        "date": "2026-10-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "10月LPR公布",
        "benefit_sectors": ["地产"],
        "leading_stocks": [],
    },
    {
        "date": "2026-10-25",
        "title": "政治局会议（10月）",
        "type": "meeting",
        "level": "major",
        "description": "四季度政治局会议",
        "benefit_sectors": ["政策受益板块"],
        "leading_stocks": [],
    },
    # ===== 2026年11月 =====
    {
        "date": "2026-11-10",
        "title": "10月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "10月物价数据",
        "benefit_sectors": ["消费"],
        "leading_stocks": [],
    },
    {
        "date": "2026-11-11",
        "title": "双十一购物节",
        "type": "market",
        "level": "moderate",
        "description": "电商大促",
        "benefit_sectors": ["电商", "物流", "快递"],
        "leading_stocks": [
            {"name": "京东集团", "code": "09618.HK", "reason": "双十一GMV"},
        ],
    },
    {
        "date": "2026-11-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "11月LPR公布",
        "benefit_sectors": ["地产"],
        "leading_stocks": [],
    },
    # ===== 2026年12月 =====
    {
        "date": "2026-12-10",
        "title": "11月CPI/PPI数据",
        "type": "economic_data",
        "level": "major",
        "description": "11月物价数据",
        "benefit_sectors": ["消费"],
        "leading_stocks": [],
    },
    {
        "date": "2026-12-15",
        "title": "中央经济工作会议",
        "type": "meeting",
        "level": "major",
        "description": "年度最重要的经济会议，定调2027年经济政策",
        "benefit_sectors": ["政策受益板块", "新质生产力", "消费"],
        "leading_stocks": [
            {"name": "中国软件", "code": "600536.SH", "reason": "信创政策预期"},
        ],
    },
    {
        "date": "2026-12-20",
        "title": "LPR利率决议",
        "type": "policy",
        "level": "major",
        "description": "12月LPR公布",
        "benefit_sectors": ["地产"],
        "leading_stocks": [],
    },
    {
        "date": "2026-12-31",
        "title": "年度收官",
        "type": "market",
        "level": "moderate",
        "description": "全年最后一个交易日，关注机构调仓和跨年行情",
        "benefit_sectors": [],
        "leading_stocks": [],
    },
]


# ===== 动态事件生成 =====

async def fetch_dynamic_events() -> list[dict]:
    """从外部 API 获取动态投资日历事件

    当前为占位实现，返回空列表。
    后续可接入金十数据/华尔街见闻等 API。

    返回格式与静态事件一致。
    """
    # TODO: 接入外部 API
    # 示例：金十数据日历 API
    # url = "https://cdn.jin10.com/data_center/calender..."
    # 解析返回数据，转换为标准格式
    return []


# ===== 聚合查询 =====

def get_events(
    start_date: str | None = None,
    end_date: str | None = None,
    level: str | None = None,
    event_type: str | None = None,
) -> list[dict]:
    """获取聚合后的投资日历事件

    参数:
        start_date: 开始日期 YYYY-MM-DD，默认今天
        end_date: 结束日期 YYYY-MM-DD，默认 +90 天
        level: 按级别过滤 major/moderate/minor
        event_type: 按类型过滤 meeting/policy/economic_data/earnings/market

    返回:
        排序后的事件列表
    """
    if start_date is None:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if end_date is None:
        end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

    # 过滤静态事件
    events = []
    for event in INVESTMENT_CALENDAR_STATIC:
        if not (start_date <= event["date"] <= end_date):
            continue
        if level and event["level"] != level:
            continue
        if event_type and event["type"] != event_type:
            continue
        events.append({**event, "source": "static"})

    # 按日期排序
    events.sort(key=lambda x: x["date"])
    return events


async def get_all_events(
    start_date: str | None = None,
    end_date: str | None = None,
    level: str | None = None,
    event_type: str | None = None,
) -> list[dict]:
    """获取全部事件（含动态 API 拉取）"""
    events = get_events(start_date, end_date, level, event_type)

    # 尝试获取动态事件
    try:
        dynamic = await fetch_dynamic_events()
        for event in dynamic:
            if start_date and event["date"] < start_date:
                continue
            if end_date and event["date"] > end_date:
                continue
            if level and event["level"] != level:
                continue
            if event_type and event["type"] != event_type:
                continue
            event["source"] = "dynamic"
            events.append(event)
    except Exception as exc:
        logger.warning("获取动态投资日历事件失败: %s", exc)

    # 按日期排序
    events.sort(key=lambda x: x["date"])
    return events


def get_event_types() -> list[dict]:
    """获取事件类型元数据"""
    return [
        {"value": "meeting", "label": "重要会议", "color": "var(--color-purple)"},
        {"value": "policy", "label": "政策发布", "color": "var(--color-accent)"},
        {"value": "economic_data", "label": "经济数据", "color": "var(--color-gold)"},
        {"value": "earnings", "label": "财报披露", "color": "var(--color-orange)"},
        {"value": "market", "label": "市场事件", "color": "var(--color-blue)"},
    ]

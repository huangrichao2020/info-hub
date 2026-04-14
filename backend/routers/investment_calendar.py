"""投资日历 API 路由"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from data.investment_calendar import INVESTMENT_CALENDAR

router = APIRouter()


@router.get("/events")
async def get_events(
    start_date: str = Query(default="", description="开始日期 YYYY-MM-DD，默认今天"),
    end_date: str = Query(default="", description="结束日期 YYYY-MM-DD，默认+60天"),
    level: str = Query(default="", description="事件级别：major/moderate/minor，空=全部"),
):
    """获取投资日历事件列表"""
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    events = []
    for evt in INVESTMENT_CALENDAR:
        evt_date = datetime.strptime(evt["date"], "%Y-%m-%d")
        if start_dt <= evt_date <= end_dt:
            if level and evt["level"] != level:
                continue
            events.append(evt)

    # 按日期排序
    events.sort(key=lambda x: x["date"])

    return {"events": events, "count": len(events)}


@router.get("/events/{date}")
async def get_events_by_date(date: str):
    """获取指定日期的事件"""
    events = [evt for evt in INVESTMENT_CALENDAR if evt["date"] == date]
    return {"date": date, "events": events}


@router.get("/types")
async def get_event_types():
    """获取事件类型列表"""
    return {
        "types": [
            {"value": "meeting", "label": "重要会议", "color": "var(--color-purple)"},
            {"value": "policy", "label": "政策发布", "color": "var(--color-accent)"},
            {"value": "economic_data", "label": "经济数据", "color": "var(--color-gold)"},
            {"value": "earnings", "label": "财报披露", "color": "var(--color-orange)"},
            {"value": "market", "label": "市场事件", "color": "var(--color-blue)"},
        ]
    }

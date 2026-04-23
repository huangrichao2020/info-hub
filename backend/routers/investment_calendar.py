"""投资日历 API 路由"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from data.investment_calendar import get_all_events, get_events, get_event_types

router = APIRouter()


@router.get("/events")
async def get_events_api(
    start_date: str = Query(default="", description="开始日期 YYYY-MM-DD，默认今天"),
    end_date: str = Query(default="", description="结束日期 YYYY-MM-DD，默认+90天"),
    level: str = Query(default="", description="事件级别：major/moderate/minor，空=全部"),
    event_type: str = Query(default="", description="事件类型：meeting/policy/economic_data/earnings/market"),
    include_dynamic: bool = Query(default=False, description="是否包含动态API拉取的事件"),
):
    """获取投资日历事件列表"""
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

    if include_dynamic:
        events = await get_all_events(
            start_date=start_date,
            end_date=end_date,
            level=level if level else None,
            event_type=event_type if event_type else None,
        )
    else:
        events = get_events(
            start_date=start_date,
            end_date=end_date,
            level=level if level else None,
            event_type=event_type if event_type else None,
        )

    return {"events": events, "count": len(events)}


@router.get("/events/{date}")
async def get_events_by_date(date: str):
    """获取指定日期的事件"""
    events = get_events(start_date=date, end_date=date)
    return {"date": date, "events": events}


@router.get("/types")
async def get_event_types_api():
    """获取事件类型列表"""
    return {"types": get_event_types()}

"""
每日 S/A/B 机会扫描器
=====================

- S 级 (1-3 只): 卡脖子定位明确 + 当日异动 + 短期催化剂 → 重点详细讲解
- A 级 (3-5 只): 卡脖子定位 + 板块强势 → 简略分析
- B 级 (5-10 只): 板块异动/资金关注 → 参考清单

设计哲学:
- 每日扫描 29 只卡脖子标的 + 候选主线龙头
- 基于 Serenity 框架的卡脖子评分 × 当日市场信号 综合评级
- 输出可直接给用户做决策的简报

数据源:
- fetch_full_snapshot() - 当日市场快照
- run_screening() - 主线 + 候选股
- ChokePointAnalyzer - 卡脖子评分库
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

from .trading_data_service import (
    fetch_full_snapshot,
    fetch_stock_detail,
    get_today_str,
    is_trade_time,
)
from .choke_point_analyzer import get_choke_analyzer


# ===== 29 只卡脖子核心标的池（来自 Serenity 卡脖子框架 v2.0）=====
CHOKEPOINT_POOL = [
    # 赛道 1: 磷化铟+锗
    {"code": "002428", "name": "云南锗业", "track": "磷化铟+锗", "score": 9.0, "logic": "6英寸InP国内唯一 + 锗资源管制"},
    {"code": "600206", "name": "有研新材", "track": "磷化铟+锗", "score": 8.0, "logic": "靶材 + 稀土 + InP 第二梯队"},
    {"code": "300566", "name": "光智科技", "track": "磷化铟+锗", "score": 7.0, "logic": "军工红外锗镜片核心"},
    # 赛道 2: 电子特气
    {"code": "688146", "name": "中船特气", "track": "电子特气", "score": 9.0, "logic": "WF6 全球第一 + 7N 级唯一"},
    {"code": "600378", "name": "昊华科技", "track": "电子特气", "score": 8.0, "logic": "电子特气综合龙头 + 央企"},
    {"code": "688268", "name": "华特气体", "track": "电子特气", "score": 8.0, "logic": "20+ 特气突破 + 国产替代先锋"},
    # 赛道 3: NOR Flash
    {"code": "603986", "name": "兆易创新", "track": "NOR Flash", "score": 8.5, "logic": "NOR 全球第二 23.2%"},
    {"code": "688766", "name": "普冉股份", "track": "NOR Flash", "score": 7.0, "logic": "中小容量 NOR + EEPROM"},
    {"code": "688525", "name": "佰维存储", "track": "NOR Flash", "score": 7.0, "logic": "嵌入式 + 工业存储专精"},
    # 赛道 4: 机器人零部件
    {"code": "688017", "name": "绿的谐波", "track": "机器人零部件", "score": 8.0, "logic": "谐波减速器全球第二"},
    {"code": "002747", "name": "埃斯顿", "track": "机器人零部件", "score": 7.5, "logic": "国产工业机器人本体第一"},
    {"code": "601689", "name": "拓普集团", "track": "机器人零部件", "score": 8.0, "logic": "特斯拉 Optimus 供应链"},
    # 赛道 5: 半导体设备
    {"code": "002371", "name": "北方华创", "track": "半导体设备", "score": 9.0, "logic": "平台型龙头 + 十五五重点"},
    {"code": "688012", "name": "中微公司", "track": "半导体设备", "score": 9.0, "logic": "刻蚀机龙头 + 5nm"},
    {"code": "688082", "name": "盛美上海", "track": "半导体设备", "score": 8.0, "logic": "清洗设备龙头 + 海力士背书"},
    {"code": "688072", "name": "拓荆科技", "track": "半导体设备", "score": 8.0, "logic": "PECVD + 涂胶显影国产替代"},
    # 赛道 6: 半导体材料
    {"code": "300346", "name": "南大光电", "track": "半导体材料", "score": 9.0, "logic": "ArF 光刻胶国内唯一量产"},
    {"code": "300666", "name": "江丰电子", "track": "半导体材料", "score": 8.5, "logic": "靶材全球领先 + 3nm"},
    {"code": "300054", "name": "鼎龙股份", "track": "半导体材料", "score": 8.0, "logic": "CMP 抛光垫国产唯一"},
    {"code": "688019", "name": "安集科技", "track": "半导体材料", "score": 8.0, "logic": "CMP 抛光液龙头 + 毛利率56%"},
    {"code": "603650", "name": "彤程新材", "track": "半导体材料", "score": 8.0, "logic": "KrF 国内唯一 + ArF 推进中"},
    {"code": "002916", "name": "深南电路", "track": "半导体材料", "score": 8.0, "logic": "ABF 载板 + AI 服务器 PCB"},
    {"code": "002409", "name": "雅克科技", "track": "半导体材料", "score": 7.5, "logic": "电子特气 + 光刻胶综合平台"},
    # 赛道 7: 碳化硅+远期
    {"code": "688234", "name": "天岳先进", "track": "碳化硅+远期", "score": 8.0, "logic": "8 英寸 SiC 衬底龙头"},
    {"code": "600703", "name": "三安光电", "track": "碳化硅+远期", "score": 7.5, "logic": "SiC + GaN IDM 全栈"},
    {"code": "002617", "name": "露笑科技", "track": "碳化硅+远期", "score": 7.0, "logic": "SiC 衬底产能快速释放"},
    {"code": "688295", "name": "中复神鹰", "track": "碳化硅+远期", "score": 8.0, "logic": "T1200 碳纤维全球首发"},
    {"code": "300699", "name": "光威复材", "track": "碳化硅+远期", "score": 8.0, "logic": "军工碳纤维龙头"},
    {"code": "600456", "name": "宝钛股份", "track": "碳化硅+远期", "score": 8.0, "logic": "航空钛材市占率 90%"},
]


# ===== 主线方向关键词映射 =====
SECTOR_TO_TRACK = {
    "半导体": ["电子特气", "NOR Flash", "半导体设备", "半导体材料"],
    "芯片": ["电子特气", "NOR Flash", "半导体设备", "半导体材料"],
    "光通信": ["磷化铟+锗"],
    "光模块": ["磷化铟+锗"],
    "AI算力": ["磷化铟+锗", "半导体设备", "半导体材料"],
    "机器人": ["机器人零部件"],
    "人形机器人": ["机器人零部件"],
    "碳化硅": ["碳化硅+远期"],
    "SiC": ["碳化硅+远期"],
    "军工": ["碳化硅+远期"],
    "碳纤维": ["碳化硅+远期"],
    "钛合金": ["碳化硅+远期"],
}


def _get_track_from_sector(sector_name: str) -> Optional[str]:
    """从板块名映射到卡脖子赛道"""
    for keyword, tracks in SECTOR_TO_TRACK.items():
        if keyword in sector_name:
            return tracks[0]  # 取第一个匹配
    return None


def _grade_stock(
    stock: Dict[str, Any],
    main_lines: List[Dict[str, Any]],
    hot_sectors: List[str],
    trade_time: bool,
) -> Dict[str, Any]:
    """
    给单只股打 S/A/B 等级

    S 级标准:
      - 卡脖子评分 >= 8.5
      - 所属赛道在今日主线方向中
      - 当日板块异动或资金关注

    A 级标准:
      - 卡脖子评分 >= 7.5
      - 板块有资金净流入或近期活跃

    B 级标准:
      - 卡脖子评分 >= 6.5
      - 仅供参考的标的
    """
    code = stock["code"]
    name = stock["name"]
    track = stock["track"]
    choke_score = stock["score"]

    # 检查是否在主线
    main_line_match = False
    main_line_rank = -1
    for i, ml in enumerate(main_lines[:5]):  # Top 5 主线
        ml_track = _get_track_from_sector(ml.get("name", "") if isinstance(ml, dict) else str(ml))
        if ml_track == track:
            main_line_match = True
            main_line_rank = i
            break

    # 检查板块联动
    sector_active = track in hot_sectors or any(
        _get_track_from_sector(s) == track for s in hot_sectors
    )

    signals = []
    if main_line_match:
        signals.append(f"主线#{main_line_rank + 1} 命中")
    if sector_active:
        signals.append("板块联动")

    # S 级: 卡脖子 8.5+ + 主线/板块
    if choke_score >= 8.5 and (main_line_match or sector_active):
        return {
            "grade": "S",
            "score": choke_score,
            "reason": f"卡脖子高评分({choke_score}) + {'主线命中' if main_line_match else '板块联动'}",
            "signals": signals,
            "action": "重点关注: 可在开盘后 30 分钟内观察回踩介入",
        }
    # S 级: 卡脖子 9+ 即使无主线（顶级标的任何时候都值得跟踪）
    elif choke_score >= 9.0:
        return {
            "grade": "S",
            "score": choke_score,
            "reason": f"顶级卡脖子标的({choke_score})，长期主线",
            "signals": signals + ["卡脖子顶级标的"],
            "action": "重点关注: 分批建仓的优质标的",
        }
    # A 级: 卡脖子 7.5+ + 板块信号
    elif choke_score >= 7.5 and (main_line_match or sector_active):
        return {
            "grade": "A",
            "score": choke_score,
            "reason": f"卡脖子稳定({choke_score}) + {'主线' if main_line_match else '板块活跃'}",
            "signals": signals,
            "action": "可观察: 等待板块二次确认或回踩机会",
        }
    # A 级: 卡脖子 8+（无主线但位置好）
    elif choke_score >= 8.0:
        return {
            "grade": "A",
            "score": choke_score,
            "reason": f"卡脖子高评分({choke_score})",
            "signals": signals,
            "action": "可观察: 长期跟踪，等待催化",
        }
    # B 级: 其他
    else:
        return {
            "grade": "B",
            "score": choke_score,
            "reason": f"卡脖子参考({choke_score})",
            "signals": signals,
            "action": "参考: 仅作板块联动观察",
        }


def scan_daily_chance() -> Dict[str, Any]:
    """
    每日 S/A/B 机会扫描

    Returns:
        {
            "date": "2026-06-29",
            "is_trade_time": True,
            "market": {
                "indices": [...],
                "main_lines": [...]
            },
            "S": [...],  # 1-3 只详细分析
            "A": [...],  # 3-5 只简略
            "B": [...],  # 5-10 只参考
        }
    """
    trade_time = is_trade_time()
    snapshot = fetch_full_snapshot() or {}

    # 主线方向
    main_lines = snapshot.get("main_lines", [])[:5]

    # 强势板块
    sector_data = snapshot.get("sectors", [])
    hot_sectors = []
    for s in sector_data[:10]:  # Top 10 板块
        if isinstance(s, dict):
            name = s.get("name", "")
            if name:
                hot_sectors.append(name)

    # 给每只卡脖子股打分
    graded = []
    for stock in CHOKEPOINT_POOL:
        grade_info = _grade_stock(stock, main_lines, hot_sectors, trade_time)
        graded.append({
            "code": stock["code"],
            "name": stock["name"],
            "track": stock["track"],
            "choke_score": stock["score"],
            "logic": stock["logic"],
            **grade_info,
        })

    # 排序 + 分类
    s_chances = [g for g in graded if g["grade"] == "S"]
    a_chances = [g for g in graded if g["grade"] == "A"]
    b_chances = [g for g in graded if g["grade"] == "B"]

    # 按卡脖子评分排序
    s_chances.sort(key=lambda x: -x["choke_score"])
    a_chances.sort(key=lambda x: -x["choke_score"])
    b_chances.sort(key=lambda x: -x["choke_score"])

    # 限制数量
    s_chances = s_chances[:3]
    a_chances = a_chances[:5]
    b_chances = b_chances[:10]

    return {
        "date": get_today_str(),
        "is_trade_time": trade_time,
        "market": {
            "indices": snapshot.get("indices", [])[:5],
            "main_lines": main_lines,
            "hot_sectors": hot_sectors[:5],
            "zt_count": snapshot.get("zt_count", 0),
        },
        "S": s_chances,
        "A": a_chances,
        "B": b_chances,
        "stats": {
            "total_pool": len(CHOKEPOINT_POOL),
            "s_count": len(s_chances),
            "a_count": len(a_chances),
            "b_count": len(b_chances),
        },
    }


def get_stock_detail_for_chance(code: str) -> Dict[str, Any]:
    """获取 S 级机会的详细数据（含 K 线）"""
    try:
        detail = fetch_stock_detail(code)
        kline = []
        try:
            kline = fetch_historical_kline_safe(code, days=60)
        except Exception:
            pass

        # 找对应的卡脖子数据
        choke_analyzer = get_choke_analyzer()
        choke_data = None
        if code in choke_analyzer.known_codes:
            choke_data = choke_analyzer.get_choke_data(code)

        return {
            "code": code,
            "detail": detail,
            "kline": kline[-30:] if kline else [],  # 最近30个交易日
            "choke_data": choke_data,
        }
    except Exception as e:
        return {"code": code, "error": str(e)}


def fetch_historical_kline_safe(code: str, days: int = 60) -> List[Dict]:
    """安全获取历史 K 线"""
    try:
        from .trading_data_service import fetch_historical_kline
        return fetch_historical_kline(code, days)
    except Exception:
        return []


# CLI 测试入口
if __name__ == "__main__":
    import json
    result = scan_daily_chance()
    print(json.dumps(result, ensure_ascii=False, indent=2))
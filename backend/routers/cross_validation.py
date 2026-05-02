"""
交叉验证 API 端点
将 llm/cross_validator.py 的 5 视角分析框架暴露为 REST API。
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import os
import pandas as pd
from datetime import datetime

from llm.cross_validator import CrossValidator

router = APIRouter(prefix="", tags=["交叉验证"])
logger = logging.getLogger("info-hub.cross_validation")

validator = CrossValidator()


class CrossValidationRequest(BaseModel):
    """交叉验证请求体（可选覆盖自动获取的市场数据）"""
    volume_change: Optional[float] = None
    north_flow: Optional[float] = None
    limit_up: Optional[int] = None
    limit_down: Optional[int] = None
    sentiment: Optional[str] = None
    consecutive_ban: Optional[int] = None
    yesterday_premium: Optional[float] = None
    index_trend: Optional[str] = None
    ma_alignment: Optional[bool] = None
    divergence: Optional[bool] = None
    main_theme: Optional[str] = None
    theme_limit_up: Optional[int] = None
    theme_tiers: Optional[int] = None
    dragon_head_status: Optional[str] = None
    policy: Optional[str] = None
    us_market: Optional[str] = None
    exchange_rate_change: Optional[float] = None


@router.get("/cross-validation")
async def get_cross_validation():
    """
    获取当前市场多视角交叉验证结果。
    自动从 Parquet 缓存聚合最新市场数据，调用 5 视角分析框架。
    """
    market_data = _build_market_data_from_cache()
    result = validator.analyze(market_data)
    return validator.to_dict(result)


@router.post("/cross-validation")
async def post_cross_validation(req: CrossValidationRequest):
    """
    自定义市场数据进行交叉验证。
    允许外部系统传入特定市场快照进行分析。
    """
    market_data = req.model_dump(exclude_none=True)
    # 填充默认值
    defaults = {
        "volume_change": 0, "north_flow": 0, "limit_up": 0, "limit_down": 0,
        "sentiment": "neutral", "consecutive_ban": 0, "yesterday_premium": 0,
        "index_trend": "sideways", "ma_alignment": False, "divergence": False,
        "main_theme": "", "theme_limit_up": 0, "theme_tiers": 0,
        "dragon_head_status": "strong", "policy": "neutral",
        "us_market": "flat", "exchange_rate_change": 0,
    }
    for k, v in defaults.items():
        market_data.setdefault(k, v)
    
    result = validator.analyze(market_data)
    return validator.to_dict(result)


def _build_market_data_from_cache() -> dict:
    """
    从本地 Parquet 缓存 + 东方财富 API 聚合市场数据。
    优先使用真实数据，失败时降级到默认值。
    """
    from services.stock_engine import get_engine
    from services.market_data_service import fetch_market_snapshot
    
    # 尝试获取真实市场快照
    try:
        real_data = fetch_market_snapshot()
        if real_data.get("fetched_at"):
            logger.info(f"使用真实市场数据 (更新时间：{real_data['fetched_at']})")
            # 合并 Parquet 计算的指标
            engine = get_engine()
            data_dir = engine.data_dir
            if os.path.exists(data_dir):
                files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
                if files:
                    # 采样计算 volume_change 和 ma_alignment
                    sample_files = files[:100]
                    volume_changes = []
                    ma_aligned = 0
                    total = 0
                    
                    for f in sample_files:
                        try:
                            path = os.path.join(data_dir, f)
                            df = pd.read_parquet(path, columns=['date', 'close', 'volume'])
                            if len(df) < 26:
                                continue
                            
                            total += 1
                            vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(25).mean().iloc[-1]
                            if pd.notna(vol_ratio) and vol_ratio > 0:
                                volume_changes.append((vol_ratio - 1) * 100)
                            
                            ma25 = df['close'].rolling(25).mean().iloc[-1]
                            if df['close'].iloc[-1] > ma25:
                                ma_aligned += 1
                        except Exception:
                            continue
                    
                    if volume_changes:
                        real_data['volume_change'] = sum(volume_changes) / len(volume_changes)
                    real_data['ma_alignment'] = ma_aligned > total * 0.6 if total > 0 else False
                    real_data['index_trend'] = "up" if ma_aligned > total * 0.6 else "sideways"
            
            return real_data
    except Exception as e:
        logger.warning(f"真实数据获取失败，降级到默认值：{e}")
    
    # 降级到默认值
    return _get_default_market_data()


def _get_default_market_data() -> dict:
    """无数据时的默认市场快照"""
    return {
        "volume_change": 0, "north_flow": 0, "limit_up": 0, "limit_down": 0,
        "sentiment": "neutral", "consecutive_ban": 0, "yesterday_premium": 0,
        "index_trend": "sideways", "ma_alignment": False, "divergence": False,
        "main_theme": "", "theme_limit_up": 0, "theme_tiers": 0,
        "dragon_head_status": "strong", "policy": "neutral",
        "us_market": "flat", "exchange_rate_change": 0,
    }

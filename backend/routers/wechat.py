"""
微信公众号搜索 API 路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, Depends
from database import get_db
from services.wechat_crud import WechatCRUD

logger = logging.getLogger("info-hub.wechat-api")

router = APIRouter(prefix="/api/wechat", tags=["微信公众号搜索"])


@router.get("/search")
def search_articles(
    q: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类（股票、复盘、盘前、热点）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
):
    """
    搜索公众号文章
    - **q**: 搜索关键词，支持标题和摘要模糊搜索
    - **category**: 按分类过滤
    - **page**: 页码，从1开始
    - **page_size**: 每页数量，最大100
    """
    return WechatCRUD.search_articles(
        db_conn=db,
        keyword=q,
        category=category,
        page=page,
        page_size=page_size,
    )


@router.get("/accounts/{account_id}/articles")
def get_account_articles(
    account_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """
    获取特定公众号的文章列表
    - **account_id**: 公众号ID
    - **page**: 页码
    - **page_size**: 每页数量
    """
    return WechatCRUD.get_articles_by_account(
        db_conn=db,
        account_id=account_id,
        page=page,
        page_size=page_size,
    )


@router.get("/accounts/{account_id}")
def get_account(
    account_id: int,
    db=Depends(get_db),
):
    """
    获取公众号详情
    - **account_id**: 公众号ID
    """
    account = WechatCRUD.get_account_by_id(db, account_id)
    if not account:
        return {"error": "公众号不存在"}
    return account


@router.get("/trending-topics")
def get_trending_topics(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
):
    """
    获取热门话题
    - **limit**: 返回数量限制
    """
    return WechatCRUD.get_trending_topics(db, limit=limit)


@router.get("/recommended-accounts")
def get_recommended_accounts(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
):
    """
    获取推荐公众号
    - **limit**: 返回数量限制
    """
    return WechatCRUD.get_recommended_accounts(db, limit=limit)


@router.get("/categories")
def get_categories(db=Depends(get_db)):
    """获取所有文章分类"""
    categories = WechatCRUD.get_categories(db)
    return {"categories": categories}


@router.get("/statistics")
def get_statistics(db=Depends(get_db)):
    """获取统计信息"""
    return WechatCRUD.get_statistics(db)


@router.post("/cleanup")
def cleanup_old_articles(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
):
    """
    清理旧文章
    - **days**: 清理超过多少天的文章
    """
    deleted = WechatCRUD.cleanup_old_articles(db, days=days)
    return {"deleted": deleted, "message": f"清理了 {deleted} 篇超过 {days} 天的文章"}

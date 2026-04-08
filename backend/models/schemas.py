"""Pydantic 请求/响应模型"""
from pydantic import BaseModel


class ArticleRequest(BaseModel):
    topic: str
    platform: str = "wechat"  # wechat | toutiao | zhihu
    reference_material: str = ""
    style: str = "informative"
    word_count: int = 2000


class PortfolioItem(BaseModel):
    code: str
    name: str
    shares: int
    cost_price: float


class ReviewRequest(BaseModel):
    portfolio: list[PortfolioItem]
    date: str = ""

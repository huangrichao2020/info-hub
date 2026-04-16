from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class OfficialAccount(Base):
    __tablename__ = 'official_accounts'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    wechat_id = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    avatar_url = Column(String(500))
    created_at = Column(DateTime)

    articles = relationship("Article", back_populates="official_account")

class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    url = Column(String(500))
    author = Column(String(255))
    publish_date = Column(DateTime)
    official_account_id = Column(Integer, ForeignKey('official_accounts.id'))

    official_account = relationship("OfficialAccount", back_populates="articles")
    keywords = relationship("ArticleKeyword", back_populates="article")

class Keyword(Base):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)
    word = Column(String(100), unique=True, nullable=False)

    articles = relationship("ArticleKeyword", back_populates="keyword")

class ArticleKeyword(Base):
    __tablename__ = 'article_keywords'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    keyword_id = Column(Integer, ForeignKey('keywords.id'))

    article = relationship("Article", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="articles")
-- WeChat Official Account Tables Migration
-- 用于微信公众号搜索功能的数据库表

-- 公众号表
CREATE TABLE IF NOT EXISTS official_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    wechat_id VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    avatar_url VARCHAR(500),
    article_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 文章表
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    summary TEXT,
    url VARCHAR(500) UNIQUE,
    author VARCHAR(255),
    publish_date DATETIME,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    official_account_id INTEGER,
    keywords JSON,
    FOREIGN KEY (official_account_id) REFERENCES official_accounts(id)
);

-- 关键词表
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) DEFAULT '其他',
    priority INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 文章关键词关联表
CREATE TABLE IF NOT EXISTS article_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER,
    keyword_id INTEGER,
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_official_accounts_wechat_id ON official_accounts(wechat_id);
CREATE INDEX IF NOT EXISTS idx_official_accounts_status ON official_accounts(status);
CREATE INDEX IF NOT EXISTS idx_articles_official_account_id ON articles(official_account_id);
CREATE INDEX IF NOT EXISTS idx_articles_publish_date ON articles(publish_date);
CREATE INDEX IF NOT EXISTS idx_articles_crawled_at ON articles(crawled_at);
CREATE INDEX IF NOT EXISTS idx_keywords_word ON keywords(word);
CREATE INDEX IF NOT EXISTS idx_keywords_category ON keywords(category);
CREATE INDEX IF NOT EXISTS idx_article_keywords_article_id ON article_keywords(article_id);
CREATE INDEX IF NOT EXISTS idx_article_keywords_keyword_id ON article_keywords(keyword_id);

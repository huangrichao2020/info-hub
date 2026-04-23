import { useState, useEffect, useCallback } from 'react'
import { Search, TrendingUp, MessageCircle, Clock, ExternalLink, BarChart3 } from 'lucide-react'
import * as wechatApi from '../../api/wechat'
import type { WechatArticle, WechatAccount, WechatTrendingTopic, WechatStatistics } from '../../types'

export default function WechatSearchPanel() {
  const [keyword, setKeyword] = useState('')
  const [articles, setArticles] = useState<WechatArticle[]>([])
  const [accounts, setAccounts] = useState<WechatAccount[]>([])
  const [trendingTopics, setTrendingTopics] = useState<WechatTrendingTopic[]>([])
  const [statistics, setStatistics] = useState<WechatStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [categories, setCategories] = useState<string[]>([])

  // 加载初始数据
  useEffect(() => {
    loadInitialData()
  }, [])

  // 加载搜索
  useEffect(() => {
    if (keyword || selectedCategory) {
      searchArticles(1)
    }
  }, [keyword, selectedCategory])

  const loadInitialData = async () => {
    try {
      const [accountsRes, topicsRes, statsRes, categoriesRes] = await Promise.all([
        wechatApi.getRecommendedAccounts(10),
        wechatApi.getTrendingTopics(10),
        wechatApi.getStatistics(),
        wechatApi.getCategories(),
      ])
      setAccounts(accountsRes)
      setTrendingTopics(topicsRes)
      setStatistics(statsRes)
      setCategories(categoriesRes)
    } catch (error) {
      console.error('加载初始数据失败:', error)
    }
  }

  const searchArticles = async (pageNum: number) => {
    setLoading(true)
    try {
      const result = await wechatApi.searchArticles({
        q: keyword || undefined,
        category: selectedCategory || undefined,
        page: pageNum,
        page_size: 20,
      })
      setArticles(result.articles)
      setTotal(result.total)
      setPages(result.pages)
      setPage(pageNum)
    } catch (error) {
      console.error('搜索失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = useCallback(() => {
    searchArticles(1)
  }, [keyword, selectedCategory])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '未知'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatTimeAgo = (dateStr: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffHours < 1) return '刚刚'
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return formatDate(dateStr)
  }

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      {/* 顶部标题和统计 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <MessageCircle size={28} />
          公众号搜索
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>
          搜索微信公众号文章，获取交易复盘、市场分析和投资资讯
        </p>
      </div>

      {/* 统计卡片 */}
      {statistics && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 16,
          marginBottom: 24,
        }}>
          <div style={statCardStyle}>
            <BarChart3 size={24} color="var(--color-accent)" />
            <div>
              <div style={{ fontSize: 28, fontWeight: 600 }}>{statistics.total_articles}</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>文章总数</div>
            </div>
          </div>
          <div style={statCardStyle}>
            <MessageCircle size={24} color="var(--color-green)" />
            <div>
              <div style={{ fontSize: 28, fontWeight: 600 }}>{statistics.total_accounts}</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>公众号数</div>
            </div>
          </div>
          <div style={statCardStyle}>
            <Clock size={24} color="var(--color-orange)" />
            <div>
              <div style={{ fontSize: 28, fontWeight: 600 }}>{statistics.recent_articles_7d}</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>近7天新增</div>
            </div>
          </div>
        </div>
      )}

      {/* 搜索框 */}
      <div style={{
        background: 'var(--color-surface)',
        borderRadius: 12,
        padding: 20,
        marginBottom: 24,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={20} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-secondary)' }} />
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="搜索文章标题、关键词..."
              style={{
                width: '100%',
                padding: '12px 12px 12px 40px',
                borderRadius: 8,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg)',
                fontSize: 14,
                outline: 'none',
              }}
            />
          </div>
          <button
            onClick={handleSearch}
            style={{
              padding: '12px 24px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--color-accent)',
              color: 'white',
              fontSize: 14,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            搜索
          </button>
        </div>

        {/* 分类过滤 */}
        {categories.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              onClick={() => setSelectedCategory('')}
              style={{
                padding: '6px 12px',
                borderRadius: 6,
                border: '1px solid var(--color-border)',
                background: !selectedCategory ? 'var(--color-accent)' : 'transparent',
                color: !selectedCategory ? 'white' : 'var(--color-text)',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              全部
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                  background: selectedCategory === cat ? 'var(--color-accent)' : 'transparent',
                  color: selectedCategory === cat ? 'white' : 'var(--color-text)',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                {cat}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24 }}>
        {/* 左侧文章列表 */}
        <div>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-secondary)' }}>
              加载中...
            </div>
          ) : articles.length > 0 ? (
            <>
              <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--color-text-secondary)' }}>
                找到 {total} 篇文章
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {articles.map((article) => (
                  <article
                    key={article.id}
                    style={{
                      background: 'var(--color-surface)',
                      borderRadius: 12,
                      padding: 20,
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                      transition: 'transform 0.2s, box-shadow 0.2s',
                      cursor: 'pointer',
                    }}
                    onClick={() => window.open(article.url, '_blank')}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)'
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.12)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'
                    }}
                  >
                    <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, lineHeight: 1.4 }}>
                      {article.title}
                    </h3>
                    {article.summary && (
                      <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginBottom: 12, lineHeight: 1.6 }}>
                        {article.summary.length > 200 ? article.summary.slice(0, 200) + '...' : article.summary}
                      </p>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: 'var(--color-text-secondary)' }}>
                      <div style={{ display: 'flex', gap: 16 }}>
                        {article.account_name && (
                          <span>
                            <MessageCircle size={12} style={{ marginRight: 4 }} />
                            {article.account_name}
                          </span>
                        )}
                        {article.publish_date && (
                          <span>
                            <Clock size={12} style={{ marginRight: 4 }} />
                            {formatTimeAgo(article.publish_date)}
                          </span>
                        )}
                      </div>
                      <ExternalLink size={14} />
                    </div>
                  </article>
                ))}
              </div>

              {/* 分页 */}
              {pages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 24 }}>
                  <button
                    onClick={() => searchArticles(page - 1)}
                    disabled={page === 1}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 6,
                      border: '1px solid var(--color-border)',
                      background: page === 1 ? 'var(--color-bg)' : 'var(--color-surface)',
                      cursor: page === 1 ? 'not-allowed' : 'pointer',
                      opacity: page === 1 ? 0.5 : 1,
                    }}
                  >
                    上一页
                  </button>
                  <span style={{ padding: '8px 16px', fontSize: 14 }}>
                    {page} / {pages}
                  </span>
                  <button
                    onClick={() => searchArticles(page + 1)}
                    disabled={page === pages}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 6,
                      border: '1px solid var(--color-border)',
                      background: page === pages ? 'var(--color-bg)' : 'var(--color-surface)',
                      cursor: page === pages ? 'not-allowed' : 'pointer',
                      opacity: page === pages ? 0.5 : 1,
                    }}
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          ) : (
            <div style={{
              textAlign: 'center',
              padding: 60,
              color: 'var(--color-text-secondary)',
              background: 'var(--color-surface)',
              borderRadius: 12,
            }}>
              <Search size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
              <p>输入关键词搜索公众号文章</p>
            </div>
          )}
        </div>

        {/* 右侧边栏 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* 热门话题 */}
          {trendingTopics.length > 0 && (
            <div style={{
              background: 'var(--color-surface)',
              borderRadius: 12,
              padding: 20,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <TrendingUp size={20} />
                热门话题
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {trendingTopics.map((topic, index) => (
                  <div
                    key={topic.topic}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '8px 12px',
                      borderRadius: 6,
                      background: index < 3 ? 'var(--color-bg)' : 'transparent',
                      cursor: 'pointer',
                    }}
                    onClick={() => {
                      setKeyword(topic.topic)
                      searchArticles(1)
                    }}
                  >
                    <span style={{ fontSize: 14 }}>{topic.topic}</span>
                    <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                      {topic.count} 篇
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 推荐公众号 */}
          {accounts.length > 0 && (
            <div style={{
              background: 'var(--color-surface)',
              borderRadius: 12,
              padding: 20,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
                推荐公众号
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {accounts.map((account) => (
                  <div
                    key={account.id}
                    style={{
                      padding: 12,
                      borderRadius: 8,
                      background: 'var(--color-bg)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
                      {account.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                      {account.article_count} 篇文章
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const statCardStyle: React.CSSProperties = {
  background: 'var(--color-surface)',
  borderRadius: 12,
  padding: 20,
  display: 'flex',
  alignItems: 'center',
  gap: 16,
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
}

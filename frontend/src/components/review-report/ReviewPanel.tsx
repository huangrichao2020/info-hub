import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { CalendarDays, History, Plus, ShieldCheck, Sparkles, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useStreamResponse } from '../../hooks/useStreamResponse'
import client from '../../api/client'
import type { PortfolioStock, ReviewHistoryItem, ReviewReportDetail } from '../../types'

const SAMPLE_PORTFOLIO: PortfolioStock[] = [
  { code: '600736', name: '苏州高新', shares: 1000, cost_price: 6.58 },
]

const markdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 style={{ fontSize: '2rem', lineHeight: 1.15, letterSpacing: '-0.04em', marginBottom: 18, fontWeight: 800 }}>
      {children}
    </h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 style={{ fontSize: '1.25rem', lineHeight: 1.3, marginTop: 28, marginBottom: 12, fontWeight: 800, paddingLeft: 12, borderLeft: '3px solid var(--color-accent)' }}>
      {children}
    </h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 style={{ fontSize: '1.06rem', lineHeight: 1.35, marginTop: 22, marginBottom: 10, fontWeight: 700 }}>
      {children}
    </h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p style={{ marginBottom: 14, color: 'var(--color-text)', lineHeight: 1.95, fontSize: '1rem' }}>
      {children}
    </p>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul style={{ marginBottom: 18, paddingLeft: 18, display: 'grid', gap: 10 }}>
      {children}
    </ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol style={{ marginBottom: 18, paddingLeft: 22, display: 'grid', gap: 10 }}>
      {children}
    </ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li style={{ color: 'var(--color-text)', lineHeight: 1.85 }}>
      {children}
    </li>
  ),
  hr: () => (
    <hr style={{ border: 'none', borderTop: '1px solid rgba(148,163,184,.18)', margin: '20px 0' }} />
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote style={{ margin: '18px 0', padding: '14px 16px', borderRadius: 14, border: '1px solid rgba(56,189,248,.16)', background: 'rgba(56,189,248,.08)', color: 'var(--color-text)' }}>
      {children}
    </blockquote>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong style={{ color: '#fff', fontWeight: 800 }}>{children}</strong>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code style={{ padding: '2px 6px', borderRadius: 6, background: 'rgba(148,163,184,.14)', fontSize: '.92em' }}>{children}</code>
  ),
} satisfies Parameters<typeof ReactMarkdown>[0]['components']

export default function ReviewPanel() {
  const [portfolio, setPortfolio] = useState<PortfolioStock[]>(SAMPLE_PORTFOLIO)
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [shares, setShares] = useState('')
  const [costPrice, setCostPrice] = useState('')
  const [reviewDate, setReviewDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [latestDate, setLatestDate] = useState<string | null>(null)
  const [historyItems, setHistoryItems] = useState<ReviewHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null)
  const [draftReady, setDraftReady] = useState(false)
  const [draftStatus, setDraftStatus] = useState<'loading' | 'saving' | 'saved' | 'error'>('loading')
  const { content, loading, startStream, reset, hydrate } = useStreamResponse()

  const contentMode = useMemo(() => (selectedHistoryId ? 'history' : 'fresh'), [selectedHistoryId])

  const addStock = () => {
    if (!code || !name) return
    setPortfolio([...portfolio, {
      code: code.trim(),
      name: name.trim(),
      shares: parseInt(shares) || 100,
      cost_price: parseFloat(costPrice) || 0,
    }])
    setCode('')
    setName('')
    setShares('')
    setCostPrice('')
  }

  const removeStock = (i: number) => {
    setPortfolio(portfolio.filter((_, idx) => idx !== i))
  }

  const handleGenerate = () => {
    if (portfolio.length === 0) return
    setSelectedHistoryId(null)
    startStream('/api/review/generate', { portfolio, date: reviewDate })
  }

  const loadHistory = useCallback(async () => {
    setHistoryError('')
    setHistoryLoading(true)
    try {
      const response = await client.get<{ items: ReviewHistoryItem[] }>('/review/history')
      const items = response.data.items || []
      setHistoryItems(items)
      // 自动检测最新可用复盘日期
      if (items.length > 0 && !latestDate) {
        const newest = items[0]?.report_date
        if (newest) {
          setLatestDate(newest)
          // 如果当前日期没有历史数据，自动切换到最新可用日期
          const today = new Date().toISOString().slice(0, 10)
          const hasToday = items.some(item => item.report_date === today)
          if (!hasToday && reviewDate === today) {
            setReviewDate(newest)
          }
        }
      }
    } catch {
      setHistoryError('复盘历史加载失败。')
    } finally {
      setHistoryLoading(false)
    }
  }, [latestDate, reviewDate])

  const openHistory = useCallback(async (id: number) => {
    setHistoryError('')
    try {
      const response = await client.get<ReviewReportDetail>(`/review/history/${id}`)
      hydrate(response.data.report_content || '')
      setSelectedHistoryId(id)
      if (response.data.report_date) {
        setReviewDate(response.data.report_date)
      }
    } catch {
      setHistoryError('复盘详情加载失败。')
    }
  }, [hydrate])

  const loadDraft = useCallback(async () => {
    try {
      const response = await client.get<{ portfolio_json: string; report_date: string }>('/review/draft')
      const parsed = JSON.parse(response.data.portfolio_json || '[]')
      if (Array.isArray(parsed) && parsed.length > 0) {
        setPortfolio(parsed)
      } else {
        setPortfolio(SAMPLE_PORTFOLIO)
      }
      if (response.data.report_date) {
        setReviewDate(response.data.report_date)
      }
      setDraftStatus('saved')
    } catch {
      setPortfolio(SAMPLE_PORTFOLIO)
      setDraftStatus('error')
    } finally {
      setDraftReady(true)
    }
  }, [])

  useEffect(() => {
    void loadHistory()
  }, [loadHistory])

  useEffect(() => {
    void loadDraft()
  }, [loadDraft])

  useEffect(() => {
    if (!loading && content) {
      void loadHistory()
    }
  }, [content, loading, loadHistory])

  useEffect(() => {
    if (!draftReady) return
    const timeout = window.setTimeout(() => {
      setDraftStatus('saving')
      void client.put('/review/draft', { portfolio, date: reviewDate })
        .then(() => setDraftStatus('saved'))
        .catch(() => setDraftStatus('error'))
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [draftReady, portfolio, reviewDate])

  const inputStyle: React.CSSProperties = {
    background: 'var(--color-card)',
    border: '1px solid var(--color-border)',
    borderRadius: 10,
    padding: '8px 14px',
    fontSize: '.84em',
    color: 'var(--color-text)',
    outline: 'none',
    transition: 'border-color .15s',
    fontFamily: 'inherit',
    width: '100%',
    boxSizing: 'border-box',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <section
        style={{
          borderRadius: 20,
          padding: '22px 20px',
          background: 'linear-gradient(145deg, rgba(56,189,248,.15), rgba(15,23,42,.96) 50%, rgba(17,24,39,.94))',
          border: '1px solid rgba(56,189,248,.18)',
        }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(280px, .8fr)', gap: 18, alignItems: 'start' }}>
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 999, background: 'rgba(56,189,248,.1)', border: '1px solid rgba(56,189,248,.18)', color: 'var(--color-accent)', fontSize: '.76em', fontWeight: 700 }}>
              <Sparkles size={14} />
              交易复盘主引擎
            </div>
            <h3 style={{ marginTop: 14, fontSize: '1.68rem', lineHeight: 1.1, letterSpacing: '-0.04em' }}>
              先定市场分类，再评估持仓与次日计划
            </h3>
            <p style={{ marginTop: 12, color: 'var(--color-dim)', lineHeight: 1.8, fontSize: '.9em' }}>
              这里不是简单生成一篇复盘文章，而是按 `uwillberich` 方法论完成
              <span style={{ color: 'var(--color-text)' }}> 市场状态判断、基准 / 乐观 / 风险 情景、持仓建议 </span>
              和
              <span style={{ color: 'var(--color-text)' }}> 时间门纪律 </span>
              的统一输出。
            </p>
          </div>

          <div
            style={{
              borderRadius: 18,
              padding: 16,
              background: 'rgba(15,23,42,.46)',
              border: '1px solid rgba(148,163,184,.12)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ShieldCheck size={16} color="var(--color-gold)" />
              <div style={{ fontSize: '.9em', fontWeight: 700 }}>复盘输出必须包含</div>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {['市场分类', '基准 / 乐观 / 风险', '持仓逐项评估', '09:00-14:00 时间门纪律', '可做 / 避免'].map((item) => (
                <div key={item} style={{ padding: '9px 10px', borderRadius: 12, background: 'rgba(30,41,59,.48)', border: '1px solid rgba(148,163,184,.1)', fontSize: '.82em' }}>
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 0.95fr) minmax(320px, 1.05fr)', gap: 24, alignItems: 'start' }}>
      {/* Left: Portfolio Input */}
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          padding: 18,
          borderRadius: 18,
          background: 'rgba(15,23,42,.52)',
          border: '1px solid rgba(148,163,184,.12)',
        }}
      >
        <div>
          <div style={{ fontSize: '.84em', fontWeight: 800, color: 'var(--color-text)' }}>持仓输入区</div>
          <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)', lineHeight: 1.7 }}>
            这里专门录入持仓信息。建议至少完整填写股票代码、名称、股数和成本价，再生成复盘。
          </div>
          <div style={{ marginTop: 8, fontSize: '.72em', color: draftStatus === 'error' ? '#fca5a5' : 'var(--color-dim)' }}>
            {draftStatus === 'loading' && '正在加载持仓草稿...'}
            {draftStatus === 'saving' && '正在自动保存持仓草稿...'}
            {draftStatus === 'saved' && '持仓草稿已自动保存到后端'}
            {draftStatus === 'error' && '持仓草稿保存失败，刷新后可能无法保留'}
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.72em', color: 'var(--color-dim)' }}>
              <CalendarDays size={14} />
              复盘日期
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {latestDate && latestDate !== reviewDate && (
                <button
                  onClick={() => setReviewDate(latestDate)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 6,
                    border: '1px solid var(--color-border)',
                    background: 'rgba(56,189,248,.08)',
                    color: 'var(--color-accent)',
                    fontSize: '.68em',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  最新
                </button>
              )}
              <button
                onClick={() => {
                  const d = new Date()
                  d.setDate(d.getDate() - 1)
                  setReviewDate(d.toISOString().slice(0, 10))
                }}
                style={{
                  padding: '3px 8px',
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-card)',
                  color: 'var(--color-dim)',
                  fontSize: '.68em',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                昨日
              </button>
              <button
                onClick={() => setReviewDate(new Date().toISOString().slice(0, 10))}
                style={{
                  padding: '3px 8px',
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-card)',
                  color: 'var(--color-dim)',
                  fontSize: '.68em',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                今日
              </button>
            </div>
          </div>
          <input
            value={reviewDate}
            onChange={(e) => setReviewDate(e.target.value)}
            type="date"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          {latestDate && latestDate !== reviewDate && (
            <div style={{ marginTop: 6, fontSize: '.68em', color: 'var(--color-gold)' }}>
              ⚠️ 最新可用复盘日期：{latestDate}，当前为 {reviewDate}
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
          <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>股票代码</div>
          <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>股票名称</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="股票代码"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="股票名称"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          <input
            value={shares}
            onChange={(e) => setShares(e.target.value)}
            placeholder="持仓数量"
            type="number"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          <input
            value={costPrice}
            onChange={(e) => setCostPrice(e.target.value)}
            placeholder="成本价"
            type="number"
            step="0.01"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
          <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>持仓数量</div>
          <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>成本价</div>
        </div>

        <button
          onClick={addStock}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
            padding: '10px 0',
            border: '1px dashed var(--color-border)',
            borderRadius: 10,
            fontSize: '.84em',
            fontWeight: 600,
            color: 'var(--color-dim)',
            background: 'transparent',
            cursor: 'pointer',
            transition: 'all .15s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--color-accent)'
            e.currentTarget.style.color = 'var(--color-accent)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--color-border)'
            e.currentTarget.style.color = 'var(--color-dim)'
          }}
        >
          <Plus size={14} /> 添加
        </button>

        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.76em', color: 'var(--color-dim)', fontWeight: 700 }}>当前持仓</div>
          <div style={{ maxHeight: 220, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {portfolio.length === 0 && (
              <div style={{ fontSize: '.76em', color: 'var(--color-dim)' }}>还没有持仓，请先录入至少一只股票。</div>
            )}
          {portfolio.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'var(--color-card)',
                borderRadius: 12,
                border: '1px solid var(--color-border)',
                transition: 'border-color .2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
              >
                <div>
                  <span style={{ fontSize: '.88em', color: 'var(--color-text)', fontWeight: 700 }}>{s.name}</span>
                  <span style={{ marginLeft: 6, fontSize: '.72em', color: 'var(--color-dim)' }}>{s.code}</span>
                  <div style={{ fontSize: '.72em', color: 'var(--color-dim)', marginTop: 4 }}>
                    {s.shares} 股 @ {s.cost_price}
                  </div>
                </div>
              <button
                onClick={() => removeStock(i)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-dim)',
                  cursor: 'pointer',
                  padding: 4,
                  transition: 'color .15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-red)' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-dim)' }}
              >
                <Trash2 size={14} />
              </button>
            </motion.div>
          ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || portfolio.length === 0}
          style={{
            width: '100%',
            padding: '10px 0',
            borderRadius: 10,
            border: '1px solid var(--color-accent)',
            background: loading || portfolio.length === 0 ? 'rgba(56,189,248,.04)' : 'rgba(56,189,248,.12)',
            color: 'var(--color-accent)',
            fontSize: '.84em',
            fontWeight: 600,
            cursor: loading || portfolio.length === 0 ? 'not-allowed' : 'pointer',
            opacity: loading || portfolio.length === 0 ? 0.5 : 1,
            transition: 'all .15s',
          }}
        >
          {loading ? '生成中...' : '一键生成复盘报告'}
        </button>

        {content && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <button
              onClick={() => {
                setSelectedHistoryId(null)
                reset()
              }}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '.72em',
                color: 'var(--color-dim)',
                cursor: 'pointer',
                textAlign: 'left',
                padding: 0,
                transition: 'color .15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-accent)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-dim)' }}
            >
              清空重新生成
            </button>
            <span style={{ fontSize: '.7em', color: 'var(--color-dim)' }}>
              {contentMode === 'history' ? '历史回看模式' : '本次生成模式'}
            </span>
          </div>
        )}

      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1 }}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          minHeight: 220,
          padding: 18,
          borderRadius: 18,
          background: 'rgba(15,23,42,.52)',
          border: '1px solid rgba(148,163,184,.12)',
        }}
      >
        <div>
          <div style={{ fontSize: '.84em', fontWeight: 800, color: 'var(--color-text)' }}>历史复盘与回看</div>
          <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)', lineHeight: 1.7 }}>
            这里专门放历史复盘，不和股票输入区挤在一起。点击任意历史记录可以直接在下方阅读正文。
          </div>
        </div>
        <div
          style={{
            borderTop: '1px solid rgba(148,163,184,.12)',
            paddingTop: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            minHeight: 220,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.78em', color: 'var(--color-dim)' }}>
              <History size={14} />
              最近复盘
            </div>
            <button
              onClick={() => void loadHistory()}
              style={{
                border: 'none',
                background: 'none',
                color: 'var(--color-accent)',
                cursor: 'pointer',
                fontSize: '.72em',
                padding: 0,
              }}
            >
              刷新
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto' }}>
            {historyLoading && <div style={{ fontSize: '.76em', color: 'var(--color-dim)' }}>正在加载历史...</div>}
            {!historyLoading && historyItems.length === 0 && (
              <div style={{ fontSize: '.76em', color: 'var(--color-dim)' }}>还没有历史复盘记录。</div>
            )}
            {historyItems.map((item) => {
              const active = selectedHistoryId === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => void openHistory(item.id)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 12px',
                    borderRadius: 12,
                    border: `1px solid ${active ? 'rgba(56,189,248,.24)' : 'var(--color-border)'}`,
                    background: active ? 'rgba(56,189,248,.08)' : 'var(--color-card)',
                    color: 'var(--color-text)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: '.8em', fontWeight: 700 }}>{item.report_date}</div>
                  <div style={{ marginTop: 4, fontSize: '.7em', color: 'var(--color-dim)' }}>
                    {new Date(item.created_at).toLocaleString('zh-CN', {
                      hour12: false,
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </button>
              )
            })}
            {historyError && <div style={{ fontSize: '.76em', color: '#fca5a5' }}>{historyError}</div>}
          </div>
        </div>
      </motion.div>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.12 }}
        style={{
          background: 'linear-gradient(180deg, rgba(17,24,39,.98), rgba(15,23,42,.94))',
          borderRadius: 20,
          border: '1px solid rgba(148,163,184,.14)',
          padding: '26px 28px',
          minHeight: 560,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 18 }}>
          <div>
            <div style={{ fontSize: '.8em', color: 'var(--color-accent)', fontWeight: 700 }}>
              {contentMode === 'history' ? '历史复盘文章' : '复盘报告正文'}
            </div>
            <div style={{ marginTop: 4, fontSize: '.82em', color: 'var(--color-dim)' }}>
              {contentMode === 'history'
                ? '这里像文章阅读区一样展示历史复盘，可完整回看当时的判断链。'
                : '生成结果会按 uwillberich 方法论流式写入，并以文章样式呈现。'}
            </div>
          </div>
          <div style={{ fontSize: '.74em', color: 'var(--color-dim)' }}>
            复盘日期：{reviewDate || '--'}
          </div>
        </div>
        {content ? (
          <div
            className="prose prose-invert prose-sm max-w-none"
            style={{
              maxWidth: 860,
              margin: '0 auto',
              fontSize: '1rem',
              lineHeight: 1.92,
            }}
          >
            <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--color-dim)',
            fontSize: '.88em',
          }}>
            添加持仓后点击生成，复盘报告将在这里显示
          </div>
        )}
        {loading && (
          <span style={{
            display: 'inline-block',
            width: 2,
            height: 16,
            background: 'var(--color-accent)',
            marginLeft: 2,
            animation: 'pulse 1s ease-in-out infinite',
          }} />
        )}
      </motion.section>
    </div>
  )
}

import { useEffect, useMemo, useRef, useState, startTransition } from 'react'
import { motion } from 'framer-motion'
import { BadgeCheck, RefreshCcw, Sparkles, TimerReset, Zap } from 'lucide-react'

import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import KlineMatrix from '../quant/KlineMatrix'
import { useAppStore } from '../../stores/appStore'
import type {
  QuantKlineMultiSeries,
  TurnStrongHistoryItem,
  TurnStrongRun,
  TurnStrongStock,
  TurnStrongValidationResponse,
} from '../../types'

const AUTO_REFRESH_MS = 30 * 60 * 1000
type RecommendationFilter = 'all' | 'buy' | 'watch' | 'avoid'

function isMarketSession(now: Date) {
  const minutes = now.getHours() * 60 + now.getMinutes()
  const morning = minutes >= 9 * 60 + 30 && minutes <= 11 * 60 + 30
  const afternoon = minutes >= 13 * 60 && minutes <= 15 * 60
  return morning || afternoon
}

function formatPercent(value?: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) {
    return '--'
  }
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(digits)}%`
}

function formatDateTime(value?: string) {
  if (!value) {
    return '--'
  }
  try {
    return new Date(value).toLocaleString('zh-CN', {
      hour12: false,
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function computeConvictionScore(item: TurnStrongStock) {
  const screen = item.screen || {}
  const analysis = item.analysis || {}
  const intraday = item.intraday_status || {}
  let score = 40

  if (analysis.recommendation === 'buy') score += 24
  if (analysis.recommendation === 'watch') score += 10
  if (analysis.recommendation === 'avoid') score -= 12

  const auctionVolume = screen.auction_volume_ratio ?? 0
  const auctionChange = screen.auction_change_pct ?? 0
  const profitJump = (screen.current_profit_ratio ?? 0) - (screen.previous_profit_ratio ?? 0)
  const liveChange = item.live_quote?.change_pct ?? screen.change_pct ?? 0

  score += Math.min(12, auctionVolume * 3)
  score += Math.max(0, Math.min(10, auctionChange * 4))
  score += Math.max(0, Math.min(8, profitJump / 2))
  score += Math.max(-8, Math.min(8, liveChange))

  if ((item.news_items || []).length > 0) score += 4
  if ((analysis.risk_flags || []).length >= 2) score -= 6
  if ((intraday.label || '').includes('转强扩散')) score += 6
  if ((intraday.label || '').includes('转弱')) score -= 8

  return Math.max(0, Math.min(100, Math.round(score)))
}

function convictionTier(score: number) {
  if (score >= 78) return { label: 'A 档', color: 'var(--color-red)' }
  if (score >= 62) return { label: 'B 档', color: 'var(--color-gold)' }
  if (score >= 48) return { label: 'C 档', color: 'var(--color-accent)' }
  return { label: 'D 档', color: 'var(--color-dim)' }
}

function verdictLabel(verdict: string) {
  if (verdict === 'success') return '成功'
  if (verdict === 'fail') return '失败'
  if (verdict === 'weak') return '偏弱'
  if (verdict === 'flat') return '一般'
  return '证据不足'
}

function isStructuredMarketSummary(value: unknown): value is {
  market_classification?: string
  rationale?: string
  turning_pool_characteristics?: string
  overall_conclusion?: string
} {
  return typeof value === 'object' && value !== null
}

function parseMarketValue(value?: string) {
  if (!value) return 0
  const normalized = value.replace(/,/g, '').trim()
  if (!normalized) return 0
  const match = normalized.match(/([\d.]+)\s*(亿|万)?/)
  if (!match) return 0
  const num = Number(match[1] || 0)
  const unit = match[2] || ''
  if (unit === '亿') return num
  if (unit === '万') return num / 10000
  return num
}

function deriveGroupKey(item: TurnStrongStock) {
  const concept = (item.screen?.style_concept || '')
    .split(/[、,，;/]/)
    .map((part) => part.trim())
    .filter(Boolean)[0]
  if (concept) return concept
  return item.screen?.industry || '其他方向'
}

function groupHeatLabel(size: number, averageTopScore: number) {
  if (size >= 3 && averageTopScore >= 58) return { label: '有板块行情', color: 'var(--color-red)' }
  if (size >= 2) return { label: '有联动', color: 'var(--color-gold)' }
  return { label: '单点异动', color: 'var(--color-dim)' }
}

function leaderLabel(position: number) {
  if (position === 0) return '龙一'
  if (position === 1) return '龙二'
  if (position === 2) return '龙三'
  return ''
}

function roleLabel(item: TurnStrongStock, position: number) {
  const marketValueYi = parseMarketValue(item.screen?.total_market_value)
  const turnoverValueYi = parseMarketValue(item.screen?.trading_amount)
  if (marketValueYi >= 250 || turnoverValueYi >= 25) return '中军'
  if (position === 0) return '龙头'
  return '跟风'
}

function buildStrictCandidates(
  groups: Array<{
    key: string
    items: Array<{ item: TurnStrongStock; score: number; groupRank: number; leader: string; role: string }>
    averageTopScore: number
    heat: { label: string; color: string }
  }>,
  totalCount: number,
) {
  const target = Math.max(5, Math.min(10, Math.ceil(totalCount / 3)))
  const pickedCodes = new Set<string>()
  const strict: Array<{
    groupKey: string
    heat: { label: string; color: string }
    entry: { item: TurnStrongStock; score: number; groupRank: number; leader: string; role: string }
  }> = []

  for (const group of groups) {
    const leader = group.items[0]
    if (!leader) continue
    const recommendation = leader.item.analysis?.recommendation
    if (recommendation === 'avoid') continue
    if (group.heat.label === '单点异动' && leader.score < 62) continue
    strict.push({ groupKey: group.key, heat: group.heat, entry: leader })
    pickedCodes.add(leader.item.code)
    if (strict.length >= target) return strict
  }

  for (const group of groups) {
    for (const entry of group.items.slice(1)) {
      if (pickedCodes.has(entry.item.code)) continue
      if ((entry.item.analysis?.recommendation || 'watch') === 'avoid') continue
      if (entry.score < 66) continue
      strict.push({ groupKey: group.key, heat: group.heat, entry })
      pickedCodes.add(entry.item.code)
      if (strict.length >= target) return strict
    }
  }

  for (const group of groups) {
    for (const entry of group.items) {
      if (pickedCodes.has(entry.item.code)) continue
      if ((entry.item.analysis?.recommendation || 'watch') === 'avoid') continue
      strict.push({ groupKey: group.key, heat: group.heat, entry })
      pickedCodes.add(entry.item.code)
      if (strict.length >= target) return strict
    }
  }

  return strict
}

export default function TurnStrongPanel({ strictMode = false }: { strictMode?: boolean }) {
  const refreshKey = useAppStore((state) => state.refreshKey)
  const [run, setRun] = useState<TurnStrongRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [selectedCode, setSelectedCode] = useState('')
  const [klineData, setKlineData] = useState<QuantKlineMultiSeries | null>(null)
  const [klineLoading, setKlineLoading] = useState(false)
  const [klineError, setKlineError] = useState('')
  const [filter, setFilter] = useState<RecommendationFilter>('all')
  const [historyItems, setHistoryItems] = useState<TurnStrongHistoryItem[]>([])
  const [compareDate, setCompareDate] = useState('')
  const [compareRun, setCompareRun] = useState<TurnStrongRun | null>(null)
  const [validation, setValidation] = useState<TurnStrongValidationResponse | null>(null)
  const lastRefreshAtRef = useRef(0)

  async function loadCurrent() {
    setError('')
    setLoading(true)
    try {
      const response = await client.get<TurnStrongRun>('/turn-strong')
      startTransition(() => {
        setRun(response.data)
      })
      const firstCode = response.data.items?.[0]?.code || ''
      setSelectedCode((current) => current || firstCode)
      lastRefreshAtRef.current = Date.now()
    } catch {
      setError('转强池加载失败，请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  async function refreshLive() {
    setError('')
    setRefreshing(true)
    try {
      const response = await client.post<TurnStrongRun>('/turn-strong/refresh')
      startTransition(() => {
        setRun(response.data)
      })
      if (!selectedCode && response.data.items?.[0]?.code) {
        setSelectedCode(response.data.items[0].code)
      }
      lastRefreshAtRef.current = Date.now()
    } catch {
      setError('盘中刷新失败，请稍后再试。')
    } finally {
      setRefreshing(false)
    }
  }

  async function generateToday() {
    setError('')
    setGenerating(true)
    try {
      const response = await client.post<TurnStrongRun>('/turn-strong/generate')
      startTransition(() => {
        setRun(response.data)
      })
      if (!selectedCode && response.data.items?.[0]?.code) {
        setSelectedCode(response.data.items[0].code)
      }
      lastRefreshAtRef.current = Date.now()
    } catch {
      setError('今日转强池生成失败，请检查后端日志。')
    } finally {
      setGenerating(false)
    }
  }

  async function loadHistoryList() {
    try {
      const response = await client.get<{ items: TurnStrongHistoryItem[] }>('/turn-strong/history/list')
      setHistoryItems(response.data.items || [])
    } catch {
      setHistoryItems([])
    }
  }

  async function loadHistoryRun(date: string) {
    if (!date) {
      setCompareRun(null)
      setValidation(null)
      return
    }
    try {
      const response = await client.get<TurnStrongRun>('/turn-strong/history', { params: { date } })
      setCompareRun(response.data)
    } catch {
      setCompareRun(null)
    }
    try {
      const response = await client.get<TurnStrongValidationResponse>('/turn-strong/validation', { params: { date } })
      setValidation(response.data)
    } catch {
      setValidation(null)
    }
  }

  useEffect(() => {
    void loadCurrent()
    void loadHistoryList()
  }, [refreshKey])

  useEffect(() => {
    if (compareDate) {
      void loadHistoryRun(compareDate)
    }
  }, [compareDate])

  useEffect(() => {
    const id = window.setInterval(() => {
      if (!isMarketSession(new Date())) {
        return
      }
      if (Date.now() - lastRefreshAtRef.current < AUTO_REFRESH_MS) {
        return
      }
      void refreshLive()
    }, 60_000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    const items = run?.items || []
    if (!items.length) {
      return
    }
    const exists = items.some((item) => item.code === selectedCode)
    if (!selectedCode || !exists) {
      setSelectedCode(items[0].code)
    }
  }, [run, selectedCode])

  useEffect(() => {
    if (!selectedCode || !run?.trade_date) {
      return
    }
    let cancelled = false
    setKlineLoading(true)
    setKlineError('')
    const params = {
      code: selectedCode,
      trade_date: Number(run.trade_date.replaceAll('-', '')),
    }

    client
      .get<QuantKlineMultiSeries>('/amazingdata-market/kline/multi', { params })
      .catch(() =>
        client.get<QuantKlineMultiSeries>('/quant-market/kline/multi', { params }),
      )
      .then((response) => {
        if (cancelled) {
          return
        }
        startTransition(() => {
          setKlineData(response.data)
        })
      })
      .catch(() => {
        if (cancelled) {
          return
        }
        setKlineError('多周期走势暂时拉取失败，请确认量化行情服务已启动。')
      })
      .finally(() => {
        if (!cancelled) {
          setKlineLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedCode, run?.trade_date])

  const items = run?.items || []
  const allEnrichedItems = useMemo(() => {
    return items
      .map((item) => ({ item, score: computeConvictionScore(item) }))
      .sort((a, b) => b.score - a.score || a.item.rank - b.item.rank)
  }, [items])
  const recommendationCounts = useMemo(() => ({
    buy: items.filter((item) => item.analysis?.recommendation === 'buy').length,
    watch: items.filter((item) => (item.analysis?.recommendation || 'watch') === 'watch').length,
    avoid: items.filter((item) => item.analysis?.recommendation === 'avoid').length,
  }), [items])
  const filteredItems = useMemo(() => {
    if (filter === 'all') {
      return allEnrichedItems
    }
    return allEnrichedItems.filter(({ item }) => (item.analysis?.recommendation || 'watch') === filter)
  }, [allEnrichedItems, filter])
  const marketSummary = run?.overall_analysis?.market_summary
  const keyPool = run?.key_pool
  const selectedStock = items.find((item) => item.code === selectedCode) || items[0] || null
  const strongestCandidate = filteredItems[0]
  const allGroupedThemes = useMemo(() => {
    const groups = new Map<string, { key: string; items: Array<{ item: TurnStrongStock; score: number; groupRank: number; leader: string; role: string }>; averageTopScore: number; heat: { label: string; color: string } }>()
    for (const entry of allEnrichedItems) {
      const key = deriveGroupKey(entry.item)
      const existing = groups.get(key) || { key, items: [], averageTopScore: 0, heat: { label: '单点异动', color: 'var(--color-dim)' } }
      existing.items.push({ ...entry, groupRank: 0, leader: '', role: '' })
      groups.set(key, existing)
    }
    const values = Array.from(groups.values()).map((group) => {
      group.items.sort((a, b) => b.score - a.score || a.item.rank - b.item.rank)
      group.items = group.items.map((entry, index) => ({
        ...entry,
        groupRank: index,
        leader: leaderLabel(index),
        role: roleLabel(entry.item, index),
      }))
      const topTwo = group.items.slice(0, 2)
      const avg = topTwo.length ? topTwo.reduce((sum, entry) => sum + entry.score, 0) / topTwo.length : 0
      group.averageTopScore = Math.round(avg)
      group.heat = groupHeatLabel(group.items.length, group.averageTopScore)
      return group
    })
    values.sort((a, b) => b.items.length - a.items.length || b.averageTopScore - a.averageTopScore)
    return values
  }, [allEnrichedItems])
  const groupedThemes = useMemo(() => {
    if (filter === 'all') return allGroupedThemes
    return allGroupedThemes
      .map((group) => ({
        ...group,
        items: group.items.filter((entry) => (entry.item.analysis?.recommendation || 'watch') === filter),
      }))
      .filter((group) => group.items.length > 0)
  }, [allGroupedThemes, filter])
  const strictCandidates = useMemo(() => buildStrictCandidates(allGroupedThemes, items.length), [allGroupedThemes, items.length])
  const strictCandidateCodes = new Set(strictCandidates.map(({ entry }) => entry.item.code))
  const visibleItems = strictMode
    ? filteredItems.filter(({ item }) => strictCandidateCodes.has(item.code))
    : filteredItems
  const currentCodes = new Set(items.map((item) => item.code))
  const repeatedCandidates = (compareRun?.items || []).filter((item) => currentCodes.has(item.code))

  if (loading) {
    return <LoadingSkeleton count={8} />
  }

  if (!run || run.status === 'empty') {
    return <EmptyState generating={generating} onGenerate={generateToday} error={error} />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        style={{
          background: 'linear-gradient(135deg, rgba(251,146,60,.16), rgba(56,189,248,.12) 52%, rgba(17,24,39,.96))',
          border: '1px solid rgba(251,146,60,.18)',
          borderRadius: 18,
          padding: 22,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ maxWidth: 760 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-gold)', fontSize: '.8em', fontWeight: 700 }}>
              <Sparkles size={16} />
              {strictMode ? '09:28 严选作战台' : '09:28 转强作战台'}
            </div>
            <h3 style={{ marginTop: 10, fontSize: '1.5em', lineHeight: 1.15, letterSpacing: '-0.03em' }}>
              {strictMode ? `今日严选 ${strictCandidates.length} 只更高确定性候选` : `今日筛出 ${items.length} 只主板转强股`}
            </h3>
            {isStructuredMarketSummary(marketSummary) ? (
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '.74em', color: 'var(--color-dim)' }}>市场分类</span>
                  <span style={{ padding: '5px 9px', borderRadius: 999, background: 'rgba(56,189,248,.08)', border: '1px solid rgba(56,189,248,.16)', color: 'var(--color-accent)', fontSize: '.76em', fontWeight: 700 }}>
                    {marketSummary.market_classification || '待判定'}
                  </span>
                </div>
                {marketSummary.rationale && (
                  <div style={{ color: 'var(--color-dim)', lineHeight: 1.7, fontSize: '.9em' }}>
                    {marketSummary.rationale}
                  </div>
                )}
                {marketSummary.turning_pool_characteristics && (
                  <div style={{ color: 'var(--color-dim)', lineHeight: 1.7, fontSize: '.9em' }}>
                    候选特征：{marketSummary.turning_pool_characteristics}
                  </div>
                )}
                {marketSummary.overall_conclusion && (
                  <div style={{ color: 'var(--color-text)', lineHeight: 1.7, fontSize: '.9em' }}>
                    结论：{marketSummary.overall_conclusion}
                  </div>
                )}
              </div>
            ) : (
              <p style={{ marginTop: 12, color: 'var(--color-dim)', lineHeight: 1.7, fontSize: '.92em' }}>
                {typeof marketSummary === 'string' && marketSummary ? marketSummary : '暂无结构化结论。'}
              </p>
            )}
            <div style={{ marginTop: 12, display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderRadius: 999, background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.16)', color: '#fca5a5', fontSize: '.75em', fontWeight: 700 }}>
              市场分类优先，竞价数据只做证据层
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <ActionButton
              label={refreshing ? '刷新中...' : '盘中刷新'}
              icon={<RefreshCcw size={15} style={{ animation: refreshing ? 'spin .8s linear infinite' : 'none' }} />}
              onClick={refreshLive}
              disabled={refreshing || generating}
            />
            <ActionButton
              label={generating ? '生成中...' : '重跑今日选股'}
              icon={<TimerReset size={15} style={{ animation: generating ? 'spin .8s linear infinite' : 'none' }} />}
              onClick={generateToday}
              disabled={refreshing || generating}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12, marginTop: 18 }}>
          <MetricCard title="交易日" value={run.trade_date || '--'} accent="var(--color-gold)" />
          <MetricCard title="前一交易日" value={run.previous_trade_date || '--'} accent="var(--color-accent)" />
          <MetricCard title="生成时间" value={formatDateTime(run.generated_at)} accent="var(--color-orange)" />
          <MetricCard title="最近刷新" value={formatDateTime(run.refreshed_at)} accent="var(--color-green)" />
        </div>

        <div style={{ marginTop: 18, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {(run.conditions || []).slice(0, 6).map((condition) => (
            <span
              key={condition.describe}
              style={{
                padding: '6px 10px',
                borderRadius: 999,
                border: '1px solid rgba(148,163,184,.18)',
                background: 'rgba(15,23,42,.45)',
                color: 'var(--color-text)',
                fontSize: '.74em',
              }}
            >
              {condition.describe}
            </span>
          ))}
        </div>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
        <MetricCard
          title="MX Key 池"
          value={`${keyPool?.configured_keys || 0} 个 key`}
          subValue={`当日 ${keyPool?.used_requests || 0}/${keyPool?.total_daily_quota || 0} 次`}
          accent="var(--color-red)"
        />
        <MetricCard
          title="盘中自动刷新"
          value="30 分钟"
          subValue="仅开市时触发"
          accent="var(--color-accent)"
        />
        <MetricCard
          title="最强信号"
          value={strongestCandidate ? `${strongestCandidate.item.name} ${strongestCandidate.item.code}` : '--'}
          subValue={strongestCandidate ? `${convictionTier(strongestCandidate.score).label} · ${strongestCandidate.score}分` : '暂无'}
          accent="var(--color-gold)"
        />
        <MetricCard
          title="推荐分层"
          value={`买入 ${recommendationCounts.buy} / 观察 ${recommendationCounts.watch}`}
          subValue={`回避 ${recommendationCounts.avoid} 只`}
          accent="var(--color-accent)"
        />
      </section>

      <section
        style={{
          borderRadius: 18,
          padding: 18,
          background: 'linear-gradient(155deg, rgba(239,68,68,.14), rgba(15,23,42,.96) 55%)',
          border: '1px solid rgba(239,68,68,.18)',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '.82em', fontWeight: 700, color: 'var(--color-red)' }}>严选控制台</div>
            <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)', lineHeight: 1.7, maxWidth: 720 }}>
              在当前宽池基础上做二次收紧，只保留更少、更确定、优先具备板块辨识度的候选。现在改成横向栅格展示，一行 3 只，更适合快速扫票。
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(120px, 1fr))', gap: 10, minWidth: 360 }}>
            <MiniMetric title="宽池" value={`${items.length} 只`} accent="var(--color-accent)" />
            <MiniMetric title="严选" value={`${strictCandidates.length} 只`} accent="var(--color-red)" />
            <MiniMetric title="压缩比例" value={`${items.length ? Math.round((1 - strictCandidates.length / items.length) * 100) : 0}%`} accent="var(--color-gold)" />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
          {strictCandidates.map(({ groupKey, heat, entry }) => (
            <button
              key={`strict-${entry.item.code}`}
              onClick={() => setSelectedCode(entry.item.code)}
              style={{
                textAlign: 'left',
                borderRadius: 14,
                padding: '13px 13px',
                border: `1px solid ${entry.item.code === selectedCode ? 'rgba(56,189,248,.24)' : 'rgba(148,163,184,.12)'}`,
                background: entry.item.code === selectedCode ? 'rgba(56,189,248,.08)' : 'rgba(15,23,42,.44)',
                cursor: 'pointer',
                minHeight: 112,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '.76em', color: 'var(--color-gold)', fontWeight: 800 }}>{entry.leader || '严选'}</span>
                    <span style={{ fontSize: '.92em', fontWeight: 700 }}>{entry.item.name}</span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: '.72em', color: 'var(--color-dim)' }}>
                    {groupKey}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '.84em', color: convictionTier(entry.score).color, fontWeight: 800 }}>{entry.score}分</div>
                </div>
              </div>
              <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <span style={{
                  padding: '4px 8px',
                  borderRadius: 999,
                  fontSize: '.68em',
                  background: entry.role === '中军' ? 'rgba(239,68,68,.08)' : entry.role === '龙头' ? 'rgba(56,189,248,.08)' : 'rgba(148,163,184,.08)',
                  border: entry.role === '中军' ? '1px solid rgba(239,68,68,.16)' : entry.role === '龙头' ? '1px solid rgba(56,189,248,.16)' : '1px solid rgba(148,163,184,.16)',
                  color: entry.role === '中军' ? 'var(--color-red)' : entry.role === '龙头' ? 'var(--color-accent)' : 'var(--color-dim)',
                }}>
                  {entry.role}
                </span>
                <span style={{
                  padding: '4px 8px',
                  borderRadius: 999,
                  fontSize: '.68em',
                  background: 'rgba(251,191,36,.08)',
                  border: '1px solid rgba(251,191,36,.16)',
                  color: heat.color,
                }}>
                  {heat.label}
                </span>
              </div>
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div
          style={{
            padding: '12px 14px',
            borderRadius: 12,
            border: '1px solid rgba(239,68,68,.22)',
            background: 'rgba(127,29,29,.18)',
            color: '#fecaca',
            fontSize: '.84em',
          }}
        >
          {error}
        </div>
      )}

      <KlineMatrix
        stock={selectedStock}
        data={klineData}
        loading={klineLoading}
        error={klineError}
      />

      <section
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
          padding: '14px 16px',
          borderRadius: 16,
          background: 'rgba(15,23,42,.62)',
          border: '1px solid rgba(148,163,184,.14)',
        }}
      >
        <div>
          <div style={{ fontSize: '.8em', fontWeight: 700, color: 'var(--color-text)' }}>候选分层</div>
          <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)' }}>
            按方法论结论、竞价强度、承接状态和消息支撑综合排序。
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { key: 'all' as RecommendationFilter, label: `全部 ${items.length}` },
            { key: 'buy' as RecommendationFilter, label: `买入 ${recommendationCounts.buy}` },
            { key: 'watch' as RecommendationFilter, label: `观察 ${recommendationCounts.watch}` },
            { key: 'avoid' as RecommendationFilter, label: `回避 ${recommendationCounts.avoid}` },
          ].map((option) => {
            const active = filter === option.key
            return (
              <button
                key={option.key}
                onClick={() => setFilter(option.key)}
                style={{
                  padding: '7px 12px',
                  borderRadius: 999,
                  border: `1px solid ${active ? 'rgba(56,189,248,.24)' : 'rgba(148,163,184,.14)'}`,
                  background: active ? 'rgba(56,189,248,.12)' : 'rgba(15,23,42,.48)',
                  color: active ? 'var(--color-text)' : 'var(--color-dim)',
                  cursor: 'pointer',
                  fontSize: '.78em',
                  fontWeight: 700,
                }}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      </section>

      <section
        style={{
          borderRadius: 18,
          padding: 18,
          background: 'linear-gradient(160deg, rgba(15,23,42,.96), rgba(30,41,59,.92))',
          border: '1px solid rgba(148,163,184,.14)',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <div>
          <div style={{ fontSize: '.82em', fontWeight: 700 }}>概念/板块二分类</div>
          <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)' }}>
            先看是不是形成板块行情，再看组内谁是龙一龙二龙三，谁是中军、龙头、跟风。
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
          {groupedThemes.map((group) => (
            <div
              key={group.key}
              style={{
                borderRadius: 16,
                padding: 14,
                background: 'rgba(15,23,42,.52)',
                border: '1px solid rgba(148,163,184,.12)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                <div>
                  <div style={{ fontSize: '.92em', fontWeight: 800 }}>{group.key}</div>
                  <div style={{ marginTop: 4, fontSize: '.72em', color: 'var(--color-dim)' }}>
                    同组 {group.items.length} 只 · 前排均分 {group.averageTopScore}
                  </div>
                </div>
                <span
                  style={{
                    padding: '6px 9px',
                    borderRadius: 999,
                    fontSize: '.72em',
                    fontWeight: 700,
                    border: `1px solid ${group.heat.color}`,
                    color: group.heat.color,
                    background: 'rgba(15,23,42,.42)',
                  }}
                >
                  {group.heat.label}
                </span>
              </div>
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {group.items.slice(0, 3).map((entry) => (
                  <button
                    key={`${group.key}-${entry.item.code}`}
                    onClick={() => setSelectedCode(entry.item.code)}
                    style={{
                      textAlign: 'left',
                      padding: '10px 11px',
                      borderRadius: 12,
                      border: `1px solid ${entry.item.code === selectedCode ? 'rgba(56,189,248,.24)' : 'rgba(148,163,184,.1)'}`,
                      background: entry.item.code === selectedCode ? 'rgba(56,189,248,.08)' : 'rgba(30,41,59,.44)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '.78em', fontWeight: 800, color: 'var(--color-gold)' }}>{entry.leader || '观察'}</span>
                        <span style={{ fontSize: '.84em', fontWeight: 700 }}>{entry.item.name}</span>
                        <span style={{ fontSize: '.7em', color: 'var(--color-dim)' }}>{entry.item.code}</span>
                      </div>
                      <span style={{ fontSize: '.74em', color: convictionTier(entry.score).color, fontWeight: 700 }}>
                        {entry.score} 分
                      </span>
                    </div>
                    <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: 999,
                        fontSize: '.7em',
                        background: 'rgba(251,191,36,.08)',
                        border: '1px solid rgba(251,191,36,.16)',
                        color: 'var(--color-gold)',
                      }}>{entry.role}</span>
                      {(entry.item.source_tags || []).slice(0, 2).map((tag) => (
                        <span key={tag} style={{
                          padding: '4px 8px',
                          borderRadius: 999,
                          fontSize: '.7em',
                          background: 'rgba(56,189,248,.08)',
                          border: '1px solid rgba(56,189,248,.16)',
                          color: 'var(--color-accent)',
                        }}>{tag}</span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(260px, .7fr) minmax(0, 1.3fr)',
          gap: 16,
        }}
      >
        <div
          style={{
            borderRadius: 16,
            padding: 16,
            background: 'var(--color-card)',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ fontSize: '.82em', fontWeight: 700 }}>历史回看</div>
          <div style={{ marginTop: 6, fontSize: '.74em', color: 'var(--color-dim)' }}>
            选一个历史交易日，对照今天的候选结构和重复出现标的。
          </div>
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {historyItems.map((item) => {
              const active = compareDate === item.trade_date
              return (
                <button
                  key={item.trade_date}
                  onClick={() => setCompareDate((current) => current === item.trade_date ? '' : item.trade_date)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 12px',
                    borderRadius: 12,
                    border: `1px solid ${active ? 'rgba(56,189,248,.24)' : 'rgba(148,163,184,.14)'}`,
                    background: active ? 'rgba(56,189,248,.08)' : 'rgba(15,23,42,.36)',
                    color: 'var(--color-text)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: '.82em', fontWeight: 700 }}>{item.trade_date}</div>
                  <div style={{ marginTop: 4, fontSize: '.7em', color: 'var(--color-dim)' }}>
                    候选 {item.selection_total} 只
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div
          style={{
            borderRadius: 16,
            padding: 16,
            background: 'rgba(15,23,42,.62)',
            border: '1px solid rgba(148,163,184,.14)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '.82em', fontWeight: 700 }}>对照摘要</div>
              <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)' }}>
                {compareRun ? `当前 vs ${compareRun.trade_date}` : '选择一个历史交易日后显示对照摘要。'}
              </div>
            </div>
            {compareRun && (
              <div style={{ fontSize: '.74em', color: 'var(--color-dim)' }}>
                历史候选 {compareRun.items.length} 只
              </div>
            )}
          </div>

          {compareRun ? (
            <div style={{ marginTop: 14, display: 'grid', gap: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10 }}>
                <MiniMetric title="历史交易日" value={compareRun.trade_date} accent="var(--color-gold)" />
                <MiniMetric title="重合候选" value={`${repeatedCandidates.length} 只`} accent="var(--color-accent)" />
                <MiniMetric title="当前候选" value={`${items.length} 只`} accent="var(--color-red)" />
              </div>
              <div style={{ padding: '12px 14px', borderRadius: 14, background: 'rgba(30,41,59,.46)', border: '1px solid rgba(148,163,184,.12)' }}>
                <div style={{ fontSize: '.76em', color: 'var(--color-dim)' }}>历史方法论摘要</div>
                <div style={{ marginTop: 6, fontSize: '.84em', lineHeight: 1.7, color: 'var(--color-text)' }}>
                  {isStructuredMarketSummary(compareRun.overall_analysis?.market_summary)
                    ? compareRun.overall_analysis?.market_summary?.overall_conclusion
                      || compareRun.overall_analysis?.market_summary?.rationale
                      || '暂无历史摘要。'
                    : compareRun.overall_analysis?.market_summary || '暂无历史摘要。'}
                </div>
              </div>
              {validation?.summary && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10 }}>
                  <MiniMetric title="次日成功" value={`${validation.summary.success_count} 只`} accent="var(--color-red)" />
                  <MiniMetric title="次日走弱" value={`${validation.summary.fail_count} 只`} accent="var(--color-green)" />
                  <MiniMetric title="平均收盘涨跌" value={formatPercent(validation.summary.avg_close_change_pct)} accent={validation.summary.avg_close_change_pct >= 0 ? 'var(--color-red)' : 'var(--color-green)'} />
                  <MiniMetric title="平均盘中最大涨幅" value={formatPercent(validation.summary.avg_max_gain_pct)} accent="var(--color-gold)" />
                </div>
              )}
              <div>
                <div style={{ fontSize: '.76em', color: 'var(--color-dim)', marginBottom: 8 }}>重复出现的候选</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {repeatedCandidates.length === 0 && (
                    <span style={{ fontSize: '.76em', color: 'var(--color-dim)' }}>当前候选与该历史日无重合。</span>
                  )}
                  {repeatedCandidates.map((item) => (
                    <span
                      key={item.code}
                      style={{
                        padding: '6px 9px',
                        borderRadius: 999,
                        background: 'rgba(56,189,248,.08)',
                        border: '1px solid rgba(56,189,248,.18)',
                        color: 'var(--color-accent)',
                        fontSize: '.76em',
                      }}
                    >
                      {item.name} {item.code}
                    </span>
                  ))}
                </div>
              </div>
              {validation?.items?.length ? (
                <div>
                  <div style={{ fontSize: '.76em', color: 'var(--color-dim)', marginBottom: 8 }}>次日验证</div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    {validation.items.slice(0, 6).map((row) => {
                      const verdictColor = row.verdict === 'success'
                        ? 'var(--color-red)'
                        : row.verdict === 'fail'
                          ? 'var(--color-green)'
                          : row.verdict === 'weak'
                            ? 'var(--color-gold)'
                            : 'var(--color-dim)'
                      return (
                        <div
                          key={`${row.code}-${row.next_trade_date}`}
                          style={{
                            padding: '11px 12px',
                            borderRadius: 12,
                            border: '1px solid rgba(148,163,184,.12)',
                            background: 'rgba(30,41,59,.42)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                            <div>
                              <div style={{ fontSize: '.84em', fontWeight: 700 }}>{row.name} {row.code}</div>
                              <div style={{ marginTop: 4, fontSize: '.72em', color: 'var(--color-dim)' }}>
                                次日 {row.next_trade_date || '--'} · 开 {row.next_open ?? '--'} / 收 {row.next_close ?? '--'} / 高 {row.next_high ?? '--'}
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontSize: '.74em', color: verdictColor, fontWeight: 700 }}>{verdictLabel(row.verdict)}</div>
                              <div style={{ marginTop: 4, fontSize: '.72em', color: 'var(--color-dim)' }}>
                                收盘 {formatPercent(row.close_change_pct)} · 盘中 {formatPercent(row.max_gain_pct)}
                              </div>
                            </div>
                          </div>
                          <div style={{ marginTop: 6, fontSize: '.76em', color: 'var(--color-dim)', lineHeight: 1.6 }}>
                            {row.note}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div style={{ marginTop: 18, fontSize: '.8em', color: 'var(--color-dim)' }}>
              历史对照适合回看哪些票反复进入候选池、哪些市场摘要在次日延续或失效。
            </div>
          )}
        </div>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
        {visibleItems.length === 0 && (
          <div
            style={{
              padding: '20px 18px',
              borderRadius: 16,
              border: '1px dashed rgba(148,163,184,.18)',
              color: 'var(--color-dim)',
              fontSize: '.84em',
            }}
          >
            {strictMode ? '当前严选条件下没有候选股，可回到转强作战台查看宽池。' : '当前筛选条件下没有候选股，可切回“全部”查看全量结果。'}
          </div>
        )}
        {visibleItems.map(({ item, score }, index) => {
          const group = groupedThemes.find((entry) => entry.items.some((candidate) => candidate.item.code === item.code))
          const groupEntry = group?.items.find((candidate) => candidate.item.code === item.code)
          return (
          <TurnStrongStockCard
            key={item.code}
            item={item}
            score={score}
            leader={groupEntry?.leader || ''}
            role={groupEntry?.role || '跟风'}
            index={index}
            selected={item.code === selectedCode}
            onSelect={() => setSelectedCode(item.code)}
          />
        )})}
      </section>
    </div>
  )
}

function ActionButton({
  label,
  icon,
  onClick,
  disabled,
}: {
  label: string
  icon: React.ReactNode
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 12px',
        borderRadius: 12,
        border: '1px solid rgba(148,163,184,.18)',
        background: disabled ? 'rgba(15,23,42,.45)' : 'rgba(15,23,42,.72)',
        color: disabled ? 'var(--color-dim)' : 'var(--color-text)',
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {icon}
      <span style={{ fontSize: '.82em', fontWeight: 600 }}>{label}</span>
    </button>
  )
}

function MetricCard({
  title,
  value,
  subValue,
  accent,
}: {
  title: string
  value: string
  subValue?: string
  accent: string
}) {
  return (
    <div
      style={{
        background: 'var(--color-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 14,
        padding: '14px 16px',
      }}
    >
      <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: '1.08em', fontWeight: 700, color: accent }}>{value}</div>
      {subValue && (
        <div style={{ marginTop: 4, fontSize: '.76em', color: 'var(--color-dim)' }}>{subValue}</div>
      )}
    </div>
  )
}

function TurnStrongStockCard({
  item,
  score,
  leader,
  role,
  index,
  selected,
  onSelect,
}: {
  item: TurnStrongStock
  score: number
  leader: string
  role: string
  index: number
  selected: boolean
  onSelect: () => void
}) {
  const screen = item.screen || {}
  const analysis = item.analysis || {}
  const liveQuote = item.live_quote || {}
  const intraday = item.intraday_status || {}
  const newsItems = item.news_items || []
  const recommendation = analysis.recommendation || 'watch'
  const tier = convictionTier(score)
  const recColor = recommendation === 'buy'
    ? 'var(--color-red)'
    : recommendation === 'avoid'
      ? 'var(--color-green)'
      : 'var(--color-gold)'

  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      style={{
        background: index < 3
          ? 'linear-gradient(160deg, rgba(251,146,60,.08), rgba(17,24,39,.96) 45%, var(--color-card))'
          : 'var(--color-card)',
        borderRadius: 16,
        border: `1px solid ${selected ? 'rgba(56,189,248,.42)' : index < 3 ? 'rgba(251,146,60,.2)' : 'var(--color-border)'}`,
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        cursor: 'pointer',
      }}
      onClick={onSelect}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '.78em', color: 'var(--color-gold)', fontWeight: 700 }}>#{item.rank}</span>
            <h4 style={{ fontSize: '1.04em', fontWeight: 700 }}>{item.name}</h4>
            {leader && (
              <span style={{
                padding: '4px 8px',
                borderRadius: 999,
                fontSize: '.68em',
                fontWeight: 700,
                background: 'rgba(251,191,36,.08)',
                border: '1px solid rgba(251,191,36,.16)',
                color: 'var(--color-gold)',
              }}>
                {leader}
              </span>
            )}
            <span style={{
              padding: '4px 8px',
              borderRadius: 999,
              fontSize: '.68em',
              fontWeight: 700,
              background: role === '中军' ? 'rgba(239,68,68,.08)' : role === '龙头' ? 'rgba(56,189,248,.08)' : 'rgba(148,163,184,.08)',
              border: role === '中军' ? '1px solid rgba(239,68,68,.16)' : role === '龙头' ? '1px solid rgba(56,189,248,.16)' : '1px solid rgba(148,163,184,.16)',
              color: role === '中军' ? 'var(--color-red)' : role === '龙头' ? 'var(--color-accent)' : 'var(--color-dim)',
            }}>
              {role}
            </span>
          </div>
          <div style={{ marginTop: 6, fontSize: '.76em', color: 'var(--color-dim)' }}>
            {item.code} · {screen.board || '主板'} · {screen.industry || '行业待补充'}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '.74em', color: 'var(--color-dim)' }}>方法论结论</div>
          <div style={{ marginTop: 6, color: recColor, fontSize: '.92em', fontWeight: 700 }}>
            {analysis.recommendation_label || '观察为主'}
          </div>
          <div style={{ marginTop: 6, fontSize: '.74em', color: tier.color, fontWeight: 700 }}>
            {tier.label} · {score} 分
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
        <SignalTile icon={<Zap size={14} />} label="竞价量比" value={screen.auction_volume_ratio != null ? String(screen.auction_volume_ratio) : '--'} />
        <SignalTile icon={<BadgeCheck size={14} />} label="高开幅度" value={formatPercent(screen.auction_change_pct)} />
        <SignalTile icon={<Sparkles size={14} />} label="前日获利盘" value={screen.previous_profit_ratio != null ? `${screen.previous_profit_ratio.toFixed(2)}%` : '--'} />
        <SignalTile icon={<RefreshCcw size={14} />} label="今日获利盘" value={screen.current_profit_ratio != null ? `${screen.current_profit_ratio.toFixed(2)}%` : '--'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
        <MiniMetric title="入池价" value={screen.latest_price != null ? `${screen.latest_price.toFixed(2)}` : '--'} accent="var(--color-gold)" />
        <MiniMetric title="当前涨幅" value={formatPercent(liveQuote.change_pct ?? screen.change_pct)} accent={(liveQuote.change_pct ?? screen.change_pct ?? 0) >= 0 ? 'var(--color-red)' : 'var(--color-green)'} />
        <MiniMetric title="盘中状态" value={intraday.label || '待刷新'} accent="var(--color-accent)" />
      </div>

      {(screen.style_concept || '').split('、').filter(Boolean).length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(item.source_tags || []).map((tag) => (
            <span
              key={`${item.code}-${tag}`}
              style={{
                padding: '5px 8px',
                borderRadius: 999,
                fontSize: '.72em',
                border: '1px solid rgba(251,191,36,.18)',
                background: 'rgba(251,191,36,.08)',
                color: 'var(--color-gold)',
              }}
            >
              {tag}
            </span>
          ))}
          {(screen.style_concept || '').split('、').filter(Boolean).slice(0, 6).map((tag) => (
            <span
              key={tag}
              style={{
                padding: '5px 8px',
                borderRadius: 999,
                fontSize: '.72em',
                border: '1px solid rgba(56,189,248,.18)',
                background: 'rgba(56,189,248,.08)',
                color: 'var(--color-accent)',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <NarrativeBlock title="逻辑支撑" content={analysis.logic_support || '暂无结构化逻辑说明。'} />
        <NarrativeBlock title="消息支持" content={analysis.news_support || '暂无结构化消息说明。'} />
        <NarrativeBlock title="方法论判断" content={analysis.methodology_view || intraday.summary || '等待盘中承接确认。'} />
      </div>

      {(analysis.risk_flags || []).length > 0 && (
        <div>
          <div style={{ fontSize: '.74em', color: 'var(--color-dim)', marginBottom: 8 }}>风险提示</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(analysis.risk_flags || []).slice(0, 3).map((risk) => (
              <span
                key={risk}
                style={{
                  padding: '5px 8px',
                  borderRadius: 999,
                  fontSize: '.72em',
                  border: '1px solid rgba(239,68,68,.18)',
                  background: 'rgba(239,68,68,.08)',
                  color: '#fca5a5',
                }}
              >
                {risk}
              </span>
            ))}
          </div>
        </div>
      )}

      {analysis.execution_plan && (
        <div
          style={{
            padding: '11px 12px',
            borderRadius: 12,
            border: '1px solid rgba(251,191,36,.16)',
            background: 'rgba(15,23,42,.42)',
            fontSize: '.8em',
            lineHeight: 1.6,
            color: 'var(--color-text)',
          }}
        >
          <span style={{ color: 'var(--color-gold)', fontWeight: 700 }}>执行建议：</span>
          {analysis.execution_plan}
        </div>
      )}

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <TimerReset size={14} color="var(--color-dim)" />
          <span style={{ fontSize: '.74em', color: 'var(--color-dim)' }}>消息线索</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {newsItems.length === 0 ? (
            <div style={{ fontSize: '.78em', color: 'var(--color-dim)' }}>暂无匹配新闻。</div>
          ) : newsItems.slice(0, 3).map((news) => (
            <a
              key={`${item.code}-${news.title}`}
              href={news.url || '#'}
              target={news.url ? '_blank' : undefined}
              rel={news.url ? 'noreferrer' : undefined}
              style={{
                textDecoration: 'none',
                color: 'inherit',
                padding: '9px 10px',
                borderRadius: 12,
                border: '1px solid rgba(148,163,184,.14)',
                background: 'rgba(15,23,42,.36)',
              }}
            >
              <div style={{ fontSize: '.8em', lineHeight: 1.55 }}>{news.title}</div>
              <div style={{ marginTop: 5, fontSize: '.7em', color: 'var(--color-dim)' }}>
                {news.source || '未知来源'} · {news.date || '--'}
              </div>
            </a>
          ))}
        </div>
      </div>
    </motion.article>
  )
}

function SignalTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div
      style={{
        padding: '10px 11px',
        borderRadius: 12,
        border: '1px solid rgba(148,163,184,.14)',
        background: 'rgba(15,23,42,.42)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-dim)', fontSize: '.72em' }}>
        {icon}
        {label}
      </div>
      <div style={{ marginTop: 7, fontSize: '1em', fontWeight: 700 }}>{value}</div>
    </div>
  )
}

function MiniMetric({
  title,
  value,
  accent,
}: {
  title: string
  value: string
  accent: string
}) {
  return (
    <div
      style={{
        padding: '10px 11px',
        borderRadius: 12,
        border: '1px solid rgba(148,163,184,.14)',
        background: 'rgba(15,23,42,.28)',
      }}
    >
      <div style={{ fontSize: '.7em', color: 'var(--color-dim)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: '.92em', fontWeight: 700, color: accent }}>{value}</div>
    </div>
  )
}

function NarrativeBlock({ title, content }: { title: string; content: string }) {
  return (
    <div>
      <div style={{ fontSize: '.74em', color: 'var(--color-dim)', marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: '.82em', lineHeight: 1.7, color: 'var(--color-text)' }}>{content}</div>
    </div>
  )
}

function EmptyState({
  generating,
  onGenerate,
  error,
}: {
  generating: boolean
  onGenerate: () => void
  error: string
}) {
  return (
    <div
      style={{
        padding: '48px 24px',
        borderRadius: 18,
        border: '1px solid var(--color-border)',
        background: 'linear-gradient(135deg, rgba(56,189,248,.08), rgba(17,24,39,.95))',
        textAlign: 'center',
      }}
    >
      <h3 style={{ fontSize: '1.35em', fontWeight: 700 }}>今日转强池还没有生成</h3>
      <p style={{ marginTop: 10, color: 'var(--color-dim)', lineHeight: 1.7 }}>
        系统会在每个交易日 09:28 自动生成一次。你也可以手动触发，立即把今天的主板转强候选池跑出来。
      </p>
      <div style={{ marginTop: 18 }}>
        <ActionButton
          label={generating ? '生成中...' : '立即生成今日选股'}
          icon={<Zap size={15} style={{ animation: generating ? 'spin .8s linear infinite' : 'none' }} />}
          onClick={onGenerate}
          disabled={generating}
        />
      </div>
      {error && (
        <div style={{ marginTop: 14, fontSize: '.82em', color: '#fca5a5' }}>{error}</div>
      )}
    </div>
  )
}

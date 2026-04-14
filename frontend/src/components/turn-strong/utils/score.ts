import type { TurnStrongStock } from '../../../types'

export function computeConvictionScore(item: TurnStrongStock) {
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

export function convictionTier(score: number) {
  if (score >= 78) return { label: 'A 档', color: 'var(--color-red)' }
  if (score >= 62) return { label: 'B 档', color: 'var(--color-gold)' }
  if (score >= 48) return { label: 'C 档', color: 'var(--color-accent)' }
  return { label: 'D 档', color: 'var(--color-text-secondary)' }
}

export function deriveGroupKey(item: TurnStrongStock) {
  const concept = item.concept || ''
  if (concept) return concept
  if ((item.analysis?.recommendation || '') === 'buy') return '精选个股'
  return '其他'
}

export function groupHeatLabel(size: number, averageTopScore: number) {
  if (size >= 6 || averageTopScore >= 70) return '🔥 极热'
  if (size >= 4 || averageTopScore >= 60) return '🔥 热'
  if (size >= 2 || averageTopScore >= 50) return '温'
  return '冷'
}

export function roleLabel(item: TurnStrongStock, position: number) {
  if (position === 0) return '龙头'
  if (position === 1) return '中军'
  if ((item.analysis?.recommendation || '') === 'buy') return '先锋'
  return '跟风'
}

export function buildStrictCandidates(
  stocks: TurnStrongStock[],
  scores: Map<TurnStrongStock, number>,
): TurnStrongStock[] {
  return stocks
    .filter((s) => {
      const score = scores.get(s) ?? 0
      return score >= 62 && s.analysis?.recommendation === 'buy'
    })
    .slice(0, 5)
}

export function formatPercent(value?: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(digits)}%`
}

export function isMarketSession(now: Date) {
  const minutes = now.getHours() * 60 + now.getMinutes()
  const morning = minutes >= 9 * 60 + 30 && minutes <= 11 * 60 + 30
  const afternoon = minutes >= 13 * 60 && minutes <= 15 * 60
  return morning || afternoon
}

export function formatDateTime(value?: string) {
  if (!value) return '--'
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

export function isStructuredMarketSummary(value: unknown): value is {
  market_classification?: string
  rationale?: string
  turning_pool_characteristics?: string
  overall_conclusion?: string
} {
  return typeof value === 'object' && value !== null
}

export function parseMarketValue(value?: string) {
  if (!value) return null
  try {
    const parsed = JSON.parse(value)
    if (isStructuredMarketSummary(parsed)) return parsed
  } catch {
    // ignore
  }
  return null
}

export function leaderLabel(position: number) {
  if (position === 0) return '龙头'
  if (position === 1) return '中军'
  return '先锋'
}

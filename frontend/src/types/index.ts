export type Section =
  | 'investment-calendar'
  | 'trade-desk'
  | 'main-wave'
  | 'chan-chart'
  | 'concept-board'
  | 'strict-turn-strong'
  | 'fin-news'
  | 'sectors'
  | 'zt-analysis'
  | 'turn-strong'
  | 'review-report'
  | 'obsession-phase'
  | 'cross-validation'

export interface NewsItem {
  id: string
  source: string
  title: string
  summary?: string
  url?: string
  keywords?: string
  published_at?: string
  collected_at: string
}

export interface TrendingItem {
  id: string
  platform: string
  title: string
  heat_score: number
  category?: string
  url?: string
  collected_at: string
}

export interface SectorItem {
  name: string
  code?: string
  change_pct: number
  leader?: string
}

export interface IndexItem {
  name: string
  price: number
  change_pct: number
}

export interface ZTStock {
  code: string
  name: string
  change_pct: number
  lianban_count?: number
  popularity_score?: number
  reason?: string
}

export interface PortfolioStock {
  code: string
  name: string
  shares: number
  cost_price: number
}

export interface ReviewHistoryItem {
  id: number
  report_date: string
  created_at: string
}

export interface ReviewReportDetail extends ReviewHistoryItem {
  portfolio_json: string
  report_content: string
}

export interface PortfolioTemplate {
  id: string
  name: string
  created_at: string
  portfolio: PortfolioStock[]
}

export interface TurnStrongCondition {
  describe: string
  stockCount: number
}

export interface TurnStrongNewsItem {
  title: string
  source?: string
  date?: string
  url?: string
  type?: string
}

export interface TurnStrongAnalysis {
  code?: string
  name?: string
  recommendation?: 'buy' | 'watch' | 'avoid'
  recommendation_label?: string
  logic_support?: string
  news_support?: string
  methodology_view?: string
  risk_flags?: string[]
  execution_plan?: string
}

export interface TurnStrongScreenSnapshot {
  board?: string
  industry?: string
  style_concept?: string
  previous_profit_ratio?: number | null
  current_profit_ratio?: number | null
  auction_volume_ratio?: number | null
  auction_change_pct?: number | null
  latest_price?: number | null
  change_pct?: number | null
  volume_ratio?: number | null
  turnover_rate?: number | null
  trading_amount?: string
  total_market_value?: string
  circulation_market_value?: string
}

export interface TurnStrongLiveQuote {
  code?: string
  name?: string
  price?: number | null
  change_pct?: number | null
  amount_100m?: number | null
  timestamp?: string
}

export interface TurnStrongIntradayStatus {
  label?: string
  summary?: string
  price_delta_from_screen?: number | null
  updated_at?: string
}

export interface TurnStrongStock {
  rank: number
  code: string
  name: string
  market?: string
  concept?: string
  source_tags?: string[]
  screen: TurnStrongScreenSnapshot
  news_items: TurnStrongNewsItem[]
  analysis: TurnStrongAnalysis
  live_quote: TurnStrongLiveQuote
  intraday_status: TurnStrongIntradayStatus
}

export interface TurnStrongKeyItem {
  name: string
  request_count: number
  remaining: number
  quota_exhausted: boolean
  last_used_at?: string
}

export interface TurnStrongKeyPool {
  usage_date: string
  configured_keys: number
  daily_quota_per_key: number
  total_daily_quota: number
  used_requests: number
  items: TurnStrongKeyItem[]
}

export interface TurnStrongRun {
  status: string
  trade_date: string
  previous_trade_date?: string
  generated_at?: string
  refreshed_at?: string
  selection_total?: number
  screening_query?: string
  conditions?: TurnStrongCondition[]
  market_snapshot?: {
    indices?: IndexItem[]
    top_risers?: SectorItem[]
    top_fallers?: SectorItem[]
  }
  overall_analysis?: {
    market_summary?: string | {
      market_classification?: string
      rationale?: string
      turning_pool_characteristics?: string
      overall_conclusion?: string
    }
    analyses?: TurnStrongAnalysis[]
    raw_text?: string
  }
  items: TurnStrongStock[]
  key_pool?: TurnStrongKeyPool
}

export interface TurnStrongHistoryItem {
  trade_date: string
  generated_at: string
  refreshed_at: string
  status: string
  selection_total: number
}

export interface TurnStrongValidationItem {
  code: string
  name: string
  entry_price?: number | null
  next_trade_date?: string
  next_open?: number | null
  next_close?: number | null
  next_high?: number | null
  close_change_pct?: number | null
  max_gain_pct?: number | null
  verdict: 'success' | 'weak' | 'flat' | 'fail' | 'insufficient'
  note: string
}

export interface TurnStrongValidationSummary {
  count: number
  success_count: number
  fail_count: number
  avg_close_change_pct: number
  avg_max_gain_pct: number
  best?: TurnStrongValidationItem | null
  worst?: TurnStrongValidationItem | null
}

export interface TurnStrongValidationResponse {
  status: string
  trade_date: string
  summary: TurnStrongValidationSummary
  items: TurnStrongValidationItem[]
}

export interface QuantKlineBar {
  code: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
}

export interface QuantKlineSeries {
  code: string
  period: string
  requested_period: string
  begin_date: number
  end_date: number
  count: number
  items: QuantKlineBar[]
}

export interface QuantKlineMultiSeries {
  code: string
  trade_date: number
  series: {
    minute: QuantKlineSeries
    fifteen_minute: QuantKlineSeries
    hour: QuantKlineSeries
    day: QuantKlineSeries
  }
}

export interface TradeEvidenceSnapshot {
  indices: IndexItem[]
  sector_evidence: {
    items: SectorItem[]
    fallback_used: boolean
  }
  news_evidence: {
    items: NewsItem[]
    fallback_used: boolean
  }
  zt_evidence: {
    items: ZTStock[]
  }
  turn_strong: {
    selection_total: number
    market_summary?: string | {
      market_classification?: string
      rationale?: string
      turning_pool_characteristics?: string
      overall_conclusion?: string
    }
  }
}

export interface ChanBar {
  index: number
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
}

export interface ChanStroke {
  start_index: number
  end_index: number
  start_date: string
  end_date: string
  start_price: number
  end_price: number
  direction: 'up' | 'down'
}

export interface ChanSegment {
  start_index: number
  end_index: number
  start_price: number
  end_price: number
  direction: 'up' | 'down'
}

export interface ChanCenter {
  start_index: number
  end_index: number
  upper: number
  lower: number
  mid: number
}

export interface ChanTradePoint {
  type: string
  index: number
  price: number
}

export interface ChanChartResponse {
  code: string
  bars: ChanBar[]
  strokes: ChanStroke[]
  segments: ChanSegment[]
  centers: ChanCenter[]
  trade_points: ChanTradePoint[]
}

export interface ChanSearchItem {
  code: string
  name: string
  market?: string
}

export interface CalendarEvent {
  date: string
  title: string
  type: 'meeting' | 'policy' | 'economic_data' | 'earnings' | 'market'
  level: 'major' | 'moderate' | 'minor'
  description: string
  benefit_sectors: string[]
  leading_stocks: { name: string; code: string; reason: string }[]
}

export interface CalendarResponse {
  events: CalendarEvent[]
  count: number
}

// 微信公众号搜索相关
export interface WechatArticle {
  id: number
  title: string
  summary?: string
  url: string
  author?: string
  publish_date?: string
  crawled_at: string
  official_account_id: number
  keywords?: Record<string, any>
  account_name?: string
  account_wechat_id?: string
}

export interface WechatSearchResponse {
  total: number
  page: number
  page_size: number
  pages: number
  articles: WechatArticle[]
}

export interface WechatAccount {
  id: number
  name: string
  wechat_id: string
  description?: string
  avatar_url?: string
  article_count: number
  status: string
  updated_at?: string
}

export interface WechatTrendingTopic {
  topic: string
  count: number
}

export interface WechatStatistics {
  total_articles: number
  total_accounts: number
  recent_articles_7d: number
  category_stats: Record<string, number>
}

export interface ObsessionSignal {
  name: string
  label: string
  triggered: boolean
  description: string
}

export interface ObsessionPhaseStatus {
  current_phase: string
  phase_label: string
  phase_description: string
  signals: ObsessionSignal[]
  signal_count: number
  action_suggestion: string
  last_updated: string
}


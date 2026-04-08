export type Section =
  | 'ai-news'
  | 'viral'
  | 'trending'
  | 'article-gen'
  | 'fin-news'
  | 'sectors'
  | 'zt-analysis'
  | 'review-report'

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

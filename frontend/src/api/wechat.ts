/**
 * 微信公众号搜索 API
 */
import type {
  WechatSearchResponse,
  WechatAccount,
  WechatTrendingTopic,
  WechatStatistics,
} from '../types'

const API_BASE = '/api/wechat'

export async function searchArticles(params: {
  q?: string
  category?: string
  page?: number
  page_size?: number
}): Promise<WechatSearchResponse> {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.set('q', params.q)
  if (params.category) searchParams.set('category', params.category)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))

  const response = await fetch(`${API_BASE}/search?${searchParams}`)
  if (!response.ok) {
    throw new Error(`搜索失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getAccountArticles(
  accountId: number,
  page = 1,
  pageSize = 20
): Promise<WechatSearchResponse> {
  const response = await fetch(
    `${API_BASE}/accounts/${accountId}/articles?page=${page}&page_size=${pageSize}`
  )
  if (!response.ok) {
    throw new Error(`获取文章失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getAccount(accountId: number): Promise<WechatAccount> {
  const response = await fetch(`${API_BASE}/accounts/${accountId}`)
  if (!response.ok) {
    throw new Error(`获取公众号失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getTrendingTopics(limit = 10): Promise<WechatTrendingTopic[]> {
  const response = await fetch(`${API_BASE}/trending-topics?limit=${limit}`)
  if (!response.ok) {
    throw new Error(`获取热门话题失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getRecommendedAccounts(limit = 10): Promise<WechatAccount[]> {
  const response = await fetch(`${API_BASE}/recommended-accounts?limit=${limit}`)
  if (!response.ok) {
    throw new Error(`获取推荐公众号失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getCategories(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/categories`)
  if (!response.ok) {
    throw new Error(`获取分类失败: ${response.statusText}`)
  }
  const data = await response.json()
  return data.categories || []
}

export async function getStatistics(): Promise<WechatStatistics> {
  const response = await fetch(`${API_BASE}/statistics`)
  if (!response.ok) {
    throw new Error(`获取统计信息失败: ${response.statusText}`)
  }
  return response.json()
}

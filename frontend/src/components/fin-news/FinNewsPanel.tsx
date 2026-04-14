import { useState } from 'react'
import NewsCard from '../common/NewsCard'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
import { useApiFetch } from '../../hooks/useApi'
import type { NewsItem } from '../../types'

const SOURCES = ['全部', 'eastmoney', 'sina', 'cls', 'ths']
const SOURCE_LABELS: Record<string, string> = {
  '全部': '全部',
  eastmoney: '东方财富',
  sina: '新浪',
  cls: '财联社',
  ths: '同花顺',
}

const SOURCE_COLORS: Record<string, { bg: string; color: string }> = {
  eastmoney: { bg: 'rgba(251,146,60,.12)', color: 'var(--color-orange)' },
  sina: { bg: 'rgba(56,189,248,.12)', color: 'var(--color-accent)' },
  cls: { bg: 'rgba(74,222,128,.12)', color: 'var(--color-green)' },
  ths: { bg: 'rgba(251,191,36,.12)', color: 'var(--color-gold)' },
}

export default function FinNewsPanel() {
  const [source, setSource] = useState('')
  const refreshKey = useAppStore((s) => s.refreshKey)

  const { data, loading, error, refetch } = useApiFetch<{
    items: NewsItem[]
    fallback_used?: boolean
  }>('/fin-news', {
    params: { source, hours: 24 },
    deps: [source, refreshKey],
  })

  const items = data?.items || []
  const fallbackUsed = data?.fallback_used || false

  return (
    <div>
      {/* Source Filter Pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {SOURCES.map((s) => {
          const isActive = (s === '全部' && !source) || source === s
          const sc = SOURCE_COLORS[s]
          return (
            <button
              key={s}
              onClick={() => setSource(s === '全部' ? '' : s)}
              style={{
                padding: '6px 14px',
                borderRadius: 999,
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all .15s',
                border: isActive ? '1px solid transparent' : '1px solid var(--color-border)',
                background: isActive ? (sc?.bg || 'var(--color-accent-dim)') : 'var(--color-surface)',
                color: isActive ? (sc?.color || 'var(--color-accent)') : 'var(--color-text-secondary)',
              }}
            >
              {SOURCE_LABELS[s] || s}
            </button>
          )
        })}
      </div>

      {/* Fallback Warning (graphify "诚实优于黑盒") */}
      {fallbackUsed && (
        <div style={{
          marginBottom: 14,
          padding: '10px 12px',
          borderRadius: 12,
          border: '1px solid rgba(251,191,36,.18)',
          background: 'var(--color-gold-dim)',
          color: 'var(--color-text-secondary)',
          fontSize: 'var(--text-sm)',
          lineHeight: 1.6,
        }}>
          ⚠️ 近 24 小时财经新闻源没有新入库，当前展示的是最近可用新闻作为证据层兜底。
        </div>
      )}

      {/* Error Display (系统化错误处理) */}
      {error && (
        <div style={{
          marginBottom: 14,
          padding: '10px 12px',
          borderRadius: 12,
          border: '1px solid rgba(239,68,68,.18)',
          background: 'var(--color-red-dim)',
          color: 'var(--color-red)',
          fontSize: 'var(--text-sm)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>❌ {error}</span>
          <button
            onClick={() => { refetch() }}
            style={{
              background: 'var(--color-red)',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 'var(--text-xs)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            重试
          </button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <LoadingSkeleton />
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-text-secondary)', fontSize: 'var(--text-base)' }}>
          暂无财经新闻
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
          {items.map((item, i) => (
            <NewsCard
              key={item.id}
              title={item.title}
              summary={item.summary}
              source={item.source}
              time={item.collected_at?.slice(11, 16)}
              url={item.url}
              index={i}
            />
          ))}
        </div>
      )}
    </div>
  )
}

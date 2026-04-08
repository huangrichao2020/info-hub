import { useEffect, useState } from 'react'
import client from '../../api/client'
import NewsCard from '../common/NewsCard'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
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
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [source, setSource] = useState('')
  const refreshKey = useAppStore((s) => s.refreshKey)

  useEffect(() => {
    setLoading(true)
    client.get('/fin-news', { params: { source, hours: 24 } }).then(({ data }) => {
      setItems(data.items || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [source, refreshKey])

  return (
    <div>
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
                fontSize: '.82em',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all .15s',
                border: isActive ? '1px solid transparent' : '1px solid var(--color-border)',
                background: isActive
                  ? (sc?.bg || 'rgba(56,189,248,.15)')
                  : 'var(--color-card)',
                color: isActive
                  ? (sc?.color || 'var(--color-accent)')
                  : 'var(--color-dim)',
              }}
            >
              {SOURCE_LABELS[s] || s}
            </button>
          )
        })}
      </div>
      {loading ? (
        <LoadingSkeleton />
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-dim)', fontSize: '.9em' }}>
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

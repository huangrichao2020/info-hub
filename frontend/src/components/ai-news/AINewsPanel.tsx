import { useEffect, useState } from 'react'
import client from '../../api/client'
import NewsCard from '../common/NewsCard'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
import type { NewsItem } from '../../types'

export default function AINewsPanel() {
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const refreshKey = useAppStore((s) => s.refreshKey)

  const fetchData = () => {
    setLoading(true)
    client.get('/ai-news', { params: { keyword } }).then(({ data }) => {
      setItems(data.items || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [refreshKey])

  return (
    <div>
      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchData()}
          placeholder="搜索 AI 新闻..."
          style={{
            flex: 1,
            background: 'var(--color-card)',
            border: '1px solid var(--color-border)',
            borderRadius: 10,
            padding: '8px 14px',
            fontSize: '.84em',
            color: 'var(--color-text)',
            outline: 'none',
            transition: 'border-color .15s',
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
          onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
        />
        <button
          onClick={fetchData}
          style={{
            padding: '8px 18px',
            borderRadius: 10,
            border: '1px solid var(--color-accent)',
            background: 'rgba(56,189,248,.08)',
            color: 'var(--color-accent)',
            fontSize: '.84em',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all .15s',
            whiteSpace: 'nowrap',
          }}
        >
          搜索
        </button>
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-dim)', fontSize: '.9em' }}>
          暂无 AI 新闻，点击搜索或等待自动采集
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
          {items.map((item, i) => (
            <NewsCard
              key={item.id}
              title={item.title}
              summary={item.summary}
              source={item.source}
              time={item.collected_at?.slice(0, 16)}
              url={item.url}
              tags={item.keywords?.split(',').filter(Boolean).slice(0, 3)}
              index={i}
            />
          ))}
        </div>
      )}
    </div>
  )
}

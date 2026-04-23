import { useState } from 'react'
import { motion } from 'framer-motion'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
import { useApiFetch } from '../../hooks/useApi'
import type { TrendingItem } from '../../types'

const PLATFORMS = [
  { key: '', label: '全部' },
  { key: 'baidu', label: '百度' },
  { key: 'weibo', label: '微博' },
  { key: 'zhihu', label: '知乎' },
  { key: 'toutiao', label: '头条' },
  { key: 'douyin', label: '抖音' },
  { key: 'xiaohongshu', label: '小红书' },
]

const PLAT_BADGE: Record<string, { bg: string; color: string; label: string }> = {
  baidu: { bg: 'var(--color-blue-dim)', color: 'var(--color-blue)', label: '百度' },
  weibo: { bg: 'var(--color-red-dim)', color: 'var(--color-red)', label: '微博' },
  zhihu: { bg: 'var(--color-blue-dim)', color: 'var(--color-blue)', label: '知乎' },
  toutiao: { bg: 'var(--color-orange-dim)', color: 'var(--color-orange)', label: '头条' },
  douyin: { bg: 'var(--color-purple-dim)', color: 'var(--color-purple)', label: '抖音' },
  xiaohongshu: { bg: 'var(--color-red-dim)', color: 'var(--color-red)', label: '小红书' },
}

export default function TrendingPanel() {
  const [platform, setPlatform] = useState('')
  const refreshKey = useAppStore((s) => s.refreshKey)

  const { data, loading, error, refetch } = useApiFetch<{ items: TrendingItem[] }>('/trending', {
    params: { platform },
    deps: [platform, refreshKey],
  })

  const items = data?.items || []

  return (
    <div>
      {/* Filter pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {PLATFORMS.map(({ key, label }) => {
          const active = platform === key
          return (
            <button
              key={key}
              onClick={() => setPlatform(key)}
              style={{
                padding: '7px 14px',
                borderRadius: 999,
                border: `1px solid ${active ? 'var(--color-accent)' : 'var(--color-border)'}`,
                background: active ? 'var(--color-accent)' : 'var(--color-surface)',
                color: active ? '#0a0e1a' : 'var(--color-text-secondary)',
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all .15s',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Error Display */}
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
          <button onClick={() => refetch()} style={{
            background: 'var(--color-red)', color: 'white', border: 'none',
            borderRadius: 6, padding: '4px 10px', fontSize: 'var(--text-xs)',
            cursor: 'pointer', fontWeight: 600,
          }}>重试</button>
        </div>
      )}

      {loading ? <LoadingSkeleton /> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {items.map((item, i) => {
            const badge = PLAT_BADGE[item.platform] || PLAT_BADGE.baidu
            return (
              <motion.a
                key={item.id}
                href={item.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.02 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px', background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)', borderRadius: 10,
                  textDecoration: 'none', transition: 'border-color .15s',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-accent)' }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-border)' }}
              >
                <span style={{
                  width: 24, textAlign: 'center', fontSize: 'var(--text-base)', fontWeight: 700,
                  color: i < 3 ? 'var(--color-red)' : 'var(--color-text-secondary)',
                }}>
                  {i + 1}
                </span>
                <span style={{
                  flex: 1, fontSize: 'var(--text-sm)', color: 'var(--color-text)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {item.title}
                </span>
                <span style={{
                  padding: '2px 8px', borderRadius: 999, fontSize: 'var(--text-xs)', fontWeight: 600,
                  background: badge.bg, color: badge.color, flexShrink: 0,
                }}>
                  {badge.label}
                </span>
                <span style={{
                  fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)',
                  fontFamily: 'monospace', flexShrink: 0, minWidth: 50, textAlign: 'right',
                }}>
                  {item.heat_score >= 10000 ? `${(item.heat_score / 10000).toFixed(1)}万` : item.heat_score?.toLocaleString()}
                </span>
              </motion.a>
            )
          })}
          {items.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-text-secondary)' }}>暂无热搜数据</div>
          )}
        </div>
      )}
    </div>
  )
}

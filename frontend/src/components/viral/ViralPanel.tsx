import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'

interface ViralItem {
  title: string
  platforms: string
  cross_platform_count: number
  max_heat: number
  total_heat: number
}

const PLAT_STYLE: Record<string, { bg: string; color: string }> = {
  baidu: { bg: 'rgba(56,189,248,.12)', color: 'var(--color-accent)' },
  weibo: { bg: 'rgba(239,68,68,.12)', color: 'var(--color-red)' },
  zhihu: { bg: 'rgba(56,189,248,.12)', color: 'var(--color-accent)' },
  toutiao: { bg: 'rgba(251,146,60,.12)', color: 'var(--color-orange)' },
  douyin: { bg: 'rgba(167,139,250,.12)', color: 'var(--color-purple)' },
  xiaohongshu: { bg: 'rgba(239,68,68,.12)', color: 'var(--color-red)' },
}

export default function ViralPanel() {
  const [items, setItems] = useState<ViralItem[]>([])
  const [loading, setLoading] = useState(true)
  const refreshKey = useAppStore((s) => s.refreshKey)

  useEffect(() => {
    setLoading(true)
    client.get('/viral/trending').then(({ data }) => setItems(data.items || [])).catch(() => {}).finally(() => setLoading(false))
  }, [refreshKey])

  if (loading) return <LoadingSkeleton />

  return (
    <div>
      <p style={{ fontSize: '.82em', color: 'var(--color-dim)', marginBottom: 16, lineHeight: 1.6 }}>
        基于跨平台热度分析 · 综合百度/微博/知乎/头条/抖音/小红书数据
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            style={{
              background: i < 3
                ? 'linear-gradient(135deg, rgba(56,189,248,.06), rgba(167,139,250,.06))'
                : 'var(--color-card)',
              border: `1px solid ${i < 3 ? 'rgba(56,189,248,.2)' : 'var(--color-border)'}`,
              borderRadius: 12,
              padding: '14px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              transition: 'border-color .2s',
              cursor: 'default',
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-accent)' }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = i < 3 ? 'rgba(56,189,248,.2)' : 'var(--color-border)' }}
          >
            {/* Rank */}
            <span style={{
              width: 28,
              textAlign: 'center',
              fontSize: i < 3 ? '1.4em' : '1.1em',
              fontWeight: 800,
              color: i < 3 ? 'var(--color-gold)' : 'var(--color-dim)',
              flexShrink: 0,
            }}>
              {i + 1}
            </span>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <h3 style={{ fontSize: '.88em', fontWeight: 600, color: 'var(--color-text)', margin: 0, lineHeight: 1.5 }}>
                {item.title}
              </h3>
              <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                {item.platforms?.split(',').map((p) => {
                  const s = PLAT_STYLE[p.trim()] || PLAT_STYLE.baidu
                  return (
                    <span key={p} style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 999,
                      fontSize: '.68em',
                      fontWeight: 600,
                      background: s.bg,
                      color: s.color,
                    }}>
                      {p.trim()}
                    </span>
                  )
                })}
              </div>
            </div>

            {/* Heat */}
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: '1.1em', fontWeight: 700, color: 'var(--color-red)' }}>
                {item.total_heat >= 10000 ? `${(item.total_heat / 10000).toFixed(1)}万` : item.total_heat.toLocaleString()}
              </div>
              <div style={{ fontSize: '.68em', color: 'var(--color-dim)' }}>综合热度</div>
            </div>
          </motion.div>
        ))}
        {items.length === 0 && (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-dim)' }}>暂无爆款数据</div>
        )}
      </div>
    </div>
  )
}

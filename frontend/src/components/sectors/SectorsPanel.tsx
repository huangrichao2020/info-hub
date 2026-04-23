import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
import type { IndexItem, SectorItem, TurnStrongRun } from '../../types'

function buildFallbackSectors(run: TurnStrongRun | null) {
  const items = run?.items || []
  const grouped = new Map<string, { name: string; count: number; total: number; leader: string }>()

  for (const item of items) {
    const concept = (item.screen?.style_concept || '')
      .split(/[、,，;/]/)
      .map((part) => part.trim())
      .filter(Boolean)[0]
    const name = concept || item.screen?.industry || '其他方向'
    const current = grouped.get(name) || { name, count: 0, total: 0, leader: item.name }
    current.count += 1
    current.total += item.live_quote?.change_pct ?? item.screen?.change_pct ?? 0
    if (!current.leader) current.leader = item.name
    grouped.set(name, current)
  }

  return Array.from(grouped.values())
    .map((group) => ({
      name: group.name,
      change_pct: group.count >= 2 ? Math.max(0.5, group.total / group.count) : Math.max(0.2, group.total / Math.max(1, group.count)),
      leader: group.leader,
    }))
    .sort((a, b) => b.change_pct - a.change_pct)
}

export default function SectorsPanel() {
  const [indices, setIndices] = useState<IndexItem[]>([])
  const [risers, setRisers] = useState<SectorItem[]>([])
  const [fallers, setFallers] = useState<SectorItem[]>([])
  const [loading, setLoading] = useState(true)
  const refreshKey = useAppStore((s) => s.refreshKey)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      client.get('/sectors/indices'),
      client.get('/sectors/movers', { params: { limit: 10, rising: true } }),
      client.get('/sectors/movers', { params: { limit: 10, rising: false } }),
      client.get<TurnStrongRun>('/turn-strong'),
    ]).then(([idxRes, upRes, downRes, turnRes]) => {
      const nextIndices = idxRes.data.items || []
      let nextRisers = upRes.data.items || []
      let nextFallers = downRes.data.items || []
      const fallback = buildFallbackSectors(turnRes.data)
      if (nextRisers.length === 0 && fallback.length > 0) {
        nextRisers = fallback.slice(0, 10)
      }
      if (nextFallers.length === 0 && fallback.length > 0) {
        nextFallers = fallback.slice(-10).reverse()
      }
      setIndices(nextIndices)
      setRisers(nextRisers)
      setFallers(nextFallers)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [refreshKey])

  if (loading) return <LoadingSkeleton count={9} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* 指数概览 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: 12,
      }}>
        {indices.map((idx, i) => {
          const isUp = idx.change_pct >= 0
          const color = isUp ? 'var(--color-red)' : 'var(--color-green)'
          const isTop3 = i < 3
          return (
            <motion.div
              key={idx.name}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
              style={{
                background: isTop3
                  ? `linear-gradient(135deg, var(--color-card), ${isUp ? 'rgba(239,68,68,.06)' : 'rgba(74,222,128,.06)'})`
                  : 'var(--color-card)',
                borderRadius: 12,
                padding: '14px 12px',
                border: isTop3
                  ? `1px solid ${isUp ? 'rgba(239,68,68,.2)' : 'rgba(74,222,128,.2)'}`
                  : '1px solid var(--color-border)',
                textAlign: 'center',
                transition: 'border-color .2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = isTop3
                  ? (isUp ? 'rgba(239,68,68,.2)' : 'rgba(74,222,128,.2)')
                  : 'var(--color-border)'
              }}
            >
              <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>{idx.name}</div>
              <div style={{ fontSize: '1.1em', fontWeight: 600, marginTop: 4, color }}>{idx.price}</div>
              <div style={{ fontSize: '.72em', color }}>
                {isUp ? '+' : ''}{idx.change_pct}%
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* 板块涨跌 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 }}>
        <div>
          <h3 style={{ fontSize: '.88em', fontWeight: 600, color: 'var(--color-red)', marginBottom: 12 }}>
            领涨板块
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {risers.map((s, i) => (
              <SectorRow key={s.name} item={s} index={i} rising />
            ))}
          </div>
        </div>
        <div>
          <h3 style={{ fontSize: '.88em', fontWeight: 600, color: 'var(--color-green)', marginBottom: 12 }}>
            领跌板块
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {fallers.map((s, i) => (
              <SectorRow key={s.name} item={s} index={i} rising={false} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function SectorRow({ item, index, rising }: { item: SectorItem; index: number; rising: boolean }) {
  const color = rising ? 'var(--color-red)' : 'var(--color-green)'
  const pct = Math.abs(item.change_pct)
  const barWidth = Math.min(pct * 10, 100)
  const isTop3 = index < 3
  const barBg = rising ? 'rgba(239,68,68,.12)' : 'rgba(74,222,128,.12)'

  return (
    <motion.div
      initial={{ opacity: 0, x: rising ? -8 : 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.03 }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 14px',
        background: isTop3
          ? `linear-gradient(90deg, var(--color-card), ${barBg})`
          : 'var(--color-card)',
        borderRadius: 12,
        border: isTop3
          ? `1px solid ${rising ? 'rgba(239,68,68,.18)' : 'rgba(74,222,128,.18)'}`
          : '1px solid var(--color-border)',
        transition: 'border-color .2s',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = isTop3
          ? (rising ? 'rgba(239,68,68,.18)' : 'rgba(74,222,128,.18)')
          : 'var(--color-border)'
      }}
    >
      {isTop3 && (
        <span style={{
          fontSize: '.7em',
          fontWeight: 700,
          color: rising ? 'var(--color-gold)' : 'var(--color-dim)',
          minWidth: 16,
        }}>
          {index + 1}
        </span>
      )}
      <span style={{
        fontSize: '.84em',
        fontWeight: 600,
        color: 'var(--color-text)',
        width: 96,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {item.name}
      </span>
      <div style={{
        flex: 1,
        height: 6,
        background: 'rgba(30,41,59,.5)',
        borderRadius: 999,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          borderRadius: 999,
          backgroundColor: color,
          width: `${barWidth}%`,
          transition: 'width .4s ease',
        }} />
      </div>
      <span style={{
        fontSize: '.84em',
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        width: 64,
        textAlign: 'right',
        color,
      }}>
        {rising ? '+' : '-'}{pct.toFixed(2)}%
      </span>
    </motion.div>
  )
}

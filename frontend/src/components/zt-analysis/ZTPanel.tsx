import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
import type { ZTStock } from '../../types'

export default function ZTPanel() {
  const [items, setItems] = useState<ZTStock[]>([])
  const [lianban, setLianban] = useState<ZTStock[]>([])
  const [loading, setLoading] = useState(true)
  const refreshKey = useAppStore((s) => s.refreshKey)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      client.get('/zt/today'),
      client.get('/zt/lianban'),
    ]).then(([todayRes, lianbanRes]) => {
      setItems(todayRes.data.items || [])
      setLianban(lianbanRes.data.items || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [refreshKey])

  if (loading) return <LoadingSkeleton count={9} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* 连板梯队 */}
      {lianban.length > 0 && (
        <div>
          <h3 style={{ fontSize: '.88em', fontWeight: 600, color: 'var(--color-red)', marginBottom: 12 }}>
            连板梯队
          </h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {lianban.map((s, i) => {
              const isTop3 = i < 3
              return (
                <motion.div
                  key={s.code}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.05 }}
                  style={{
                    background: isTop3
                      ? 'linear-gradient(135deg, var(--color-card), rgba(251,191,36,.06))'
                      : 'var(--color-card)',
                    borderRadius: 12,
                    padding: '14px 16px',
                    border: isTop3
                      ? '1px solid rgba(251,191,36,.2)'
                      : '1px solid rgba(239,68,68,.2)',
                    minWidth: 120,
                    transition: 'border-color .2s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = isTop3
                      ? 'rgba(251,191,36,.2)'
                      : 'rgba(239,68,68,.2)'
                  }}
                >
                  <div style={{ fontSize: '.84em', fontWeight: 600, color: 'var(--color-text)' }}>{s.name}</div>
                  <div style={{ fontSize: '.68em', color: 'var(--color-dim)', marginTop: 2 }}>{s.code}</div>
                  <div style={{
                    marginTop: 6,
                    fontSize: '1.15em',
                    fontWeight: 700,
                    color: isTop3 ? 'var(--color-gold)' : 'var(--color-red)',
                  }}>
                    {s.lianban_count}板
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* 今日涨停 */}
      <div>
        <h3 style={{ fontSize: '.88em', fontWeight: 600, color: 'var(--color-text)', marginBottom: 12 }}>
          今日涨停 ({items.length})
        </h3>
        {items.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-dim)', fontSize: '.9em' }}>
            暂无涨停数据
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
            {items.map((s, i) => {
              const isTop3 = i < 3
              return (
                <motion.div
                  key={s.code}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02, duration: 0.25 }}
                  style={{
                    background: isTop3
                      ? 'linear-gradient(135deg, var(--color-card), rgba(239,68,68,.05))'
                      : 'var(--color-card)',
                    borderRadius: 12,
                    padding: '14px 16px',
                    border: isTop3
                      ? '1px solid rgba(239,68,68,.18)'
                      : '1px solid var(--color-border)',
                    transition: 'border-color .2s',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = isTop3
                      ? 'rgba(239,68,68,.18)'
                      : 'var(--color-border)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <span style={{ fontSize: '.84em', fontWeight: 600, color: 'var(--color-text)' }}>{s.name}</span>
                      <span style={{ marginLeft: 8, fontSize: '.72em', color: 'var(--color-dim)' }}>{s.code}</span>
                    </div>
                    <span style={{
                      fontSize: '.84em',
                      fontWeight: 600,
                      color: isTop3 ? 'var(--color-gold)' : 'var(--color-red)',
                    }}>
                      +{s.change_pct?.toFixed(2)}%
                    </span>
                  </div>
                  {s.reason && (
                    <div style={{ fontSize: '.78em', color: 'var(--color-dim)', lineHeight: 1.5 }}>
                      {s.reason}
                    </div>
                  )}
                  {s.popularity_score != null && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                      <div style={{ fontSize: '.68em', color: 'var(--color-dim)' }}>人气</div>
                      <div style={{
                        flex: 1,
                        height: 5,
                        background: 'rgba(30,41,59,.5)',
                        borderRadius: 999,
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          background: 'var(--color-accent)',
                          borderRadius: 999,
                          width: `${Math.min(s.popularity_score, 100)}%`,
                          transition: 'width .4s ease',
                        }} />
                      </div>
                      <div style={{
                        fontSize: '.68em',
                        fontVariantNumeric: 'tabular-nums',
                        color: 'var(--color-accent)',
                      }}>
                        {s.popularity_score}
                      </div>
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

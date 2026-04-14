import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CalendarDays, ChevronDown, ChevronRight, TrendingUp, AlertCircle, Clock } from 'lucide-react'
import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import type { CalendarEvent, CalendarResponse } from '../../types'

const LEVEL_STYLES: Record<string, { bg: string; color: string; label: string; icon: any }> = {
  major: { bg: 'var(--color-red-dim)', color: 'var(--color-red)', label: '重大', icon: AlertCircle },
  moderate: { bg: 'var(--color-gold-dim)', color: 'var(--color-gold)', label: '重要', icon: Clock },
  minor: { bg: 'var(--color-blue-dim)', color: 'var(--color-blue)', label: '一般', icon: CalendarDays },
}

const TYPE_STYLES: Record<string, string> = {
  meeting: 'var(--color-purple)',
  policy: 'var(--color-accent)',
  economic_data: 'var(--color-gold)',
  earnings: 'var(--color-orange)',
  market: 'var(--color-blue)',
}

const TYPE_LABELS: Record<string, string> = {
  meeting: '重要会议',
  policy: '政策发布',
  economic_data: '经济数据',
  earnings: '财报披露',
  market: '市场事件',
}

export default function InvestmentCalendarPanel() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set())
  const [filterLevel, setFilterLevel] = useState('')
  const [filterType, setFilterType] = useState('')

  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10)
    const endDate = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
    setLoading(true)
    client.get<CalendarResponse>('/investment-calendar/events', {
      params: { start_date: today, end_date: endDate },
    })
      .then((res) => {
        setEvents(res.data.events || [])
        // Auto-expand first 3 dates
        const firstDates = new Set<string>()
        const seen = new Set<string>()
        for (const evt of res.data.events) {
          if (!seen.has(evt.date)) {
            seen.add(evt.date)
            if (firstDates.size < 5) firstDates.add(evt.date)
          }
        }
        setExpandedDates(firstDates)
      })
      .finally(() => setLoading(false))
  }, [])

  // Group events by date
  const groupedByDate: Record<string, CalendarEvent[]> = {}
  for (const evt of events) {
    if (filterLevel && evt.level !== filterLevel) continue
    if (filterType && evt.type !== filterType) continue
    if (!groupedByDate[evt.date]) groupedByDate[evt.date] = []
    groupedByDate[evt.date].push(evt)
  }

  const sortedDates = Object.keys(groupedByDate).sort()

  const toggleDate = (date: string) => {
    setExpandedDates((prev) => {
      const next = new Set(prev)
      if (next.has(date)) next.delete(date)
      else next.add(date)
      return next
    })
  }

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return {
      full: `${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`,
      short: `${d.getMonth() + 1}/${d.getDate()}`,
    }
  }

  if (loading) return <LoadingSkeleton count={8} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* Header */}
      <section
        style={{
          borderRadius: 20,
          padding: 18,
          background: 'linear-gradient(145deg, rgba(56,189,248,.12), rgba(15,23,42,.96) 55%)',
          border: '1px solid rgba(56,189,248,.18)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <CalendarDays size={20} style={{ color: 'var(--color-accent)' }} />
          <div>
            <h3 style={{ fontSize: '1.52rem', letterSpacing: '-0.04em', fontWeight: 700 }}>投资日历</h3>
            <div style={{ marginTop: 4, fontSize: '.84em', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              未来 90 天重要会议、经济数据、政策发布日程及受益板块与龙头个股
            </div>
          </div>
        </div>

        {/* Filters */}
        <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: '.76em', color: 'var(--color-text-secondary)', lineHeight: '32px' }}>级别：</span>
          {['', 'major', 'moderate', 'minor'].map((level) => (
            <button
              key={level}
              onClick={() => setFilterLevel(level)}
              style={{
                padding: '4px 12px',
                borderRadius: 999,
                fontSize: '.74em',
                fontWeight: 600,
                border: filterLevel === level ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                background: filterLevel === level ? 'var(--color-accent-dim)' : 'var(--color-surface)',
                color: filterLevel === level ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
              }}
            >
              {level ? LEVEL_STYLES[level]?.label || level : '全部'}
            </button>
          ))}
          <span style={{ fontSize: '.76em', color: 'var(--color-text-secondary)', lineHeight: '32px', marginLeft: 8 }}>类型：</span>
          {['', 'meeting', 'policy', 'economic_data', 'earnings', 'market'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              style={{
                padding: '4px 12px',
                borderRadius: 999,
                fontSize: '.74em',
                fontWeight: 600,
                border: filterType === type ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                background: filterType === type ? 'var(--color-accent-dim)' : 'var(--color-surface)',
                color: filterType === type ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
              }}
            >
              {type ? TYPE_LABELS[type] || type : '全部'}
            </button>
          ))}
        </div>
      </section>

      {/* Event list */}
      {sortedDates.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-text-secondary)', fontSize: '.9em' }}>
          暂无符合条件的事件
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sortedDates.map((date) => {
            const dayEvents = groupedByDate[date]
            const isExpanded = expandedDates.has(date)
            const { full } = formatDate(date)
            const levelCounts: Record<string, number> = { major: 0, moderate: 0, minor: 0 }
            dayEvents.forEach((e) => { levelCounts[e.level] = (levelCounts[e.level] || 0) + 1 })

            return (
              <motion.div
                key={date}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  borderRadius: 16,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  overflow: 'hidden',
                }}
              >
                {/* Date header */}
                <button
                  onClick={() => toggleDate(date)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 18px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'inherit',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{
                      fontSize: '1.08em',
                      fontWeight: 700,
                      color: 'var(--color-text)',
                    }}>
                      {full}
                    </span>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {levelCounts.major > 0 && (
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: 999,
                          fontSize: '.68em',
                          background: 'var(--color-red-dim)',
                          color: 'var(--color-red)',
                          fontWeight: 600,
                        }}>
                          重大 {levelCounts.major}
                        </span>
                      )}
                      {levelCounts.moderate > 0 && (
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: 999,
                          fontSize: '.68em',
                          background: 'var(--color-gold-dim)',
                          color: 'var(--color-gold)',
                          fontWeight: 600,
                        }}>
                          重要 {levelCounts.moderate}
                        </span>
                      )}
                    </div>
                  </div>
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>

                {/* Events */}
                {isExpanded && (
                  <div style={{ padding: '0 18px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {dayEvents.map((evt, idx) => {
                      const levelStyle = LEVEL_STYLES[evt.level] || LEVEL_STYLES.minor
                      const typeColor = TYPE_STYLES[evt.type] || 'var(--color-text-secondary)'
                      const LevelIcon = levelStyle.icon

                      return (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.05 }}
                          style={{
                            padding: '12px 14px',
                            borderRadius: 12,
                            border: '1px solid var(--color-border)',
                            background: 'rgba(15,23,42,.4)',
                          }}
                        >
                          {/* Title row */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                            <LevelIcon size={14} style={{ color: levelStyle.color }} />
                            <span style={{ fontSize: '.92em', fontWeight: 700, color: 'var(--color-text)' }}>
                              {evt.title}
                            </span>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: 4,
                              fontSize: '.64em',
                              background: levelStyle.bg,
                              color: levelStyle.color,
                              fontWeight: 600,
                            }}>
                              {levelStyle.label}
                            </span>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: 4,
                              fontSize: '.64em',
                              background: `${typeColor}18`,
                              color: typeColor,
                              fontWeight: 600,
                            }}>
                              {TYPE_LABELS[evt.type] || evt.type}
                            </span>
                          </div>

                          {/* Description */}
                          <div style={{ fontSize: '.8em', color: 'var(--color-text-secondary)', lineHeight: 1.6, marginBottom: 10 }}>
                            {evt.description}
                          </div>

                          {/* Benefit sectors */}
                          {evt.benefit_sectors.length > 0 && (
                            <div style={{ marginBottom: 8 }}>
                              <div style={{ fontSize: '.72em', color: 'var(--color-text-tertiary)', marginBottom: 4 }}>受益板块</div>
                              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                {evt.benefit_sectors.map((sector) => (
                                  <span
                                    key={sector}
                                    style={{
                                      padding: '3px 8px',
                                      borderRadius: 999,
                                      fontSize: '.7em',
                                      background: 'var(--color-accent-dim)',
                                      color: 'var(--color-accent)',
                                      fontWeight: 500,
                                    }}
                                  >
                                    <TrendingUp size={10} style={{ marginRight: 3, verticalAlign: 'middle' }} />
                                    {sector}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Leading stocks */}
                          {evt.leading_stocks.length > 0 && (
                            <div>
                              <div style={{ fontSize: '.72em', color: 'var(--color-text-tertiary)', marginBottom: 4 }}>龙头个股</div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {evt.leading_stocks.map((stock) => (
                                  <div
                                    key={stock.code}
                                    style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 8,
                                      padding: '4px 8px',
                                      borderRadius: 6,
                                      background: 'rgba(56,189,248,.06)',
                                      fontSize: '.76em',
                                    }}
                                  >
                                    <span style={{ fontWeight: 700, color: 'var(--color-text)' }}>{stock.name}</span>
                                    <span style={{ color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>{stock.code}</span>
                                    <span style={{ color: 'var(--color-text-secondary)', flex: 1 }}>{stock.reason}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </motion.div>
                      )
                    })}
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}

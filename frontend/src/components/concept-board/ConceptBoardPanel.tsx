import { useEffect, useMemo, useState } from 'react'

import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import type { TurnStrongRun, TurnStrongStock } from '../../types'

function parseMarketValue(value?: string) {
  if (!value) return 0
  const normalized = value.replace(/,/g, '').trim()
  const match = normalized.match(/([\d.]+)\s*(亿|万)?/)
  if (!match) return 0
  const num = Number(match[1] || 0)
  const unit = match[2] || ''
  if (unit === '亿') return num
  if (unit === '万') return num / 10000
  return num
}

function computeScore(item: TurnStrongStock) {
  const screen = item.screen || {}
  const analysis = item.analysis || {}
  let score = 40
  if (analysis.recommendation === 'buy') score += 24
  if (analysis.recommendation === 'watch') score += 10
  if (analysis.recommendation === 'avoid') score -= 12
  score += Math.min(12, (screen.auction_volume_ratio ?? 0) * 3)
  score += Math.max(0, Math.min(10, (screen.auction_change_pct ?? 0) * 4))
  score += Math.max(0, Math.min(8, ((screen.current_profit_ratio ?? 0) - (screen.previous_profit_ratio ?? 0)) / 2))
  if ((item.news_items || []).length > 0) score += 4
  return Math.max(0, Math.min(100, Math.round(score)))
}

function groupKey(item: TurnStrongStock) {
  const concept = (item.screen?.style_concept || '')
    .split(/[、,，;/]/)
    .map((part) => part.trim())
    .filter(Boolean)[0]
  return concept || item.screen?.industry || '其他方向'
}

function roleLabel(item: TurnStrongStock, position: number) {
  const marketValueYi = parseMarketValue(item.screen?.total_market_value)
  const turnoverValueYi = parseMarketValue(item.screen?.trading_amount)
  if (marketValueYi >= 250 || turnoverValueYi >= 25) return '中军'
  if (position === 0) return '龙头'
  return '跟风'
}

function gradeLabel(size: number, avgTopScore: number) {
  if (size >= 3 && avgTopScore >= 78) return { label: 'S', text: '强主线', color: 'var(--color-red)' }
  if (size >= 3 && avgTopScore >= 66) return { label: 'A', text: '强联动', color: 'var(--color-orange)' }
  if (size >= 2 && avgTopScore >= 58) return { label: 'B', text: '可跟踪', color: 'var(--color-gold)' }
  if (size >= 2) return { label: 'C', text: '弱联动', color: 'var(--color-accent)' }
  return { label: 'D', text: '单点异动', color: 'var(--color-dim)' }
}

export default function ConceptBoardPanel() {
  const [run, setRun] = useState<TurnStrongRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeGroup, setActiveGroup] = useState('')

  useEffect(() => {
    setLoading(true)
    client.get<TurnStrongRun>('/turn-strong')
      .then((response) => setRun(response.data))
      .catch(() => setRun(null))
      .finally(() => setLoading(false))
  }, [])

  const groups = useMemo(() => {
    const items = run?.items || []
    const map = new Map<string, { key: string; items: Array<{ item: TurnStrongStock; score: number; role: string }>; avgTopScore: number; grade: { label: string; text: string; color: string } }>()
    for (const item of items) {
      const key = groupKey(item)
      const current = map.get(key) || { key, items: [], avgTopScore: 0, grade: { label: 'D', text: '单点异动', color: 'var(--color-dim)' } }
      current.items.push({ item, score: computeScore(item), role: '跟风' })
      map.set(key, current)
    }
    const values = Array.from(map.values()).map((group) => {
      group.items.sort((a, b) => b.score - a.score || a.item.rank - b.item.rank)
      group.items = group.items.map((entry, index) => ({ ...entry, role: roleLabel(entry.item, index) }))
      const top = group.items.slice(0, 2)
      group.avgTopScore = Math.round(top.reduce((sum, entry) => sum + entry.score, 0) / Math.max(1, top.length))
      group.grade = gradeLabel(group.items.length, group.avgTopScore)
      return group
    })
    const filtered = values.filter((group) => group.grade.label !== 'D')
    filtered.sort((a, b) => {
      const rank = ['S', 'A', 'B', 'C', 'D']
      return rank.indexOf(a.grade.label) - rank.indexOf(b.grade.label) || b.items.length - a.items.length || b.avgTopScore - a.avgTopScore
    })
    return filtered
  }, [run])

  useEffect(() => {
    if (groups.length && !activeGroup) {
      setActiveGroup(groups[0].key)
    }
  }, [groups, activeGroup])

  const selected = groups.find((group) => group.key === activeGroup) || groups[0]

  if (loading) return <LoadingSkeleton count={6} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <section style={{ borderRadius: 20, padding: 20, background: 'linear-gradient(145deg, rgba(251,146,60,.14), rgba(15,23,42,.95) 55%)', border: '1px solid rgba(251,146,60,.18)' }}>
        <div style={{ fontSize: '.8em', color: 'var(--color-orange)', fontWeight: 700 }}>概念作战图</div>
        <h3 style={{ marginTop: 10, fontSize: '1.58rem', letterSpacing: '-0.04em' }}>先看概念强弱，再看组内龙头梯队</h3>
        <p style={{ marginTop: 10, color: 'var(--color-dim)', lineHeight: 1.8, maxWidth: 760 }}>
          这里先把转强候选池按概念/行业聚类，再给每组一个 `S/A/B/C/D` 等级，帮助你优先看主线、联动和单点异动。
        </p>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 14 }}>
        {groups.map((group) => (
          <button
            key={group.key}
            onClick={() => setActiveGroup(group.key)}
            style={{
              textAlign: 'left',
              borderRadius: 18,
              padding: 16,
              border: `1px solid ${activeGroup === group.key ? 'rgba(56,189,248,.22)' : 'rgba(148,163,184,.12)'}`,
              background: activeGroup === group.key ? 'rgba(56,189,248,.08)' : 'rgba(15,23,42,.48)',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontSize: '.96em', fontWeight: 800 }}>{group.key}</div>
                <div style={{ marginTop: 4, fontSize: '.72em', color: 'var(--color-dim)' }}>
                  同组 {group.items.length} 只 · 前排均分 {group.avgTopScore}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 900, color: group.grade.color }}>{group.grade.label}</div>
                <div style={{ fontSize: '.72em', color: group.grade.color, fontWeight: 700 }}>{group.grade.text}</div>
              </div>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 6 }}>
              {group.items.slice(0, 3).map((entry, index) => (
                <div key={entry.item.code} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: '.8em' }}>
                  <div>{['龙一', '龙二', '龙三'][index] || '观察'} · {entry.item.name}</div>
                  <div style={{ color: 'var(--color-dim)' }}>{entry.score}分</div>
                </div>
              ))}
            </div>
          </button>
        ))}
      </section>

      {selected && (
        <section style={{ borderRadius: 20, padding: 20, background: 'rgba(15,23,42,.56)', border: '1px solid rgba(148,163,184,.12)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '.82em', color: selected.grade.color, fontWeight: 700 }}>概念详情</div>
              <h4 style={{ marginTop: 8, fontSize: '1.4rem', fontWeight: 800 }}>{selected.key}</h4>
              <div style={{ marginTop: 6, fontSize: '.78em', color: 'var(--color-dim)' }}>
                分级 {selected.grade.label} · {selected.grade.text} · 共 {selected.items.length} 只
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(120px, 1fr))', gap: 10, minWidth: 380 }}>
              <Metric title="概念等级" value={selected.grade.label} accent={selected.grade.color} />
              <Metric title="候选数量" value={`${selected.items.length} 只`} accent="var(--color-accent)" />
              <Metric title="前排均分" value={`${selected.avgTopScore}`} accent="var(--color-gold)" />
            </div>
          </div>

          <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
            {selected.items.slice(0, 9).map((entry, index) => (
              <div
                key={entry.item.code}
                style={{
                  borderRadius: 16,
                  padding: 14,
                  background: 'var(--color-card)',
                  border: '1px solid rgba(148,163,184,.12)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '.74em', color: 'var(--color-gold)', fontWeight: 800 }}>{['龙一', '龙二', '龙三'][index] || '跟踪'}</span>
                      <span style={{ fontSize: '.9em', fontWeight: 700 }}>{entry.item.name}</span>
                    </div>
                    <div style={{ marginTop: 4, fontSize: '.72em', color: 'var(--color-dim)' }}>
                      {entry.item.code} · {entry.role}
                    </div>
                  </div>
                  <div style={{ fontSize: '.82em', color: entry.score >= 70 ? 'var(--color-red)' : 'var(--color-gold)', fontWeight: 800 }}>
                    {entry.score}分
                  </div>
                </div>
                <div style={{ marginTop: 10, display: 'grid', gap: 6, fontSize: '.76em', color: 'var(--color-dim)' }}>
                  <div>竞价量比：{entry.item.screen.auction_volume_ratio ?? '--'}</div>
                  <div>竞价涨幅：{entry.item.screen.auction_change_pct ?? '--'}%</div>
                  <div>来源：{(entry.item.source_tags || []).join(' / ') || '--'}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function Metric({ title, value, accent }: { title: string; value: string; accent: string }) {
  return (
    <div style={{ borderRadius: 14, padding: '12px 14px', background: 'var(--color-card)', border: '1px solid rgba(148,163,184,.12)' }}>
      <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: '1.04em', fontWeight: 800, color: accent }}>{value}</div>
    </div>
  )
}

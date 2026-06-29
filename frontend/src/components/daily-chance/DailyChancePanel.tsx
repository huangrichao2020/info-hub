import { useEffect, useState } from 'react'
import { Target, Zap, AlertCircle, Activity, TrendingUp } from 'lucide-react'

interface Chance {
  code: string
  name: string
  track: string
  choke_score: number
  logic: string
  grade: 'S' | 'A' | 'B'
  score: number
  reason: string
  signals: string[]
  action: string
}

interface Market {
  indices: any[]
  main_lines: any[]
  hot_sectors: string[]
  zt_count: number
}

interface DailyChanceData {
  date: string
  is_trade_time: boolean
  market: Market
  S: Chance[]
  A: Chance[]
  B: Chance[]
  stats: {
    total_pool: number
    s_count: number
    a_count: number
    b_count: number
  }
}

const GRADE_COLORS = {
  S: { bg: 'rgba(255, 71, 87, 0.15)', border: '#ff4757', text: '#ff4757', label: '重点讲解' },
  A: { bg: 'rgba(255, 184, 0, 0.12)', border: '#ffb800', text: '#ffb800', label: '简略分析' },
  B: { bg: 'rgba(154, 163, 187, 0.08)', border: '#4a5170', text: '#9aa3bb', label: '参考' },
}

export default function DailyChancePanel() {
  const [data, setData] = useState<DailyChanceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/daily-chance/today')
      .then(r => r.json())
      .then(res => {
        if (res.status === 'ok') {
          setData(res.data)
        } else {
          setError(res.message || '未知错误')
        }
      })
      .catch(err => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ padding: 32, color: '#9aa3bb' }}>
        <Activity size={20} className="spin" /> 扫描今日机会...
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={{ padding: 32, color: '#ff4757' }}>
        <AlertCircle size={20} /> 扫描失败：{error}
      </div>
    )
  }

  return (
    <div style={{ padding: 24, maxWidth: 1240, margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1a2138 0%, #131829 100%)',
          border: '1px solid #2a3252',
          borderRadius: 16,
          padding: 28,
          marginBottom: 20,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: 'linear-gradient(90deg, #ff4757, #00d4ff, #ffd700)',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <Target size={28} color="#ff4757" />
          <div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>每日 S/A/B 机会</div>
            <div style={{ fontSize: 13, color: '#9aa3bb', marginTop: 4 }}>
              {data.date} · {data.is_trade_time ? '🟢 交易时段' : '⚫ 非交易时段'} · 标的池 {data.stats.total_pool} 只
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 20 }}>
          <Metric label="S 级重点" value={data.stats.s_count} color="#ff4757" />
          <Metric label="A 级简略" value={data.stats.a_count} color="#ffb800" />
          <Metric label="B 级参考" value={data.stats.b_count} color="#9aa3bb" />
          <Metric label="今日涨停" value={data.market.zt_count || 0} color="#ff4757" />
        </div>
        {data.market.main_lines.length > 0 && (
          <div style={{ marginTop: 16, fontSize: 13, color: '#9aa3bb' }}>
            <strong style={{ color: '#e8ecf5' }}>今日主线：</strong>
            {data.market.main_lines
              .slice(0, 5)
              .map((m: any, i) => (typeof m === 'string' ? m : m.name || JSON.stringify(m)))
              .join(' · ')}
          </div>
        )}
      </div>

      {/* S 级 - 详细讲解 */}
      {data.S.length > 0 && (
        <Section title="🅢 S 级 · 重点讲解" hint="每日 1-3 只，详细分析产业链定位 + 卡脖子逻辑 + 资金信号 + 介入建议" color="#ff4757">
          {data.S.map(stock => (
            <SCard key={stock.code} stock={stock} />
          ))}
        </Section>
      )}

      {/* A 级 - 简略分析 */}
      {data.A.length > 0 && (
        <Section title="🅐 A 级 · 简略分析" hint="卡脖子定位 + 板块强势，可观察等待回踩" color="#ffb800">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {data.A.map(stock => (
              <CompactCard key={stock.code} stock={stock} />
            ))}
          </div>
        </Section>
      )}

      {/* B 级 - 参考 */}
      {data.B.length > 0 && (
        <Section title="🅑 B 级 · 参考清单" hint="板块异动或卡脖子参考，仅供板块联动观察" color="#9aa3bb">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2a3252', color: '#9aa3bb' }}>
                <th style={{ padding: '10px 8px', textAlign: 'left' }}>代码</th>
                <th style={{ padding: '10px 8px', textAlign: 'left' }}>名称</th>
                <th style={{ padding: '10px 8px', textAlign: 'left' }}>赛道</th>
                <th style={{ padding: '10px 8px', textAlign: 'left' }}>卡脖子</th>
                <th style={{ padding: '10px 8px', textAlign: 'left' }}>信号</th>
              </tr>
            </thead>
            <tbody>
              {data.B.map(s => (
                <tr key={s.code} style={{ borderBottom: '1px dashed #2a3252' }}>
                  <td style={{ padding: '8px' }}>
                    <span style={{ background: '#00d4ff', color: '#0a0e1a', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
                      {s.code}
                    </span>
                  </td>
                  <td style={{ padding: '8px', fontWeight: 600 }}>{s.name}</td>
                  <td style={{ padding: '8px', color: '#9aa3bb' }}>{s.track}</td>
                  <td style={{ padding: '8px', color: '#ffd700' }}>{s.choke_score}/10</td>
                  <td style={{ padding: '8px', color: '#9aa3bb', fontSize: 12 }}>{s.signals.join(' · ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      {/* Footer */}
      <div style={{ marginTop: 32, padding: 16, background: '#131829', borderRadius: 8, fontSize: 12, color: '#9aa3bb', lineHeight: 1.8 }}>
        <strong style={{ color: '#00d4ff' }}>方法论声明</strong> · 基于 Serenity 卡脖子框架 v2.0 + 当日市场信号综合评分。<br />
        <strong>S 级</strong> = 卡脖子评分 ≥ 8.5 + 主线/板块联动 + 短期催化，重点详细讲解<br />
        <strong>A 级</strong> = 卡脖子评分 ≥ 7.5 + 板块强势，简略分析供参考<br />
        <strong>B 级</strong> = 卡脖子参考，仅作板块联动观察<br />
        ⚠️ 不构成投资建议 · 实时行情 / PE / 资金数据需独立核实 · 卡脖子评分 1-10 为主观判断
      </div>
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ background: '#131829', padding: 14, borderRadius: 8, border: '1px solid #2a3252' }}>
      <div style={{ fontSize: 12, color: '#9aa3bb', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
    </div>
  )
}

function Section({ title, hint, color, children }: { title: string; hint: string; color: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color }}>{title}</h2>
        <span style={{ fontSize: 12, color: '#9aa3bb' }}>{hint}</span>
      </div>
      {children}
    </div>
  )
}

function SCard({ stock }: { stock: Chance }) {
  const c = GRADE_COLORS.S
  return (
    <div
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: 20,
        marginBottom: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
        <span
          style={{
            background: c.border,
            color: '#fff',
            padding: '4px 10px',
            borderRadius: 6,
            fontWeight: 700,
            fontSize: 13,
          }}
        >
          S
        </span>
        <span style={{ background: '#00d4ff', color: '#0a0e1a', padding: '3px 10px', borderRadius: 6, fontSize: 12, fontWeight: 700 }}>
          {stock.code}
        </span>
        <span style={{ fontSize: 20, fontWeight: 700 }}>{stock.name}</span>
        <span style={{ fontSize: 12, color: '#9aa3bb', marginLeft: 'auto' }}>
          {stock.track} · 卡脖子 {stock.choke_score}/10
        </span>
      </div>

      <div style={{ fontSize: 14, color: '#e8ecf5', marginBottom: 12, lineHeight: 1.7 }}>
        <strong style={{ color: c.text }}>卡脖子定位：</strong>
        {stock.logic}
      </div>

      <div style={{ fontSize: 13, color: '#9aa3bb', marginBottom: 8 }}>
        <strong style={{ color: '#e8ecf5' }}>为什么是 S：</strong>
        {stock.reason}
      </div>

      {stock.signals.length > 0 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          {stock.signals.map((s, i) => (
            <span
              key={i}
              style={{
                background: 'rgba(0, 212, 255, 0.15)',
                color: '#00d4ff',
                padding: '3px 8px',
                borderRadius: 4,
                fontSize: 12,
                border: '1px solid #00d4ff',
              }}
            >
              {s}
            </span>
          ))}
        </div>
      )}

      <div
        style={{
          background: 'rgba(0, 212, 255, 0.08)',
          borderLeft: '3px solid #00d4ff',
          padding: '10px 14px',
          borderRadius: 6,
          fontSize: 13,
          color: '#e8ecf5',
          marginTop: 8,
        }}
      >
        <Zap size={14} color="#00d4ff" style={{ display: 'inline', marginRight: 6 }} />
        <strong>操作建议：</strong>
        {stock.action}
      </div>
    </div>
  )
}

function CompactCard({ stock }: { stock: Chance }) {
  const c = GRADE_COLORS.A
  return (
    <div
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        borderRadius: 8,
        padding: 14,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span
          style={{
            background: c.border,
            color: '#0a0e1a',
            padding: '2px 8px',
            borderRadius: 4,
            fontWeight: 700,
            fontSize: 12,
          }}
        >
          A
        </span>
        <span style={{ fontSize: 15, fontWeight: 700 }}>{stock.name}</span>
        <span style={{ fontSize: 11, color: '#9aa3bb', marginLeft: 'auto' }}>{stock.code}</span>
      </div>
      <div style={{ fontSize: 12, color: '#e8ecf5', marginBottom: 6, lineHeight: 1.6 }}>
        {stock.logic}
      </div>
      <div style={{ fontSize: 11, color: c.text }}>{stock.reason}</div>
      {stock.signals.length > 0 && (
        <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
          {stock.signals.map((s, i) => (
            <span key={i} style={{ fontSize: 10, color: '#00d4ff' }}>
              · {s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
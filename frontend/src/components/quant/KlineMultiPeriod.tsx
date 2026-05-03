/**
 * 多周期K线面板 — AmazingData 多周期对比
 * 日线 + 60分钟 + 15分钟 + 1分钟
 */
import { useState, useEffect } from 'react'
import { Loader2, Search, BarChart3 } from 'lucide-react'
import apiClient from '../../api/client'
import type { AmazingDataKlineItem } from '../../types'

const PERIOD_LABELS: Record<string, string> = {
  day: '日线',
  min60: '60分钟',
  min15: '15分钟',
  min1: '1分钟',
}

const PERIOD_COLORS: Record<string, string> = {
  day: '#3b82f6',
  min60: '#f59e0b',
  min15: '#10b981',
  min1: '#8b5cf6',
}

export default function KlineMultiPeriod() {
  const [code, setCode] = useState('600519.SH')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<Record<string, { period: string; count: number; items: AmazingDataKlineItem[] }> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchKline = async () => {
    if (!code.trim()) return
    setLoading(true)
    setError(null)
    try {
      const resp = await apiClient.get('/amazingdata-market/amazingdata/multi-period', {
        params: { code: code.trim().toUpperCase() },
      })
      setData(resp.data.series)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '请求失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKline()
  }, [])

  return (
    <div style={{ padding: '16px 24px' }}>
      {/* 输入区 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 20,
        padding: '12px 16px',
        background: 'var(--color-card)',
        borderRadius: 10,
        border: '1px solid var(--color-border)',
      }}>
        <Search size={18} style={{ color: 'var(--color-dim)' }} />
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchKline()}
          placeholder="输入股票代码，如 600519.SH"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--color-text)',
            fontSize: 15,
            fontWeight: 600,
          }}
        />
        <button
          onClick={fetchKline}
          disabled={loading}
          style={{
            padding: '8px 20px',
            background: 'var(--color-gold)',
            color: '#000',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 14,
          }}
        >
          {loading ? '查询中...' : '查询'}
        </button>
      </div>

      {error && (
        <div style={{ padding: 16, background: 'rgba(239, 68, 68, 0.1)', borderRadius: 10, color: '#ef4444', marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
          <Loader2 size={32} className="animate-spin" style={{ color: 'var(--color-gold)' }} />
          <span style={{ marginLeft: 12, color: 'var(--color-dim)' }}>获取多周期K线...</span>
        </div>
      )}

      {!loading && data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
          {Object.entries(data).map(([periodKey, series]) => {
            const items = series.items || []
            if (items.length === 0) return null

            const last = items[items.length - 1]
            const first = items[0]
            const change = first.close > 0 ? ((last.close - first.close) / first.close * 100) : 0
            const isUp = change >= 0

            return (
              <div key={periodKey} style={{
                padding: 16,
                background: 'var(--color-card)',
                borderRadius: 12,
                border: '1px solid var(--color-border)',
              }}>
                {/* 周期标题 */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 12,
                }}>
                  <BarChart3 size={18} style={{ color: PERIOD_COLORS[periodKey] || 'var(--color-dim)' }} />
                  <span style={{ fontWeight: 700, fontSize: 15, color: PERIOD_COLORS[periodKey] }}>
                    {PERIOD_LABELS[periodKey] || periodKey}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-dim)' }}>
                    {series.count} 根
                  </span>
                </div>

                {/* 关键数据 */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: 8,
                  marginBottom: 12,
                  padding: 10,
                  background: 'rgba(0,0,0,0.2)',
                  borderRadius: 8,
                  fontSize: 13,
                }}>
                  <div>
                    <div style={{ color: 'var(--color-dim)', fontSize: 11 }}>最新价</div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{last.close.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--color-dim)', fontSize: 11 }}>区间涨跌</div>
                    <div style={{
                      fontWeight: 700,
                      fontSize: 15,
                      color: isUp ? '#ef4444' : '#22c55e',
                    }}>
                      {isUp ? '+' : ''}{change.toFixed(2)}%
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--color-dim)', fontSize: 11 }}>成交量</div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>
                      {(last.volume / 10000).toFixed(1)}万
                    </div>
                  </div>
                </div>

                {/* 迷你K线可视化（纯CSS） */}
                <div style={{
                  display: 'flex',
                  alignItems: 'end',
                  gap: 1,
                  height: 60,
                  padding: '4px 0',
                }}>
                  {items.slice(-40).map((item, i) => {
                    const allCloses = items.slice(-40).map(x => x.close)
                    const minC = Math.min(...allCloses)
                    const maxC = Math.max(...allCloses)
                    const range = maxC - minC || 1
                    const barH = Math.max(4, ((item.close - minC) / range) * 50)
                    const isGreen = item.close >= item.open
                    return (
                      <div
                        key={i}
                        title={`${item.timestamp}\n开: ${item.open.toFixed(2)} 收: ${item.close.toFixed(2)}`}
                        style={{
                          flex: 1,
                          height: barH,
                          background: isGreen ? '#22c55e' : '#ef4444',
                          borderRadius: 1,
                          opacity: 0.8,
                          minWidth: 2,
                        }}
                      />
                    )
                  })}
                </div>

                {/* 时间范围 */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 11,
                  color: 'var(--color-dim)',
                  marginTop: 6,
                }}>
                  <span>{items[0]?.timestamp?.slice(0, 10)}</span>
                  <span>{items[items.length - 1]?.timestamp?.slice(0, 10)}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 说明 */}
      <div style={{
        marginTop: 20,
        padding: '12px 16px',
        background: 'rgba(139, 92, 246, 0.08)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: 10,
        fontSize: 13,
        color: 'var(--color-dim)',
      }}>
        <span style={{ color: '#8b5cf6', fontWeight: 600 }}>📊 多周期分析：</span>
        日线看趋势方向，60分钟看波段节奏，15分钟看买卖点，1分钟看盘口微结构。多周期共振时信号最强。
      </div>
    </div>
  )
}


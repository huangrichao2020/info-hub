/**
 * 主升浪日K面板 — 基于 AmazingData daily-bars 接口
 * 展示量价共振信号和主升浪候选标的
 */
import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, ArrowUp, ArrowDown, Activity, Loader2 } from 'lucide-react'
import apiClient from '../../api/client'
import type { AmazingDataKlineItem } from '../../types'

interface StockConfig {
  code: string
  name: string
}

// 预设关注股票池（可后续改为从后端获取）
const WATCHLIST: StockConfig[] = [
  { code: '600519.SH', name: '贵州茅台' },
  { code: '000858.SZ', name: '五粮液' },
  { code: '601318.SH', name: '中国平安' },
  { code: '000001.SZ', name: '平安银行' },
  { code: '600036.SH', name: '招商银行' },
  { code: '300750.SZ', name: '宁德时代' },
]

function calcVolumeRatio(items: AmazingDataKlineItem[], idx: number): number {
  if (idx < 5) return 1
  const recent = items[idx]?.volume || 0
  const avg = items.slice(Math.max(0, idx - 5), idx).reduce((s, i) => s + i.volume, 0) / 5
  return avg > 0 ? recent / avg : 1
}

function isMainRisingWave(items: AmazingDataKlineItem[]): boolean {
  if (items.length < 10) return false
  const last5 = items.slice(-5)
  const prev5 = items.slice(-10, -5)
  const recentAvg = last5.reduce((s, i) => s + i.volume, 0) / 5
  const prevAvg = prev5.reduce((s, i) => s + i.volume, 0) / 5
  const priceUp = last5[4]?.close > prev5[0]?.close
  const volUp = recentAvg > prevAvg * 1.3
  return priceUp && volUp
}

export default function AmazingDataDailyBars() {
  const [loading, setLoading] = useState(true)
  const [results, setResults] = useState<Record<string, { stock: StockConfig; items: AmazingDataKlineItem[]; resonance: boolean }[]>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true)
      setError(null)
      const data: typeof results = {}

      for (const stock of WATCHLIST) {
        try {
          const resp = await apiClient.get('/amazingdata-market/amazingdata/daily-bars', {
            params: { code: stock.code, lookback_days: 30 },
          })
          const items: AmazingDataKlineItem[] = resp.data.items || []
          const resonance = isMainRisingWave(items)
          data[stock.code] = [{ stock, items, resonance }]
        } catch {
          data[stock.code] = [{ stock, items: [], resonance: false }]
        }
      }

      setResults(data)
      setLoading(false)
    }
    fetchAll()
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
        <Loader2 size={32} className="animate-spin" style={{ color: 'var(--color-gold)' }} />
        <span style={{ marginLeft: 12, color: 'var(--color-dim)' }}>正在获取 AmazingData 日K数据...</span>
      </div>
    )
  }

  if (error) {
    return <div style={{ color: 'var(--color-red)', padding: 20 }}>加载失败：{error}</div>
  }

  // 统计共振数量
  const resonanceCount = Object.values(results).flat().filter(r => r.resonance).length

  return (
    <div style={{ padding: '16px 24px' }}>
      {/* 顶部摘要卡 */}
      <div style={{
        background: 'linear-gradient(135deg, #1a3a2a 0%, #0d1f15 100%)',
        border: '1px solid #2d5a3d',
        borderRadius: 12,
        padding: '16px 20px',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
      }}>
        <Activity size={24} style={{ color: '#4ade80' }} />
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#4ade80' }}>
            主升浪信号：{resonanceCount} 只共振
          </div>
          <div style={{ fontSize: 13, color: 'var(--color-dim)', marginTop: 4 }}>
            基于 AmazingData 日K数据 · 量价共振筛选 · 放量+趋势向上
          </div>
        </div>
      </div>

      {/* 标的列表 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {Object.values(results).flat().map(({ stock, items, resonance }) => {
          if (items.length === 0) {
            return (
              <div key={stock.code} style={{
                padding: '12px 16px',
                background: 'var(--color-card)',
                borderRadius: 10,
                border: '1px solid var(--color-border)',
                opacity: 0.6,
              }}>
                <span style={{ fontWeight: 600 }}>{stock.name}</span>
                <span style={{ marginLeft: 8, color: 'var(--color-dim)', fontSize: 12 }}>({stock.code})</span>
                <span style={{ marginLeft: 12, color: 'var(--color-orange)' }}>无数据</span>
              </div>
            )
          }

          const last = items[items.length - 1]
          const prev = items.length > 1 ? items[items.length - 2] : last
          const change = prev.close > 0 ? ((last.close - prev.close) / prev.close * 100) : 0
          const volRatio = calcVolumeRatio(items, items.length - 1)
          const isUp = change >= 0

          return (
            <div key={stock.code} style={{
              padding: '14px 16px',
              background: resonance ? 'linear-gradient(90deg, #1a2a3a 0%, var(--color-card) 100%)' : 'var(--color-card)',
              borderRadius: 10,
              border: `1px solid ${resonance ? '#3b82f6' : 'var(--color-border)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {resonance ? (
                  <ArrowUp size={20} style={{ color: '#ef4444' }} />
                ) : (
                  <div style={{ width: 20 }} />
                )}
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{stock.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-dim)' }}>{stock.code}</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, color: 'var(--color-dim)' }}>最新收盘</div>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>{last.close.toFixed(2)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, color: 'var(--color-dim)' }}>涨跌幅</div>
                  <div style={{
                    fontWeight: 700, fontSize: 16,
                    color: isUp ? '#ef4444' : '#22c55e',
                  }}>
                    {isUp ? '+' : ''}{change.toFixed(2)}%
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, color: 'var(--color-dim)' }}>量比</div>
                  <div style={{
                    fontWeight: 700, fontSize: 16,
                    color: volRatio > 1.5 ? '#ef4444' : 'var(--color-text)',
                  }}>
                    {volRatio.toFixed(2)}
                  </div>
                </div>
                {resonance && (
                  <div style={{
                    padding: '4px 10px',
                    background: 'rgba(59, 130, 246, 0.2)',
                    borderRadius: 6,
                    fontSize: 12,
                    color: '#60a5fa',
                    fontWeight: 600,
                  }}>
                    量价共振
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* 底部操作提醒 */}
      <div style={{
        marginTop: 20,
        padding: '12px 16px',
        background: 'rgba(250, 204, 21, 0.08)',
        border: '1px solid rgba(250, 204, 21, 0.3)',
        borderRadius: 10,
        fontSize: 13,
        color: 'var(--color-dim)',
      }}>
        <span style={{ color: '#facc15', fontWeight: 600 }}>⚠️ 操作提醒：</span>
        共振标的优先关注，试仓 20%，确认后再加码。量价背离时减仓，破 MA25 止损。
      </div>
    </div>
  )
}


import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'

import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import type { ChanBar, ChanChartResponse, ChanSearchItem, ChanTradePoint, ChanStroke } from '../../types'

const MIN_CHART_W = 1180
const PRICE_H = 440
const VOLUME_H = 120
const PAD_X = 46
const PAD_TOP = 22
const PAD_BOTTOM = 24

function scaleX(index: number, total: number, width: number) {
  const usable = width - PAD_X * 2
  return PAD_X + (index / Math.max(1, total - 1)) * usable
}

function scaleY(value: number, min: number, max: number) {
  const usable = PRICE_H - PAD_TOP - PAD_BOTTOM
  if (max === min) return PRICE_H / 2
  return PAD_TOP + (max - value) / (max - min) * usable
}

function formatNumber(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '--'
  return value.toFixed(2)
}

/* Candle K线组件 - 增加可见度 */
function Candle({ bar, index, total, min, max, width, hovered, onHover }: {
  bar: ChanBar
  index: number
  total: number
  min: number
  max: number
  width: number
  hovered: boolean
  onHover: (idx: number | null) => void
}) {
  const x = scaleX(index, total, width)
  const openY = scaleY(bar.open, min, max)
  const closeY = scaleY(bar.close, min, max)
  const highY = scaleY(bar.high, min, max)
  const lowY = scaleY(bar.low, min, max)
  const up = bar.close >= bar.open
  const color = up ? '#ef4444' : '#22c55e'
  const bodyY = Math.min(openY, closeY)
  const bodyH = Math.max(2, Math.abs(closeY - openY))

  return (
    <g
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
      style={{ cursor: 'crosshair' }}
    >
      {/* 隐形热区 - 增加鼠标捕获区域 */}
      <rect x={x - 5} y={PAD_TOP} width={10} height={PRICE_H - PAD_TOP - PAD_BOTTOM} fill="transparent" />
      
      {/* K线 */}
      <line x1={x} x2={x} y1={highY} y2={lowY} stroke={color} strokeWidth={hovered ? 2 : 1.5} />
      <rect
        x={x - 4}
        y={bodyY}
        width={8}
        height={bodyH}
        rx="1"
        fill={up ? 'rgba(239,68,68,.25)' : 'rgba(34,197,94,.25)'}
        stroke={color}
        strokeWidth={hovered ? 2 : 1.2}
      />
      
      {/* hover高亮 */}
      {hovered && (
        <line x1={x} x2={x} y1={PAD_TOP} y2={PRICE_H - PAD_BOTTOM} stroke="rgba(255,255,255,.15)" strokeWidth={1} strokeDasharray="3 3" />
      )}
    </g>
  )
}

function volumeColor(bar: ChanBar) {
  return bar.close >= bar.open ? 'rgba(239,68,68,.45)' : 'rgba(34,197,94,.45)'
}

export default function ChanChartPanel() {
  const [code, setCode] = useState('000001.SH')
  const [draft, setDraft] = useState('上证指数')
  const [matches, setMatches] = useState<ChanSearchItem[]>([])
  const [data, setData] = useState<ChanChartResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  useEffect(() => {
    const keyword = draft.trim()
    if (!keyword) {
      setMatches([])
      return
    }
    const timeout = window.setTimeout(() => {
      client.get<{ items: ChanSearchItem[] }>('/chan/search', { params: { query: keyword, limit: 6 } })
        .then((response) => setMatches(response.data.items || []))
        .catch(() => setMatches([]))
    }, 180)
    return () => window.clearTimeout(timeout)
  }, [draft])

  useEffect(() => {
    setLoading(true)
    client.get<ChanChartResponse>('/chan/daily', { params: { code, limit: 220 } })
      .then((response) => setData(response.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [code])

  const bars = data?.bars || []
  const chartWidth = useMemo(() => Math.max(MIN_CHART_W, bars.length * 9.5 + PAD_X * 2), [bars.length])
  const priceMin = useMemo(() => bars.length ? Math.min(...bars.map((bar) => bar.low)) * 0.98 : 0, [bars])
  const priceMax = useMemo(() => bars.length ? Math.max(...bars.map((bar) => bar.high)) * 1.02 : 1, [bars])
  const volumeMax = useMemo(() => bars.length ? Math.max(...bars.map((bar) => bar.volume)) : 1, [bars])
  const latest = bars[bars.length - 1]
  const hoveredBar = hoveredIdx != null ? bars[hoveredIdx] : null

  if (loading) return <LoadingSkeleton count={5} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* Header section */}
      <section style={{ borderRadius: 20, padding: 18, background: 'linear-gradient(145deg, rgba(167,139,250,.16), rgba(15,23,42,.96) 55%)', border: '1px solid rgba(167,139,250,.18)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '.82em', color: 'var(--color-purple)', fontWeight: 700 }}>日K缠论图</div>
            <h3 style={{ marginTop: 8, fontSize: '1.52rem', letterSpacing: '-0.04em' }}>{data?.code || code}</h3>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="输入 上证指数 / 贵州茅台 / 电子城"
              style={{
                width: 220,
                padding: '10px 12px',
                borderRadius: 12,
                border: '1px solid rgba(148,163,184,.18)',
                background: 'rgba(15,23,42,.42)',
                color: 'var(--color-text)',
              }}
            />
            <button
              onClick={() => {
                const selected = matches[0]
                setCode(selected?.code || draft)
                if (selected?.name) setDraft(selected.name)
              }}
              style={{
                padding: '10px 14px',
                borderRadius: 12,
                border: '1px solid rgba(167,139,250,.24)',
                background: 'rgba(167,139,250,.12)',
                color: 'var(--color-purple)',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              查看日线
            </button>
          </div>
        </div>
        {matches.length > 0 && (
          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {matches.map((item) => (
              <button
                key={item.code}
                onClick={() => {
                  setDraft(item.name)
                  setCode(item.code)
                }}
                style={{
                  padding: '6px 10px',
                  borderRadius: 999,
                  border: '1px solid rgba(148,163,184,.14)',
                  background: 'rgba(15,23,42,.42)',
                  color: 'var(--color-text)',
                  cursor: 'pointer',
                  fontSize: '.76em',
                }}
              >
                {item.name} · {item.code}
              </button>
            ))}
          </div>
        )}

        {latest && (
          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: 10 }}>
            <Metric title="日期" value={latest.date} accent="var(--color-text)" />
            <Metric title="开盘" value={formatNumber(latest.open)} accent="var(--color-text)" />
            <Metric title="最高" value={formatNumber(latest.high)} accent="var(--color-red)" />
            <Metric title="最低" value={formatNumber(latest.low)} accent="var(--color-green)" />
            <Metric title="收盘" value={formatNumber(latest.close)} accent="var(--color-accent)" />
            <Metric title="成交量" value={`${(latest.volume / 1e8).toFixed(2)}亿`} accent="var(--color-gold)" />
          </div>
        )}
      </section>

      {data ? (
        <section style={{ borderRadius: 20, padding: 18, background: 'rgba(15,23,42,.62)', border: '1px solid rgba(148,163,184,.12)' }}>
          <div style={{ marginBottom: 10, fontSize: '.76em', color: 'var(--color-dim)' }}>
            左右滚动查看更长历史，鼠标悬停K线查看当日数据。
          </div>
          <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
          <svg viewBox={`0 0 ${chartWidth} ${PRICE_H + VOLUME_H + 40}`} style={{ width: chartWidth, height: 'auto', display: 'block', minWidth: '100%' }}>
            {/* Grid lines */}
            {[0.2, 0.4, 0.6, 0.8].map((ratio) => {
              const y = PAD_TOP + (PRICE_H - PAD_TOP - PAD_BOTTOM) * ratio
              return <line key={ratio} x1={PAD_X} x2={chartWidth - PAD_X} y1={y} y2={y} stroke="rgba(148,163,184,.12)" strokeDasharray="4 4" />
            })}

            {/* Candles */}
            {bars.map((bar, index) => (
              <Candle
                key={bar.date}
                bar={bar}
                index={index}
                total={bars.length}
                min={priceMin}
                max={priceMax}
                width={chartWidth}
                hovered={hoveredIdx === index}
                onHover={setHoveredIdx}
              />
            ))}

            {/* Volume bars */}
            {bars.map((bar, index) => {
              const x = scaleX(index, bars.length, chartWidth)
              const height = (bar.volume / Math.max(1, volumeMax)) * (VOLUME_H - 20)
              return (
                <motion.rect
                  key={`${bar.date}-vol`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: Math.min(index * 0.004, 0.35), duration: 0.16 }}
                  x={x - 2.5}
                  y={PRICE_H + 20 + (VOLUME_H - 20 - height)}
                  width={5}
                  height={height}
                  fill={volumeColor(bar)}
                />
              )
            })}

            {/* Strokes (笔) */}
            {data.strokes.map((stroke: ChanStroke, index) => (
              <motion.line
                key={`stroke-${index}`}
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ delay: 0.2 + index * 0.05, duration: 0.35 }}
                x1={scaleX(stroke.start_index, bars.length, chartWidth)}
                y1={scaleY(stroke.start_price, priceMin, priceMax)}
                x2={scaleX(stroke.end_index, bars.length, chartWidth)}
                y2={scaleY(stroke.end_price, priceMin, priceMax)}
                stroke="#a78bfa"
                strokeWidth="2.5"
              />
            ))}

            {/* Trade points (买卖点) */}
            {data.trade_points.map((point: ChanTradePoint, index) => {
              const barAtPoint = bars[point.index]
              // 买点放最低价下方，卖点放最高价上方
              const isSell = point.type.includes('卖')
              const priceForLabel = barAtPoint
                ? (isSell ? barAtPoint.high * 1.03 : barAtPoint.low * 0.97)
                : point.price
              return (
              <motion.g
                key={`point-${index}`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.55 + index * 0.05, duration: 0.2 }}
              >
                <motion.circle
                  animate={{ r: [4, 5.5, 4] }}
                  transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 1.2 }}
                  cx={scaleX(point.index, bars.length, chartWidth)}
                  cy={scaleY(point.price, priceMin, priceMax)}
                  r="4"
                  fill={point.type.includes('买') ? '#ef4444' : '#14b8a6'}
                />
                <text
                  x={scaleX(point.index, bars.length, chartWidth)}
                  y={scaleY(priceForLabel, priceMin, priceMax)}
                  textAnchor="middle"
                  fontSize="13"
                  fill={point.type.includes('买') ? '#ef4444' : '#14b8a6'}
                  fontWeight="700"
                >
                  {point.type}
                </text>
              </motion.g>
              )
            })}

            {/* Tooltip */}
            {hoveredBar && hoveredIdx != null && (
              <g>
                {(() => {
                  const x = scaleX(hoveredIdx, bars.length, chartWidth)
                  const isUp = hoveredBar.close >= hoveredBar.open
                  const tooltipW = 180
                  const tooltipH = 130
                  const tooltipX = x + tooltipW > chartWidth - PAD_X ? x - tooltipW - 10 : x + 10
                  const tooltipY = PAD_TOP + 10

                  return (
                    <>
                      {/* Tooltip background */}
                      <rect
                        x={tooltipX}
                        y={tooltipY}
                        width={tooltipW}
                        height={tooltipH}
                        rx="8"
                        fill="rgba(15,23,42,.92)"
                        stroke="rgba(148,163,184,.2)"
                        strokeWidth="1"
                      />
                      {/* Date */}
                      <text x={tooltipX + 10} y={tooltipY + 20} fontSize="12" fill="var(--color-text-secondary)" fontWeight="600">
                        {hoveredBar.date}
                      </text>
                      {/* OHLC */}
                      <text x={tooltipX + 10} y={tooltipY + 42} fontSize="11" fill="var(--color-text)">
                        开: {formatNumber(hoveredBar.open)}
                      </text>
                      <text x={tooltipX + 10} y={tooltipY + 58} fontSize="11" fill={isUp ? '#ef4444' : '#22c55e'}>
                        收: {formatNumber(hoveredBar.close)}
                      </text>
                      <text x={tooltipX + 10} y={tooltipY + 74} fontSize="11" fill="#ef4444">
                        高: {formatNumber(hoveredBar.high)}
                      </text>
                      <text x={tooltipX + 10} y={tooltipY + 90} fontSize="11" fill="#22c55e">
                        低: {formatNumber(hoveredBar.low)}
                      </text>
                      <text x={tooltipX + 10} y={tooltipY + 106} fontSize="11" fill="var(--color-gold)">
                        量: {(hoveredBar.volume / 1e4).toFixed(0)}万
                      </text>
                      {/* Change */}
                      <text x={tooltipX + 10} y={tooltipY + 122} fontSize="11" fill={isUp ? '#ef4444' : '#22c55e'} fontWeight="600">
                        涨跌: {isUp ? '+' : ''}{((hoveredBar.close - hoveredBar.open) / hoveredBar.open * 100).toFixed(2)}%
                      </text>
                    </>
                  )
                })()}
              </g>
            )}
          </svg>
          </div>
        </section>
      ) : (
        <div style={{ padding: 26, borderRadius: 16, border: '1px dashed rgba(148,163,184,.18)', color: 'var(--color-dim)' }}>
          暂无缠论图数据。
        </div>
      )}
    </div>
  )
}

function Metric({ title, value, accent }: { title: string; value: string; accent: string }) {
  return (
    <div style={{ borderRadius: 14, padding: '12px 14px', background: 'rgba(15,23,42,.42)', border: '1px solid rgba(148,163,184,.12)' }}>
      <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: '1.02em', fontWeight: 800, color: accent }}>{value}</div>
    </div>
  )
}

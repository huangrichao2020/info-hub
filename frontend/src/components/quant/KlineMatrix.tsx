import type { QuantKlineMultiSeries, QuantKlineSeries, TurnStrongStock } from '../../types'

function formatPrice(value?: number | null) {
  if (value == null || Number.isNaN(value)) {
    return '--'
  }
  return value.toFixed(2)
}

function formatPercent(value?: number | null) {
  if (value == null || Number.isNaN(value)) {
    return '--'
  }
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function summarizeSeries(series?: QuantKlineSeries) {
  const items = series?.items || []
  if (items.length === 0) {
    return { lastClose: null, firstOpen: null, changePct: null, high: null, low: null }
  }
  const first = items[0]
  const last = items[items.length - 1]
  const firstOpen = first.open ?? first.close ?? null
  const lastClose = last.close ?? null
  const highs = items.map((item) => item.high ?? item.close ?? 0)
  const lows = items.map((item) => item.low ?? item.close ?? 0)
  const high = highs.length ? Math.max(...highs) : null
  const low = lows.length ? Math.min(...lows) : null
  const changePct = firstOpen && lastClose != null ? (lastClose - firstOpen) / firstOpen * 100 : null
  return { lastClose, firstOpen, changePct, high, low }
}

function buildCandles(series?: QuantKlineSeries) {
  const items = series?.items || []
  if (items.length === 0) {
    return { candles: [], min: 0, max: 0 }
  }
  const sliced = items.slice(-48)
  const highs = sliced.map((item) => item.high ?? item.close ?? 0)
  const lows = sliced.map((item) => item.low ?? item.close ?? 0)
  const max = Math.max(...highs)
  const min = Math.min(...lows)
  return { candles: sliced, min, max }
}

function scaleY(value: number, min: number, max: number, height: number) {
  if (max === min) {
    return height / 2
  }
  const padding = 12
  return padding + (max - value) / (max - min) * (height - padding * 2)
}

function KlineChart({ title, series }: { title: string; series?: QuantKlineSeries }) {
  const { candles, min, max } = buildCandles(series)
  const summary = summarizeSeries(series)
  const width = 320
  const height = 180
  const candleWidth = candles.length > 0 ? Math.max(3, Math.floor((width - 24) / candles.length) - 1) : 4

  return (
    <div
      style={{
        background: 'var(--color-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 16,
        padding: 14,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
        <div>
          <div style={{ fontSize: '.8em', color: 'var(--color-dim)' }}>{title}</div>
          <div style={{ marginTop: 4, fontSize: '1em', fontWeight: 700 }}>{formatPrice(summary.lastClose)}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>区间涨跌</div>
          <div style={{ marginTop: 4, fontSize: '.84em', fontWeight: 700, color: (summary.changePct ?? 0) >= 0 ? 'var(--color-red)' : 'var(--color-green)' }}>
            {formatPercent(summary.changePct)}
          </div>
        </div>
      </div>

      {candles.length === 0 ? (
        <div style={{ height: 180, display: 'grid', placeItems: 'center', color: 'var(--color-dim)', fontSize: '.82em' }}>
          暂无走势数据
        </div>
      ) : (
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 180, display: 'block' }}>
          <line x1="0" x2={width} y1="20" y2="20" stroke="rgba(148,163,184,.12)" />
          <line x1="0" x2={width} y1={height / 2} y2={height / 2} stroke="rgba(148,163,184,.12)" />
          <line x1="0" x2={width} y1={height - 20} y2={height - 20} stroke="rgba(148,163,184,.12)" />
          {candles.map((item, index) => {
            const x = 12 + index * ((width - 24) / candles.length)
            const open = item.open ?? item.close ?? 0
            const close = item.close ?? open
            const high = item.high ?? Math.max(open, close)
            const low = item.low ?? Math.min(open, close)
            const openY = scaleY(open, min, max, height)
            const closeY = scaleY(close, min, max, height)
            const highY = scaleY(high, min, max, height)
            const lowY = scaleY(low, min, max, height)
            const rising = close >= open
            const color = rising ? '#ef4444' : '#22c55e'
            const bodyY = Math.min(openY, closeY)
            const bodyHeight = Math.max(2, Math.abs(closeY - openY))
            return (
              <g key={`${item.timestamp}-${index}`}>
                <line x1={x} x2={x} y1={highY} y2={lowY} stroke={color} strokeWidth="1.2" />
                <rect
                  x={x - candleWidth / 2}
                  y={bodyY}
                  width={candleWidth}
                  height={bodyHeight}
                  rx="1.5"
                  fill={rising ? 'rgba(239,68,68,.2)' : 'rgba(34,197,94,.2)'}
                  stroke={color}
                  strokeWidth="1"
                />
              </g>
            )
          })}
        </svg>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
        <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>最高：<span style={{ color: 'var(--color-text)' }}>{formatPrice(summary.high)}</span></div>
        <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>最低：<span style={{ color: 'var(--color-text)' }}>{formatPrice(summary.low)}</span></div>
        <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>K 线数：<span style={{ color: 'var(--color-text)' }}>{series?.count ?? 0}</span></div>
      </div>
    </div>
  )
}

export default function KlineMatrix({
  stock,
  data,
  loading,
  error,
}: {
  stock?: TurnStrongStock | null
  data?: QuantKlineMultiSeries | null
  loading: boolean
  error: string
}) {
  if (!stock) {
    return null
  }

  return (
    <section
      style={{
        background: 'linear-gradient(160deg, rgba(56,189,248,.08), rgba(17,24,39,.96) 40%, var(--color-card))',
        border: '1px solid rgba(56,189,248,.18)',
        borderRadius: 18,
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '.78em', color: 'var(--color-accent)', fontWeight: 700 }}>量价走势面板</div>
          <h3 style={{ marginTop: 6, fontSize: '1.24em' }}>{stock.name} {stock.code}</h3>
          <div style={{ marginTop: 6, color: 'var(--color-dim)', fontSize: '.8em' }}>
            点击下方卡片可切换个股；这里展示小时、日 K 走势。
          </div>
        </div>
        <div style={{ fontSize: '.8em', color: 'var(--color-dim)' }}>
          交易日：{data?.trade_date || '--'}
        </div>
      </div>

      {loading && (
        <div style={{ padding: 24, borderRadius: 14, border: '1px dashed rgba(148,163,184,.18)', color: 'var(--color-dim)', textAlign: 'center' }}>
          正在拉取多周期走势...
        </div>
      )}

      {error && !loading && (
        <div style={{ padding: 14, borderRadius: 14, border: '1px solid rgba(239,68,68,.22)', background: 'rgba(127,29,29,.18)', color: '#fecaca', fontSize: '.84em' }}>
          {error}
        </div>
      )}

      {!loading && !error && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
          <KlineChart title="小时走势" series={data?.series?.hour} />
          <KlineChart title="日 K 走势" series={data?.series?.day} />
        </div>
      )}
    </section>
  )
}

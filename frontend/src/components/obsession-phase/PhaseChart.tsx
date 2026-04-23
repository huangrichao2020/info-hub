import { useRef, useEffect } from 'react'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

interface PhaseDataPoint {
  timestamp: string
  signal_count: number
  phase: string
}

interface PhaseChartProps {
  history: PhaseDataPoint[]
}

const PHASE_COLORS: Record<string, string> = {
  emptiness: '#64748b',
  subtle_use: '#60a5fa',
  obsession_form: '#38bdf8',
  obsession_strong: '#fbbf24',
  obsession_break: '#ef4444',
}

const PHASE_LABELS: Record<string, string> = {
  emptiness: '空性',
  subtle_use: '妙用',
  obsession_form: '执念形成',
  obsession_strong: '住相强化',
  obsession_break: '住相破裂',
}

export default function PhaseChart({ history }: PhaseChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<Chart | null>(null)

  useEffect(() => {
    if (!canvasRef.current || history.length === 0) return

    const ctx = canvasRef.current.getContext('2d')
    if (!ctx) return

    if (chartRef.current) {
      chartRef.current.destroy()
    }

    const sorted = [...history].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )

    const labels = sorted.map((h) => {
      const d = new Date(h.timestamp)
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
    })

    const bgColors = sorted.map((h) => {
      const base = PHASE_COLORS[h.phase] || '#64748b'
      return base + '44'
    })

    const borderColors = sorted.map((h) => PHASE_COLORS[h.phase] || '#64748b')

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '信号数',
            data: sorted.map((h) => h.signal_count),
            borderColor: '#fbbf24',
            backgroundColor: 'rgba(251,191,36,0.1)',
            borderWidth: 2,
            pointBackgroundColor: borderColors,
            pointBorderColor: borderColors,
            pointRadius: 5,
            pointHoverRadius: 7,
            fill: true,
            tension: 0.3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e293b',
            titleColor: '#f1f5f9',
            bodyColor: '#94a3b8',
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => {
                const h = sorted[ctx.dataIndex]
                return `信号: ${h.signal_count}/5 | 阶段: ${PHASE_LABELS[h.phase] || h.phase}`
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(51,65,85,0.3)' },
            ticks: { color: '#64748b', font: { size: 11 }, maxTicksLimit: 8 },
          },
          y: {
            min: 0,
            max: 5,
            ticks: {
              stepSize: 1,
              color: '#64748b',
              font: { size: 11 },
              callback: (v) => `${v}/5`,
            },
            grid: { color: 'rgba(51,65,85,0.3)' },
          },
        },
      },
    })

    return () => {
      chartRef.current?.destroy()
    }
  }, [history])

  if (history.length === 0) {
    return (
      <div
        style={{
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--color-text-tertiary)',
          fontSize: 13,
        }}
      >
        暂无历史数据
      </div>
    )
  }

  return (
    <div style={{ position: 'relative', height: 220 }}>
      <canvas ref={canvasRef} />
    </div>
  )
}

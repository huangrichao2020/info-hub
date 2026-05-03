import { AlertTriangle, RefreshCw, History, BarChart3, Target, X } from 'lucide-react'
import { useState } from 'react'

import { useApiFetch } from '../../hooks/useApi'
import LoadingSkeleton from '../common/LoadingSkeleton'
import SignalChain from './SignalChain'
import PhaseGauge from './PhaseGauge'
import PhaseChart from './PhaseChart'
import { useAppStore } from '../../stores/appStore'
import type { ObsessionPhaseStatus, ObsessionSignal } from '../../types'

const SIGNAL_ACTION_MAP: Record<number, { level: string; color: string; advice: string }> = {
  0: { level: '安全', color: 'var(--color-green)', advice: '执念未形成或处于早期，继续观察，不急于出手' },
  1: { level: '关注', color: 'var(--color-blue)', advice: '出现首个信号，开始盯盘，注意龙头承接质量' },
  2: { level: '警戒', color: 'var(--color-gold)', advice: '2个信号出现，考虑减仓，降低敞口' },
  3: { level: '减仓', color: 'var(--color-orange)', advice: '3个信号，住相开始松动，必须减仓' },
  4: { level: '危险', color: 'var(--color-red)', advice: '4个信号，住相破裂前夜，清仓准备' },
  5: { level: '破裂', color: 'var(--color-red)', advice: '5个信号全亮，住相已破，远离该板块' },
}

type ViewMode = 'dashboard' | 'history' | 'backtest'

interface HistoryRecord {
  recorded_at: string
  current_phase: string
  phase_label: string
  signal_count: number
  signals_json: string
}

interface BacktestResult {
  days_analyzed: number
  total_records: number
  signal_frequency: Record<string, number>
  signal_frequency_pct: Record<string, number>
  phase_distribution: Record<string, number>
  phase_distribution_pct: Record<string, number>
  avg_signal_count: number
  max_signal_count: number
  break_phase_ratio_pct: string
}

export default function ObsessionPhasePanel() {
  const refreshKey = useAppStore((state) => state.refreshKey)
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard')
  const [historyDays, setHistoryDays] = useState(7)
  const [backtestDays, setBacktestDays] = useState(30)
  const [manualSignal, setManualSignal] = useState<string | null>(null)

  const { data, loading, error, refetch } = useApiFetch<ObsessionPhaseStatus>('/obsession-phase/status', {
    deps: [refreshKey],
  })

  const { data: historyData, loading: historyLoading } = useApiFetch<HistoryRecord[]>(
    `/obsession-phase/history?days=${historyDays}`,
    { deps: [historyDays, refreshKey], immediate: viewMode === 'history' },
  )

  const { data: backtestData, loading: backtestLoading } = useApiFetch<BacktestResult>(
    `/obsession-phase/backtest?days=${backtestDays}`,
    { deps: [backtestDays, refreshKey], immediate: viewMode === 'backtest' },
  )

  const handleMarkSignal = async (signalName: string, triggered: boolean) => {
    try {
      const formData = new URLSearchParams()
      formData.append('signal_name', signalName)
      formData.append('triggered', String(triggered))
      await fetch(`/info-hub/api/obsession-phase/mark?${formData.toString()}`, { method: 'POST' })
      refetch()
    } catch {
      // ignore
    }
  }

  const handleResetSignals = async () => {
    try {
      await fetch('/info-hub/api/obsession-phase/reset', { method: 'POST' })
      refetch()
    } catch {
      // ignore
    }
  }

  if (loading) return <LoadingSkeleton count={4} />
  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-secondary)' }}>
        <AlertTriangle size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
        <p>{error}</p>
        <button onClick={() => refetch()} style={{ marginTop: 12, padding: '8px 20px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', cursor: 'pointer' }}>重试</button>
      </div>
    )
  }

  const signals = data?.signals ?? []
  const signalCount = data?.signal_count ?? 0
  const actionInfo = SIGNAL_ACTION_MAP[signalCount] ?? SIGNAL_ACTION_MAP[0]

  // 导航标签
  const tabs: { key: ViewMode; label: string; icon: typeof Target }[] = [
    { key: 'dashboard', label: '实时监控', icon: Target },
    { key: 'history', label: '历史记录', icon: History },
    { key: 'backtest', label: '回测分析', icon: BarChart3 },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* 顶部：标题 + 视图切换 + 刷新 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--color-text)' }}>住相信号链</h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-tertiary)', marginTop: 4 }}>执念 → 住相 → 破裂，用信号判断买卖时机</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {tabs.map((tab) => {
            const Icon = tab.icon
            const active = viewMode === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setViewMode(tab.key)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '8px 14px', borderRadius: 8,
                  border: active ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                  background: active ? 'var(--color-accent-dim)' : 'var(--color-surface)',
                  color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                  cursor: 'pointer', fontSize: 13, fontWeight: active ? 600 : 400,
                  transition: 'all 0.2s',
                }}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            )
          })}
          <button onClick={() => refetch()} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text-secondary)', cursor: 'pointer', fontSize: 13 }}>
            <RefreshCw size={14} /> 刷新
          </button>
        </div>
      </div>

      {/* ── 仪表盘视图 ── */}
      {viewMode === 'dashboard' && (
        <>
          {/* 阶段仪表盘 */}
          <div style={{ padding: 20, borderRadius: 16, background: 'var(--color-card)', border: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-secondary)' }}>当前阶段</h3>
              <button onClick={handleResetSignals} style={{ fontSize: 12, color: 'var(--color-text-tertiary)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px', borderRadius: 4 }} onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-text)' }} onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-text-tertiary)' }}>重置信号</button>
            </div>
            <PhaseGauge current_phase={data?.current_phase ?? 'obsession_strong'} phase_label={data?.phase_label ?? '住相强化'} phase_description={data?.phase_description} />
          </div>

          {/* 信号链 SVG */}
          <div style={{ padding: 20, borderRadius: 16, background: 'var(--color-card)', border: '1px solid var(--color-border)' }}>
            <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-secondary)', marginBottom: 14 }}>破裂信号链（点击节点手动标记）</h3>
            <SignalChain signals={signals} onToggle={handleMarkSignal} />
            <div style={{ textAlign: 'center', marginTop: 8, fontSize: 12, color: 'var(--color-text-tertiary)' }}>
              已触发 {signalCount} / 5
            </div>
          </div>

          {/* 操作建议 */}
          <div style={{ padding: 20, borderRadius: 16, background: 'var(--color-card)', border: `1px solid ${actionInfo.color}44`, borderLeft: `4px solid ${actionInfo.color}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <span style={{ padding: '3px 10px', borderRadius: 6, background: `${actionInfo.color}22`, color: actionInfo.color, fontSize: 13, fontWeight: 600 }}>
                {actionInfo.level} · {signalCount}/5 信号
              </span>
            </div>
            <p style={{ fontSize: 14, color: 'var(--color-text)', lineHeight: 1.7 }}>{data?.action_suggestion ?? actionInfo.advice}</p>
            {data?.last_updated && <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 10 }}>最后更新: {data.last_updated}</p>}
          </div>

          {/* 铁律提醒 */}
          <div style={{ padding: 16, borderRadius: 12, background: 'var(--color-surface-elevated)', border: '1px solid var(--color-border)' }}>
            <h4 style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-gold)', marginBottom: 8 }}>💡 铁律提醒</h4>
            <ul style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.8, paddingLeft: 18 }}>
              <li>住相破裂前夜的卖出，比破裂当天的卖出更值钱</li>
              <li>看到 2-3 个信号 → 减仓，看到 4-5 个信号 → 清仓</li>
              <li>龙头尾盘回封往往是诱多，不要当成住相未破</li>
              <li>买的是执念形成，卖的是住相破裂前夜</li>
            </ul>
          </div>
        </>
      )}

      {/* ── 历史记录视图 ── */}
      {viewMode === 'history' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>查看</span>
            <select value={historyDays} onChange={(e) => setHistoryDays(Number(e.target.value))} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: 13 }}>
              {[3, 7, 14, 30].map((d) => <option key={d} value={d}>{d} 天</option>)}
            </select>
            <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>的记录</span>
          </div>

          {historyLoading ? <LoadingSkeleton count={4} /> : (
            <>
              <PhaseChart history={(historyData ?? []).map((h) => ({ timestamp: h.recorded_at, signal_count: h.signal_count, phase: h.current_phase }))} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(historyData ?? []).slice(0, 20).map((record, i) => {
                  const phaseColors: Record<string, string> = { emptiness: '#64748b', subtle_use: '#60a5fa', obsession_form: '#38bdf8', obsession_strong: '#fbbf24', obsession_break: '#ef4444' }
                  const color = phaseColors[record.current_phase] || '#64748b'
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--color-surface-elevated)', border: '1px solid var(--color-border)' }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)', minWidth: 80 }}>{record.phase_label}</span>
                      <span style={{ fontSize: 13, color: color, fontWeight: 600, minWidth: 50 }}>{record.signal_count}/5</span>
                      <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)', flex: 1 }}>{record.recorded_at}</span>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── 回测分析视图 ── */}
      {viewMode === 'backtest' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>回测周期</span>
            <select value={backtestDays} onChange={(e) => setBacktestDays(Number(e.target.value))} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text)', fontSize: 13 }}>
              {[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{d} 天</option>)}
            </select>
          </div>

          {backtestLoading ? <LoadingSkeleton count={4} /> : backtestData && backtestData.total_records > 0 ? (
            <>
              {/* 核心指标 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
                {[
                  { label: '总记录数', value: backtestData.total_records, color: 'var(--color-accent)' },
                  { label: '平均信号数', value: backtestData.avg_signal_count, color: 'var(--color-gold)' },
                  { label: '最高信号数', value: backtestData.max_signal_count, color: 'var(--color-red)' },
                  { label: '破裂阶段占比', value: backtestData.break_phase_ratio_pct, color: 'var(--color-orange)' },
                ].map((m) => (
                  <div key={m.label} style={{ padding: 16, borderRadius: 12, background: 'var(--color-surface-elevated)', border: '1px solid var(--color-border)', textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 600, color: m.color }}>{m.value}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 4 }}>{m.label}</div>
                  </div>
                ))}
              </div>

              {/* 信号频率 */}
              <div style={{ padding: 20, borderRadius: 16, background: 'var(--color-card)', border: '1px solid var(--color-border)' }}>
                <h4 style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-secondary)', marginBottom: 14 }}>信号触发频率</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {Object.entries(backtestData.signal_frequency_pct).map(([name, pct]) => {
                    const sigDef = signals.find((s) => s.name === name)
                    const barColor = pct > 30 ? 'var(--color-red)' : pct > 15 ? 'var(--color-orange)' : 'var(--color-gold)'
                    return (
                      <div key={name}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontSize: 13, color: 'var(--color-text)' }}>{sigDef?.label || name}</span>
                          <span style={{ fontSize: 13, color: barColor, fontWeight: 600 }}>{pct}%</span>
                        </div>
                        <div style={{ height: 6, borderRadius: 3, background: 'var(--color-surface-elevated)', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${Math.min(pct, 100)}%`, background: barColor, borderRadius: 3, transition: 'width 0.5s' }} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* 阶段分布 */}
              <div style={{ padding: 20, borderRadius: 16, background: 'var(--color-card)', border: '1px solid var(--color-border)' }}>
                <h4 style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-secondary)', marginBottom: 14 }}>阶段分布</h4>
                <div style={{ display: 'flex', borderRadius: 8, overflow: 'hidden', height: 32 }}>
                  {Object.entries(backtestData.phase_distribution_pct).map(([phase, pct]) => {
                    const phaseLabels: Record<string, string> = { emptiness: '空性', subtle_use: '妙用', obsession_form: '执念', obsession_strong: '住相', obsession_break: '破裂' }
                    const phaseColors: Record<string, string> = { emptiness: '#64748b', subtle_use: '#60a5fa', obsession_form: '#38bdf8', obsession_strong: '#fbbf24', obsession_break: '#ef4444' }
                    return (
                      <div key={phase} style={{ flex: pct, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#fff', background: phaseColors[phase] || '#64748b', fontWeight: 500 }}>
                        {phaseLabels[phase] || phase} {pct}%
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-tertiary)' }}>
              <BarChart3 size={32} style={{ marginBottom: 12, opacity: 0.3 }} />
              <p style={{ fontSize: 14 }}>暂无回测数据，请等待定时任务采集</p>
              <p style={{ fontSize: 12, marginTop: 8 }}>系统每 30 分钟自动记录一次信号状态</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


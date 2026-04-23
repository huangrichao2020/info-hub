import type { ObsessionSignal } from '../../types'

const PHASES = [
  { key: 'emptiness', label: '空性', color: 'var(--color-text-tertiary)', desc: '事件无固定意义，随阶段而变' },
  { key: 'subtle_use', label: '妙用', color: 'var(--color-blue)', desc: '同一事件对不同资金作用不同' },
  { key: 'obsession_form', label: '执念形成', color: 'var(--color-accent)', desc: '人群开始相信叙事' },
  { key: 'obsession_strong', label: '住相强化', color: 'var(--color-gold)', desc: '把阶段性有效当成永恒' },
  { key: 'obsession_break', label: '住相破裂', color: 'var(--color-red)', desc: '叙事崩塌，资金撤离' },
]

interface PhaseGaugeProps {
  current_phase: string
  phase_label: string
  phase_description?: string
}

export default function PhaseGauge({ current_phase, phase_label, phase_description }: PhaseGaugeProps) {
  const currentIndex = PHASES.findIndex((p) => p.key === current_phase)
  const activeIndex = currentIndex >= 0 ? currentIndex : 2

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 色带进度条 */}
      <div style={{ display: 'flex', borderRadius: 8, overflow: 'hidden', height: 32 }}>
        {PHASES.map((phase, i) => {
          const isActive = i === activeIndex
          const isPast = i < activeIndex
          return (
            <div
              key={phase.key}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#fff' : isPast ? 'var(--color-text-tertiary)' : 'var(--color-text-tertiary)',
                background: isActive
                  ? phase.color
                  : isPast
                    ? `${phase.color}33`
                    : 'var(--color-surface-elevated)',
                borderRight: i < PHASES.length - 1 ? '1px solid var(--color-bg)' : 'none',
                transition: 'all 0.3s ease',
                cursor: 'default',
              }}
              title={phase.desc}
            >
              {phase.label}
            </div>
          )
        })}
      </div>

      {/* 当前阶段说明 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 14px',
          borderRadius: 10,
          background: 'var(--color-surface-elevated)',
          border: '1px solid var(--color-border)',
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: PHASES[activeIndex].color,
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: 14, fontWeight: 500, color: PHASES[activeIndex].color }}>
          {phase_label}
        </span>
        <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
          {phase_description || PHASES[activeIndex].desc}
        </span>
      </div>
    </div>
  )
}

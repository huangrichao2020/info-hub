/* ============================================
   Metric - 指标卡片
   用于展示关键数据指标（来自 ChanChartPanel / ConceptBoardPanel 去重）
   ============================================ */

interface MetricProps {
  title: string
  value: string
  accent?: string
  variant?: 'default' | 'compact' | 'premium'
}

export default function Metric({ title, value, accent = 'var(--color-accent)', variant = 'default' }: MetricProps) {
  const styles = {
    default: {
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 14,
      padding: '12px 14px',
    },
    compact: {
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 10,
      padding: '8px 10px',
    },
    premium: {
      background: 'rgba(15,23,42,.42)',
      border: '1px solid rgba(148,163,184,.12)',
      borderRadius: 14,
      padding: '12px 14px',
    },
  }

  return (
    <div style={styles[variant]}>
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: 'var(--text-lg)', fontWeight: 800, color: accent }}>{value}</div>
    </div>
  )
}

/* ============================================
   MetricCard - 带副指标的指标卡片
   用于展示主值 + 辅助值（来自 TurnStrongPanel 去重）
   ============================================ */

interface MetricCardProps {
  title: string
  value: string
  subValue?: string
  accent?: string
}

export function MetricCard({ title, value, subValue, accent = 'var(--color-accent)' }: MetricCardProps) {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 14,
        padding: '14px 16px',
      }}
    >
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: 'var(--text-xl)', fontWeight: 700, color: accent }}>{value}</div>
      {subValue && (
        <div style={{ marginTop: 4, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{subValue}</div>
      )}
    </div>
  )
}

/* ============================================
   ActionButton - 操作按钮
   用于面板内的快捷操作（来自 TurnStrongPanel 去重）
   ============================================ */

interface ActionButtonProps {
  label: string
  icon?: React.ReactNode
  onClick: () => void
  active?: boolean
  variant?: 'primary' | 'secondary' | 'ghost'
}

export function ActionButton({ label, icon, onClick, active = false, variant = 'secondary' }: ActionButtonProps) {
  const baseStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: variant === 'primary' ? '8px 16px' : '6px 12px',
    borderRadius: 8,
    fontSize: 'var(--text-base)',
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
    transition: 'all .2s',
    opacity: 1,
  }

  const variants = {
    primary: {
      background: 'var(--color-accent)',
      color: 'var(--color-bg)',
    },
    secondary: {
      background: active ? 'var(--color-accent-dim)' : 'transparent',
      color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
      border: `1px solid ${active ? 'var(--color-accent)' : 'var(--color-border)'}`,
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-text-secondary)',
    },
  }

  return (
    <button
      onClick={onClick}
      style={{ ...baseStyle, ...variants[variant] }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--color-accent)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = active ? 'var(--color-accent)' : 'var(--color-border)'
      }}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

/* ============================================
   EmptyState - 空状态
   用于无数据/无结果场景（来自 TurnStrongPanel 去重）
   ============================================ */

interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        gap: 12,
      }}
    >
      <div style={{ color: 'var(--color-text-secondary)', opacity: 0.6 }}>{icon}</div>
      <div style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--color-text)' }}>{title}</div>
      {description && (
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', maxWidth: 400 }}>
          {description}
        </div>
      )}
      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop: 8,
            background: 'var(--color-accent)',
            color: 'var(--color-bg)',
            border: 'none',
            borderRadius: 8,
            padding: '8px 20px',
            fontSize: 'var(--text-base)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

/* ============================================
   Badge - 徽章
   用于状态/标签展示（从 NewsCard 提取）
   ============================================ */

interface BadgeProps {
  label: string
  variant?: 'default' | 'red' | 'green' | 'gold' | 'orange' | 'purple' | 'blue'
}

const BADGE_STYLES: Record<string, { background: string; color: string }> = {
  default: { background: 'var(--color-accent-dim)', color: 'var(--color-accent)' },
  red: { background: 'var(--color-red-dim)', color: 'var(--color-red)' },
  green: { background: 'var(--color-green-dim)', color: 'var(--color-green)' },
  gold: { background: 'var(--color-gold-dim)', color: 'var(--color-gold)' },
  orange: { background: 'var(--color-orange-dim)', color: 'var(--color-orange)' },
  purple: { background: 'var(--color-purple-dim)', color: 'var(--color-purple)' },
  blue: { background: 'var(--color-blue-dim)', color: 'var(--color-blue)' },
}

export function Badge({ label, variant = 'default' }: BadgeProps) {
  const style = BADGE_STYLES[variant]
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 999,
        fontSize: 'var(--text-xs)',
        fontWeight: 600,
        background: style.background,
        color: style.color,
      }}
    >
      {label}
    </span>
  )
}

/* ============================================
   ConfidenceDot - 数据置信度指示器
   来自 graphify "诚实优于黑盒" 理念
   ============================================ */

interface ConfidenceDotProps {
  level: 'extracted' | 'inferred' | 'ambiguous'
  size?: number
}

const CONFIDENCE_COLORS: Record<string, string> = {
  extracted: 'var(--confidence-extracted)',
  inferred: 'var(--confidence-inferred)',
  ambiguous: 'var(--confidence-ambiguous)',
}

const CONFIDENCE_LABELS: Record<string, string> = {
  extracted: '已采集',
  inferred: '已推断',
  ambiguous: '存疑',
}

export function ConfidenceDot({ level, size = 6 }: ConfidenceDotProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
      }}
      title={`数据置信度：${CONFIDENCE_LABELS[level]}`}
    >
      <span
        style={{
          display: 'inline-block',
          width: size,
          height: size,
          borderRadius: '50%',
          background: CONFIDENCE_COLORS[level],
        }}
      />
    </span>
  )
}

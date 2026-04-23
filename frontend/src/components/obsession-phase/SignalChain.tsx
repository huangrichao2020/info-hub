import type { ObsessionSignal } from '../../types'

const SIGNAL_COLORS = {
  triggered: { bg: 'var(--color-red-dim)', border: 'var(--color-red)', text: 'var(--color-red)' },
  default: { bg: 'var(--color-surface-elevated)', border: 'var(--color-border)', text: 'var(--color-text-tertiary)' },
}

interface SignalChainProps {
  signals: ObsessionSignal[]
  onToggle?: (name: string, triggered: boolean) => void
}

export default function SignalChain({ signals, onToggle }: SignalChainProps) {
  // 标准5个信号节点
  const defaultSignals: ObsessionSignal[] = [
    { name: 'leader_weak', label: '龙头乏力', triggered: false, description: '龙头股上涨动能衰减' },
    { name: 'followers_flee', label: '跟风先跑', triggered: false, description: '跟风股率先下跌' },
    { name: 'diffusion_stop', label: '扩散停止', triggered: false, description: '板块扩散效应消失' },
    { name: 'emotion_diverge', label: '情绪背离', triggered: false, description: '价格与情绪出现背离' },
    { name: 'capital_shift', label: '资金转向', triggered: false, description: '主力资金开始转移' },
  ]

  const nodes = signals.length > 0 ? signals : defaultSignals
  const nodeWidth = 100
  const nodeHeight = 36
  const arrowWidth = 30
  const totalWidth = nodes.length * (nodeWidth + arrowWidth) - arrowWidth
  const centerY = 28

  return (
    <div style={{ overflowX: 'auto', padding: '8px 0' }}>
      <svg
        width={totalWidth}
        height={56}
        viewBox={`0 0 ${totalWidth} 56`}
        style={{ display: 'block', margin: '0 auto' }}
      >
        {nodes.map((signal, i) => {
          const x = i * (nodeWidth + arrowWidth)
          const colors = signal.triggered ? SIGNAL_COLORS.triggered : SIGNAL_COLORS.default

          return (
            <g
              key={signal.name || i}
              onClick={() => onToggle?.(signal.name, !signal.triggered)}
              style={{ cursor: onToggle ? 'pointer' : 'default' }}
            >
              {/* 节点圆角矩形 */}
              <rect
                x={x}
                y={centerY - nodeHeight / 2}
                width={nodeWidth}
                height={nodeHeight}
                rx={8}
                ry={8}
                fill={colors.bg}
                stroke={colors.border}
                strokeWidth={signal.triggered ? 2 : 1}
              />
              {/* 节点文字 */}
              <text
                x={x + nodeWidth / 2}
                y={centerY + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={colors.text}
                fontSize={12}
                fontWeight={signal.triggered ? 700 : 500}
              >
                {signal.label}
              </text>
              {/* 触发标记 */}
              {signal.triggered && (
                <circle cx={x + nodeWidth - 8} cy={centerY - nodeHeight / 2 + 8} r={4} fill="var(--color-red)" />
              )}
              {/* 箭头 (非最后一个节点) */}
              {i < nodes.length - 1 && (
                <g>
                  <line
                    x1={x + nodeWidth + 4}
                    y1={centerY}
                    x2={x + nodeWidth + arrowWidth - 6}
                    y2={centerY}
                    stroke={signal.triggered ? 'var(--color-red)' : 'var(--color-border)'}
                    strokeWidth={2}
                  />
                  <polygon
                    points={`${x + nodeWidth + arrowWidth - 2},${centerY} ${x + nodeWidth + arrowWidth - 10},${centerY - 5} ${x + nodeWidth + arrowWidth - 10},${centerY + 5}`}
                    fill={signal.triggered ? 'var(--color-red)' : 'var(--color-border)'}
                  />
                </g>
              )}
            </g>
          )
        })}
      </svg>
      {/* 触发信号计数 */}
      <div style={{ textAlign: 'center', marginTop: 4 }}>
        <span style={{ fontSize: '.75em', color: 'var(--color-text-tertiary)' }}>
          已触发 {nodes.filter((s) => s.triggered).length} / {nodes.length}
        </span>
      </div>
    </div>
  )
}

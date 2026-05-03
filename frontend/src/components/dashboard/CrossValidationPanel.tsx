import { motion } from 'framer-motion'
import { ShieldCheck, AlertTriangle, TrendingUp, Target, Zap, Loader2 } from 'lucide-react'
import { useApiFetch } from '../../hooks/useApi'

interface PerspectiveData {
  name: string
  verdict: string
  confidence: number
  reasoning: string
  signals: string[]
  risks: string[]
}

interface Disagreement {
  perspective: string
  verdict: string
  reasoning: string
}

interface CrossValidationResponse {
  timestamp: string
  consensus: string
  consensus_strength: number
  disagreements: Disagreement[]
  perspectives: PerspectiveData[]
  final_verdict: string
  action_plan: string
}

const VERDICT_COLOR: Record<string, string> = {
  '看多': '#ef4444',
  '看空': '#22c55e',
  '中性': '#94a3b8',
  '结构性机会': '#f59e0b',
}

const VERDICT_BG: Record<string, string> = {
  '看多': 'rgba(239, 68, 68, 0.1)',
  '看空': 'rgba(34, 197, 94, 0.1)',
  '中性': 'rgba(148, 163, 184, 0.1)',
  '结构性机会': 'rgba(245, 158, 11, 0.1)',
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#94a3b8'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1,
        height: 4,
        borderRadius: 2,
        background: 'rgba(255,255,255,0.08)',
        overflow: 'hidden',
      }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          style={{ height: '100%', borderRadius: 2, background: color }}
        />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color, minWidth: 36, textAlign: 'right' }}>
        {pct}%
      </span>
    </div>
  )
}

function PerspectiveCard({ result, index }: { result: PerspectiveData; index: number }) {
  const color = VERDICT_COLOR[result.verdict] || '#94a3b8'
  const bg = VERDICT_BG[result.verdict] || 'rgba(148, 163, 184, 0.1)'

  const icons: Record<string, React.ReactNode> = {
    '供需': <ShieldCheck size={18} />,
    '执念': <Target size={18} />,
    '住相': <AlertTriangle size={18} />,
    '龙头': <TrendingUp size={18} />,
    '宏观': <Zap size={18} />,
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      style={{
        padding: '18px 20px',
        borderRadius: 16,
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ padding: 8, borderRadius: 10, background: bg, color, display: 'flex' }}>
            {icons[result.name]}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>{result.name}</div>
            <div style={{
              fontSize: 11, fontWeight: 600, padding: '2px 8px',
              borderRadius: 999, background: bg, color,
              display: 'inline-block', marginTop: 2,
            }}>
              {result.verdict}
            </div>
          </div>
        </div>
        <ConfidenceBar value={result.confidence} />
      </div>

      <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, margin: '0 0 12px' }}>
        {result.reasoning}
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {(result.signals || []).length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#4ade80', marginBottom: 6 }}>✓ 看多信号</div>
            {(result.signals || []).map((s, i) => (
              <div key={i} style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginBottom: 3 }}>• {s}</div>
            ))}
          </div>
        )}
        {(result.risks || []).length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#f87171', marginBottom: 6 }}>⚠ 风险</div>
            {(result.risks || []).map((r, i) => (
              <div key={i} style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginBottom: 3 }}>• {r}</div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default function CrossValidationPanel() {
  const { data, loading, error } = useApiFetch<CrossValidationResponse>('/stock/cross-validation')

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
      <Loader2 size={32} className="animate-spin" style={{ color: 'var(--color-gold)' }} />
      <span style={{ marginLeft: 12, color: 'var(--color-dim)' }}>正在交叉验证...</span>
    </div>
  )

  if (error) return (
    <div style={{ padding: 20, color: '#f87171', fontSize: 14 }}>
      <AlertTriangle size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle' }} />
      {error}
    </div>
  )

  if (!data) return null

  const perspectives = data.perspectives || []
  const disagreements = data.disagreements || []
  const strengthPct = Math.round((data.consensus_strength || 0) * 100)

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* 共识摘要卡 */}
      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 20,
          padding: '24px 26px',
          background:
            'radial-gradient(circle at top left, rgba(251,191,36,.18), transparent 30%), radial-gradient(circle at 80% 20%, rgba(56,189,248,.14), transparent 25%), linear-gradient(140deg, rgba(15,23,42,.98), rgba(17,24,39,.96) 50%, rgba(28,25,23,.98))',
          border: '1px solid rgba(251,191,36,.14)',
        }}
      >
        <div style={{ position: 'absolute', inset: 'auto -30px -50px auto', width: 180, height: 180, borderRadius: '50%', background: 'rgba(180,83,9,.1)', filter: 'blur(18px)' }} />
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <ShieldCheck size={20} style={{ color: 'var(--color-gold)' }} />
            <h2 style={{ margin: 0, fontSize: 17, fontWeight: 800, letterSpacing: '-0.02em' }}>
              交叉验证结论
            </h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{
                fontSize: 13, padding: '4px 10px', borderRadius: 999,
                background: VERDICT_BG[data.consensus] || 'rgba(148,163,184,0.1)',
                color: VERDICT_COLOR[data.consensus] || '#94a3b8',
                fontWeight: 700, display: 'inline-block', marginBottom: 10,
              }}>
                {data.consensus}
              </div>
              <p style={{ margin: 0, fontSize: 13, color: 'rgba(255,255,255,0.65)', lineHeight: 1.7 }}>
                {data.final_verdict}
              </p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--color-dim)' }}>
                <span>共识强度</span>
                <span style={{ fontWeight: 700, color: strengthPct >= 70 ? '#4ade80' : '#f59e0b' }}>{strengthPct}%</span>
              </div>
              <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${strengthPct}%` }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                  style={{ height: '100%', borderRadius: 3, background: strengthPct >= 70 ? '#4ade80' : '#f59e0b' }}
                />
              </div>
              {data.action_plan && (
                <div style={{
                  padding: '8px 12px', background: 'rgba(255,255,255,0.04)',
                  borderRadius: 10, fontSize: 12, color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, marginTop: 4,
                }}>
                  <span style={{ color: 'var(--color-gold)', fontWeight: 600 }}>📋 动作：</span>
                  {data.action_plan}
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.section>

      {/* 分歧点 */}
      {disagreements.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          style={{ padding: '14px 18px', borderRadius: 14, background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <AlertTriangle size={16} style={{ color: '#f59e0b' }} />
            <span style={{ fontSize: 13, fontWeight: 700, color: '#f59e0b' }}>视角分歧</span>
          </div>
          {disagreements.map((d, i) => (
            <div key={i} style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginBottom: 4 }}>
              <span style={{ color: '#fbbf24' }}>▸</span>
              <strong style={{ color: '#fcd34d' }}>{d.perspective}</strong>（{d.verdict}）：{d.reasoning}
            </div>
          ))}
        </motion.div>
      )}

      {/* 五视角卡片 */}
      {perspectives.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 14 }}>
          {perspectives.map((p, i) => (
            <PerspectiveCard key={p.name} result={p} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}

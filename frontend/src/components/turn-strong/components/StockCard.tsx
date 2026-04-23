import { motion } from 'framer-motion'
import { BadgeCheck, RefreshCcw, Sparkles, TimerReset, Zap } from 'lucide-react'
import type { TurnStrongStock } from '../../../types'
import { convictionTier, formatPercent } from '../utils/score'

/* TurnStrongStockCard - 个股详情卡片 */
export default function TurnStrongStockCard({
  item,
  score,
  leader,
  role,
  index,
  selected,
  onSelect,
}: {
  item: TurnStrongStock
  score: number
  leader: string
  role: string
  index: number
  selected: boolean
  onSelect: () => void
}) {
  const screen = item.screen || {}
  const analysis = item.analysis || {}
  const liveQuote = item.live_quote || {}
  const intraday = item.intraday_status || {}
  const newsItems = item.news_items || []
  const recommendation = analysis.recommendation || 'watch'
  const tier = convictionTier(score)
  const recColor = recommendation === 'buy' ? 'var(--color-red)' : recommendation === 'avoid' ? 'var(--color-green)' : 'var(--color-gold)'

  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      style={{
        background: index < 3 ? 'linear-gradient(160deg, rgba(251,146,60,.08), rgba(17,24,39,.96) 45%, var(--color-surface))' : 'var(--color-surface)',
        borderRadius: 16,
        border: `1px solid ${selected ? 'rgba(56,189,248,.42)' : index < 3 ? 'rgba(251,146,60,.2)' : 'var(--color-border)'}`,
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        cursor: 'pointer',
      }}
      onClick={onSelect}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-gold)', fontWeight: 700 }}>#{item.rank}</span>
            <h4 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, margin: 0 }}>{item.name}</h4>
            {leader && (
              <span style={{
                padding: '4px 8px', borderRadius: 999, fontSize: 'var(--text-xs)', fontWeight: 700,
                background: 'rgba(251,191,36,.08)', border: '1px solid rgba(251,191,36,.16)', color: 'var(--color-gold)',
              }}>
                {leader}
              </span>
            )}
            <span style={{
              padding: '4px 8px', borderRadius: 999, fontSize: 'var(--text-xs)', fontWeight: 700,
              background: role === '中军' ? 'rgba(239,68,68,.08)' : role === '龙头' ? 'rgba(56,189,248,.08)' : 'rgba(148,163,184,.08)',
              border: role === '中军' ? '1px solid rgba(239,68,68,.16)' : role === '龙头' ? '1px solid rgba(56,189,248,.16)' : '1px solid rgba(148,163,184,.16)',
              color: role === '中军' ? 'var(--color-red)' : role === '龙头' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
            }}>
              {role}
            </span>
          </div>
          <div style={{ marginTop: 6, fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>
            {item.code} · {screen.board || '主板'} · {screen.industry || '行业待补充'}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>方法论结论</div>
          <div style={{ marginTop: 6, color: recColor, fontSize: 'var(--text-base)', fontWeight: 700 }}>
            {analysis.recommendation_label || '观察为主'}
          </div>
          <div style={{ marginTop: 6, fontSize: 'var(--text-sm)', color: tier.color, fontWeight: 700 }}>
            {tier.label} · {score} 分
          </div>
        </div>
      </div>

      {/* Signal Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
        <SignalTile icon={<Zap size={14} />} label="竞价量比" value={screen.auction_volume_ratio != null ? String(screen.auction_volume_ratio) : '--'} />
        <SignalTile icon={<BadgeCheck size={14} />} label="高开幅度" value={formatPercent(screen.auction_change_pct)} />
        <SignalTile icon={<Sparkles size={14} />} label="前日获利盘" value={screen.previous_profit_ratio != null ? `${screen.previous_profit_ratio.toFixed(2)}%` : '--'} />
        <SignalTile icon={<RefreshCcw size={14} />} label="今日获利盘" value={screen.current_profit_ratio != null ? `${screen.current_profit_ratio.toFixed(2)}%` : '--'} />
      </div>

      {/* Mini Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
        <MiniMetric title="入池价" value={screen.latest_price != null ? `${screen.latest_price.toFixed(2)}` : '--'} accent="var(--color-gold)" />
        <MiniMetric title="当前涨幅" value={formatPercent(liveQuote.change_pct ?? screen.change_pct)} accent={(liveQuote.change_pct ?? screen.change_pct ?? 0) >= 0 ? 'var(--color-red)' : 'var(--color-green)'} />
        <MiniMetric title="盘中状态" value={intraday.label || '待刷新'} accent="var(--color-accent)" />
      </div>

      {/* Tags */}
      {(screen.style_concept || '').split('、').filter(Boolean).length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(item.source_tags || []).map((tag) => (
            <span key={`${item.code}-${tag}`} style={{
              padding: '5px 8px', borderRadius: 999, fontSize: 'var(--text-xs)',
              border: '1px solid rgba(251,191,36,.18)', background: 'rgba(251,191,36,.08)', color: 'var(--color-gold)',
            }}>
              {tag}
            </span>
          ))}
          {(screen.style_concept || '').split('、').filter(Boolean).slice(0, 6).map((tag) => (
            <span key={tag} style={{
              padding: '5px 8px', borderRadius: 999, fontSize: 'var(--text-xs)',
              border: '1px solid rgba(56,189,248,.18)', background: 'rgba(56,189,248,.08)', color: 'var(--color-accent)',
            }}>
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Narrative Blocks */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <NarrativeBlock title="逻辑支撑" content={analysis.logic_support || '暂无结构化逻辑说明。'} />
        <NarrativeBlock title="消息支持" content={analysis.news_support || '暂无结构化消息说明。'} />
        <NarrativeBlock title="方法论判断" content={analysis.methodology_view || intraday.summary || '等待盘中承接确认。'} />
      </div>

      {/* Risk Flags */}
      {(analysis.risk_flags || []).length > 0 && (
        <div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', marginBottom: 8 }}>风险提示</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(analysis.risk_flags || []).slice(0, 3).map((risk) => (
              <span key={risk} style={{
                padding: '5px 8px', borderRadius: 999, fontSize: 'var(--text-xs)',
                border: '1px solid rgba(239,68,68,.18)', background: 'rgba(239,68,68,.08)', color: '#fca5a5',
              }}>
                {risk}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Execution Plan */}
      {analysis.execution_plan && (
        <div style={{
          padding: '11px 12px', borderRadius: 12, border: '1px solid rgba(251,191,36,.16)',
          background: 'rgba(15,23,42,.42)', fontSize: 'var(--text-sm)', lineHeight: 1.6, color: 'var(--color-text)',
        }}>
          <span style={{ color: 'var(--color-gold)', fontWeight: 700 }}>执行建议：</span>
          {analysis.execution_plan}
        </div>
      )}

      {/* News */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <TimerReset size={14} color="var(--color-text-secondary)" />
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>消息线索</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {newsItems.length === 0 ? (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>暂无匹配新闻。</div>
          ) : newsItems.slice(0, 3).map((news) => (
            <a
              key={`${item.code}-${news.title}`}
              href={news.url || '#'}
              target={news.url ? '_blank' : undefined}
              rel={news.url ? 'noreferrer' : undefined}
              style={{
                textDecoration: 'none', color: 'inherit', padding: '9px 10px', borderRadius: 12,
                border: '1px solid rgba(148,163,184,.14)', background: 'rgba(15,23,42,.36)',
              }}
            >
              <div style={{ fontSize: 'var(--text-sm)', lineHeight: 1.55 }}>{news.title}</div>
              <div style={{ marginTop: 5, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                {news.source || '未知来源'} · {news.date || '--'}
              </div>
            </a>
          ))}
        </div>
      </div>
    </motion.article>
  )
}

function SignalTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{
      padding: '10px 11px', borderRadius: 12, border: '1px solid rgba(148,163,184,.14)',
      background: 'rgba(15,23,42,.42)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-text-secondary)', fontSize: 'var(--text-xs)' }}>
        {icon}{label}
      </div>
      <div style={{ marginTop: 7, fontSize: 'var(--text-lg)', fontWeight: 700 }}>{value}</div>
    </div>
  )
}

function MiniMetric({ title, value, accent }: { title: string; value: string; accent: string }) {
  return (
    <div style={{
      padding: '10px 11px', borderRadius: 12, border: '1px solid rgba(148,163,184,.14)',
      background: 'rgba(15,23,42,.28)',
    }}>
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: 'var(--text-base)', fontWeight: 700, color: accent }}>{value}</div>
    </div>
  )
}

function NarrativeBlock({ title, content }: { title: string; content: string }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: 'var(--text-sm)', lineHeight: 1.7, color: 'var(--color-text)' }}>{content}</div>
    </div>
  )
}

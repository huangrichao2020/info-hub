import { motion } from 'framer-motion'
import {
  ArrowRight,
  CandlestickChart,
  Newspaper,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react'

import { useApiFetch } from '../../hooks/useApi'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { useAppStore } from '../../stores/appStore'
import { SECTION_META } from '../../config/sections'
import { ConfidenceDot } from '../common'
import type { Section, TradeEvidenceSnapshot } from '../../types'

const CORE_ACTIONS: { key: Section; kicker: string; bullets: string[] }[] = [
  {
    key: 'concept-board',
    kicker: '概念优先',
    bullets: [
      '先看哪个概念是 S/A/B/C/D 档',
      '先看板块梯队，再看单票强弱',
      '避免一上来就被零散个股带偏',
    ],
  },
  {
    key: 'review-report',
    kicker: '复盘主引擎',
    bullets: [
      '先判断 主线 / 独立龙头 / 区间防御',
      '输出 基准 / 乐观 / 风险 情景路径',
      '把持仓评估和时间门纪律一起收口',
    ],
  },
  {
    key: 'turn-strong',
    kicker: '盘前执行器',
    bullets: [
      '竞价强度、板块共振、消息支撑统一评估',
      '不因单个漂亮数据直接判 buy',
      '用多周期量价确认开盘后的承接质量',
    ],
  },
]

const EVIDENCE_ITEMS = [
  { key: 'fin-news' as Section, label: '财经新闻', detail: '外部冲击、政策催化、事件脉冲' },
  { key: 'sectors' as Section, label: '热门板块', detail: '主线扩散、防御集中、板块轮动' },
  { key: 'zt-analysis' as Section, label: '涨停分析', detail: '情绪高度、连板结构、龙头辨识度' },
]

export default function TradeDeskPanel() {
  const setSection = useAppStore((state) => state.setSection)
  const refreshKey = useAppStore((state) => state.refreshKey)

  const { data: snapshot, loading: loadingEvidence } = useApiFetch<TradeEvidenceSnapshot>('/evidence/snapshot', {
    deps: [refreshKey],
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        style={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 24,
          padding: '28px 26px',
          background:
            'radial-gradient(circle at top left, rgba(251,191,36,.22), transparent 28%), radial-gradient(circle at 78% 18%, rgba(56,189,248,.18), transparent 22%), linear-gradient(140deg, rgba(15,23,42,.98), rgba(17,24,39,.96) 45%, rgba(28,25,23,.98))',
          border: '1px solid rgba(251,191,36,.16)',
        }}
      >
        <div style={{ position: 'absolute', inset: 'auto -40px -60px auto', width: 220, height: 220, borderRadius: '50%', background: 'rgba(180,83,9,.12)', filter: 'blur(20px)' }} />
        <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(320px, .8fr)', gap: 20, alignItems: 'start' }}>
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '7px 12px', borderRadius: 999, background: 'rgba(251,191,36,.1)', border: '1px solid rgba(251,191,36,.18)', color: 'var(--color-gold)', fontSize: '.76em', fontWeight: 700 }}>
              <Sparkles size={14} />
              Uwillberich First
            </div>
            <h2 style={{ marginTop: 16, fontSize: '2.2rem', lineHeight: 1.02, letterSpacing: '-0.05em', maxWidth: 680 }}>
              先定市场状态，再做复盘与转强决策
            </h2>
            <p style={{ marginTop: 16, maxWidth: 680, color: 'var(--color-dim)', lineHeight: 1.8, fontSize: '.96em' }}>
              `info-hub` 现在不再是分散的资讯面板，而是围绕两条交易主线组织：
              <span style={{ color: 'var(--color-text)' }}> 交易复盘 </span>
              负责定框架，
              <span style={{ color: 'var(--color-text)' }}> 转强作战台 </span>
              负责盘前执行。其余模块全部退到证据层，只为方法论服务。
            </p>
          </div>

          <div
            style={{
              borderRadius: 20,
              padding: 18,
              background: 'rgba(15,23,42,.52)',
              border: '1px solid rgba(148,163,184,.12)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <ShieldCheck size={18} color="var(--color-accent)" />
              <div style={{ fontSize: '.9em', fontWeight: 700 }}>四条铁律</div>
            </div>
            <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
              {[
                '先定方法论，再调工具',
                '数据为辅，逻辑为主',
                '不因数据好看改变市场判断',
                '工具与 uwillberich 冲突时，信 uwillberich',
              ].map((rule) => (
                <div key={rule} style={{ padding: '10px 12px', borderRadius: 14, background: 'rgba(30,41,59,.5)', border: '1px solid rgba(148,163,184,.12)', fontSize: '.84em', color: 'var(--color-text)' }}>
                  {rule}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        {CORE_ACTIONS.map((action, index) => {
          const meta = SECTION_META[action.key]
          const Icon = meta.icon
          return (
            <motion.button
              key={action.key}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * index, duration: 0.3 }}
              onClick={() => setSection(action.key)}
              style={{
                textAlign: 'left',
                borderRadius: 22,
                padding: 20,
                background:
                  action.key === 'review-report'
                    ? 'linear-gradient(155deg, rgba(56,189,248,.16), rgba(15,23,42,.98) 52%)'
                    : 'linear-gradient(155deg, rgba(239,68,68,.16), rgba(15,23,42,.98) 52%)',
                border: `1px solid ${action.key === 'review-report' ? 'rgba(56,189,248,.24)' : 'rgba(239,68,68,.24)'}`,
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '.76em', color: meta.dotColor, fontWeight: 700 }}>{action.kicker}</div>
                  <div style={{ marginTop: 6, fontSize: '1.36rem', fontWeight: 800, letterSpacing: '-0.04em' }}>{meta.label}</div>
                  <div style={{ marginTop: 8, fontSize: '.84em', color: 'var(--color-dim)', lineHeight: 1.7 }}>{meta.description}</div>
                </div>
                <div style={{ width: 42, height: 42, borderRadius: 14, display: 'grid', placeItems: 'center', background: 'rgba(255,255,255,.04)', color: meta.dotColor }}>
                  <Icon size={20} />
                </div>
              </div>

              <div style={{ display: 'grid', gap: 8 }}>
                {action.bullets.map((bullet) => (
                  <div key={bullet} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', color: 'var(--color-text)', fontSize: '.84em', lineHeight: 1.6 }}>
                    <span style={{ marginTop: 7, width: 6, height: 6, borderRadius: '50%', background: meta.dotColor, flexShrink: 0 }} />
                    <span>{bullet}</span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 'auto', display: 'inline-flex', alignItems: 'center', gap: 8, color: meta.dotColor, fontSize: '.82em', fontWeight: 700 }}>
                进入模块
                <ArrowRight size={14} />
              </div>
            </motion.button>
          )
        })}
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(320px, .9fr)', gap: 16 }}>
        <div
          style={{
            borderRadius: 20,
            padding: 20,
            background: 'var(--color-card)',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <CandlestickChart size={18} color="var(--color-gold)" />
            <div style={{ fontSize: '1rem', fontWeight: 800 }}>作战顺序</div>
          </div>
          <div style={{ marginTop: 16, display: 'grid', gap: 12 }}>
            {[
              ['第一步', '判断市场分类', '主线、独立龙头、区间防御，必须先定性。'],
              ['第二步', '给出情景概率', '输出 基准 / 乐观 / 风险，而不是单一路径。'],
              ['第三步', '按时间门执行', '09:00、09:25、09:30-10:00、14:00 各做不同判断。'],
              ['第四步', '让证据层补强', '新闻、板块、涨停、问财筛选只负责提供证据。'],
            ].map(([step, title, detail]) => (
              <div key={step} style={{ display: 'grid', gridTemplateColumns: '86px 1fr', gap: 14, alignItems: 'start' }}>
                <div style={{ fontSize: '.74em', fontWeight: 700, color: 'var(--color-accent)' }}>{step}</div>
                <div>
                  <div style={{ fontSize: '.92em', fontWeight: 700 }}>{title}</div>
                  <div style={{ marginTop: 4, fontSize: '.82em', color: 'var(--color-dim)', lineHeight: 1.7 }}>{detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            borderRadius: 20,
            padding: 20,
            background: 'linear-gradient(180deg, rgba(17,24,39,.98), rgba(15,23,42,.92))',
            border: '1px solid rgba(148,163,184,.14)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <ScanSearch size={18} color="var(--color-accent)" />
            <div style={{ fontSize: '1rem', fontWeight: 800 }}>证据层入口</div>
          </div>
          <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
            {EVIDENCE_ITEMS.map((item) => (
              <button
                key={item.key}
                onClick={() => setSection(item.key)}
                style={{
                  textAlign: 'left',
                  borderRadius: 16,
                  padding: '12px 14px',
                  background: 'rgba(30,41,59,.5)',
                  border: '1px solid rgba(148,163,184,.12)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ fontSize: '.88em', fontWeight: 700 }}>{item.label}</div>
                  <ArrowRight size={14} color="var(--color-accent)" />
                </div>
                <div style={{ marginTop: 6, fontSize: '.78em', color: 'var(--color-dim)', lineHeight: 1.6 }}>{item.detail}</div>
              </button>
            ))}
          </div>
          <div style={{ marginTop: 16, padding: '12px 14px', borderRadius: 16, background: 'rgba(251,191,36,.08)', border: '1px solid rgba(251,191,36,.16)', fontSize: '.8em', color: 'var(--color-dim)', lineHeight: 1.7 }}>
            这些入口只能辅助判断，不能越过复盘中心和转强作战台直接形成交易结论。
          </div>
        </div>
      </section>

      <section
        style={{
          borderRadius: 20,
          padding: 20,
          background: 'linear-gradient(160deg, rgba(17,24,39,.98), rgba(15,23,42,.94))',
          border: '1px solid rgba(148,163,184,.14)',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '.82em', fontWeight: 700 }}>交易证据面板</div>
            <div style={{ marginTop: 4, fontSize: '.74em', color: 'var(--color-dim)' }}>
              把指数、候选概念板块、财经新闻、涨停验证压成一屏，减少来回切换。
            </div>
          </div>
          {snapshot?.turn_strong && (
            <div style={{ fontSize: '.76em', color: 'var(--color-dim)' }}>
              今日转强池：{snapshot.turn_strong.selection_total} 只
            </div>
          )}
        </div>

        {loadingEvidence ? (
          <LoadingSkeleton count={4} />
        ) : snapshot ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 16 }}>
            <div style={{ borderRadius: 16, padding: 16, background: 'rgba(15,23,42,.5)', border: '1px solid rgba(148,163,184,.12)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <TrendingUp size={16} color="var(--color-gold)" />
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>候选概念板块</div>
                {snapshot.sector_evidence.fallback_used ? (
                  <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                    <ConfidenceDot level="inferred" size={6} /> 推断数据
                  </span>
                ) : (
                  <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                    <ConfidenceDot level="extracted" size={6} /> 实时采集
                  </span>
                )}
              </div>
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {snapshot.sector_evidence.items.slice(0, 5).map((item) => (
                  <div key={item.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 'var(--text-sm)' }}>
                    <div>{item.name}</div>
                    <div style={{ color: item.change_pct >= 0 ? 'var(--color-red)' : 'var(--color-green)', fontWeight: 700 }}>
                      {item.change_pct != null ? `${item.change_pct >= 0 ? '+' : ''}${item.change_pct.toFixed(2)}%` : 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ borderRadius: 16, padding: 16, background: 'rgba(15,23,42,.5)', border: '1px solid rgba(148,163,184,.12)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Newspaper size={16} color="var(--color-accent)" />
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>财经新闻</div>
                {snapshot.news_evidence.fallback_used ? (
                  <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                    <ConfidenceDot level="inferred" size={6} /> 缓存数据
                  </span>
                ) : (
                  <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                    <ConfidenceDot level="extracted" size={6} /> 实时采集
                  </span>
                )}
              </div>
              <div style={{ marginTop: 12, display: 'grid', gap: 10 }}>
                {snapshot.news_evidence.items.slice(0, 3).map((item) => (
                  <div key={item.id} style={{ paddingBottom: 8, borderBottom: '1px solid rgba(148,163,184,.08)' }}>
                    <div style={{ fontSize: '.8em', fontWeight: 700 }}>{item.title}</div>
                    <div style={{ marginTop: 4, fontSize: '.72em', color: 'var(--color-dim)' }}>
                      {item.source} · {(item.collected_at || item.published_at || '').slice(0, 16)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ borderRadius: 16, padding: 16, background: 'rgba(15,23,42,.5)', border: '1px solid rgba(148,163,184,.12)' }}>
              <div style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>指数快照</div>
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {snapshot.indices.map((idx) => (
                  <div key={idx.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 'var(--text-sm)' }}>
                    <div>{idx.name}</div>
                    <div style={{ color: idx.change_pct >= 0 ? 'var(--color-red)' : 'var(--color-green)', fontWeight: 700 }}>
                      {idx.change_pct != null ? `${idx.change_pct >= 0 ? '+' : ''}${idx.change_pct.toFixed(2)}%` : 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ borderRadius: 16, padding: 16, background: 'rgba(15,23,42,.5)', border: '1px solid rgba(148,163,184,.12)' }}>
              <div style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>涨停验证</div>
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {snapshot.zt_evidence.items.slice(0, 5).map((item) => (
                  <div key={item.code} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 'var(--text-sm)' }}>
                    <div>{item.name}</div>
                    <div style={{ color: 'var(--color-red)', fontWeight: 700 }}>
                      {item.change_pct != null ? `+${item.change_pct.toFixed(2)}%` : 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: '.82em', color: 'var(--color-dim)' }}>证据快照暂时不可用。</div>
        )}
      </section>
    </div>
  )
}

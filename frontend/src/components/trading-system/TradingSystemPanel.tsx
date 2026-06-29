import { useEffect, useState, useCallback, useRef } from 'react'
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import {
  AlertTriangle, ArrowUpCircle, BarChart3, CheckCircle,
  ChevronDown, ChevronRight, Clock, Database,
  DollarSign, Eye, Filter, FlaskConical,
  LineChart, Loader2, RefreshCw, Search,
  Settings, ShieldAlert, Signal, TrendingUp, Zap,
  X, Plus, Trash2, BookOpen,
} from 'lucide-react'

import client from '../../api/client'
import LoadingSkeleton from '../common/LoadingSkeleton'
import {
  IconZhangTing, IconDieTing, IconZhuXian, IconLongTou,
  IconKanZhang, IconKanDie, IconKLineUp, IconKLineDown,
} from '../common/AStockIcons'

// ═══════════════════════════════════════════════════════
// CountUp 数字滚动 — framer-motion 实现，无需外部库
// ═══════════════════════════════════════════════════════

function CountUp({ value, duration = 0.8, decimals = 0, suffix = '', className = '' }: {
  value: number
  duration?: number
  decimals?: number
  suffix?: string
  className?: string
}) {
  const motionVal = useMotionValue(value)
  const displayRef = useRef<HTMLSpanElement>(null)
  const [text, setText] = useState(value.toFixed(decimals) + suffix)

  useEffect(() => {
    const controls = animate(motionVal, value, {
      duration,
      ease: 'easeOut',
      onUpdate: (v) => {
        if (displayRef.current) {
          displayRef.current.textContent = v.toFixed(decimals) + suffix
        }
      },
    })
    return controls.stop
  }, [value, duration, decimals, suffix, motionVal])

  return (
    <span ref={displayRef} className={className}>
      {text}
    </span>
  )
}

// ═══════════════════════════════════════════════════════
// 类型定义
// ═══════════════════════════════════════════════════════

interface MarketSnapshot {
  snapshot_time: string
  trade_date: string
  shanghai_close: number
  shanghai_change_pct: number
  chuangye_close: number
  chuangye_change_pct: number
  zt_count: number
  dt_count: number
  breadth: number
  main_net_flow: number
  top_industry_sectors: any[]
  top_concept_sectors: any[]
  signal_count: number
  lit_signals?: string[]
}

interface SignalResult {
  signal_count: number
  lit_signals: string[]
  obsession_phase: string
  phase_label: string
  confidence_score: number
  confidence_grade: string
  market_status: string
  financial_tier: string
  financial定性: string
  financial_strategy: string
  final_action: string
  analysis_time: string
  position_limit_pct: number
}

interface Position {
  id: number
  stock_code: string
  stock_name: string
  position_type: string
  shares: number
  avg_cost: number
  current_price: number
  stop_loss_price: number
  profit_pct: number
  signal_action: string
  urgent: boolean
  global_signal_count: number
}

interface Candidate {
  code: string
  name: string
  change_pct: number
  turnover_rate: number
  amount: number
  score: number
  tier: string
  level: string
  reason: string
  buy_allowed: boolean
  lianban_days: number
}

interface ScreenerResult {
  screening_time: string
  market_status: string
  obsession_phase: string
  confidence_grade: string
  confidence_score: number
  zhuxiang_count: number
  main_line: any
  picks_A: Candidate[]
  picks_B: Candidate[]
  picks_C: Candidate[]
  buyable: Candidate[]
  total_candidates: number
  final_action: string
}

// ═══════════════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════════════

function formatPct(v?: number | null, digits = 2) {
  if (v == null) return '--'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(digits)}%`
}

function pnlColor(pct: number) {
  if (pct > 5) return 'text-red-400'
  if (pct > 0) return 'text-red-500'
  if (pct < -5) return 'text-green-400'
  if (pct < 0) return 'text-green-500'
  return 'text-gray-400'
}

function gradeColor(grade: string) {
  const map: Record<string, string> = {
    A: 'bg-green-500/20 text-green-400 border border-green-500/40',
    B: 'bg-blue-500/20 text-blue-400 border border-blue-500/40',
    C: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
    D: 'bg-red-500/20 text-red-400 border border-red-500/40',
  }
  return map[grade] || 'bg-gray-700/50 text-gray-400 border border-gray-600'
}

function phaseColor(phase: string) {
  const map: Record<string, string> = {
    '少数先知期': 'text-green-400',
    '机构试错期': 'text-blue-400',
    '游资点火期': 'text-yellow-400',
    '散户共识期': 'text-orange-400',
    '全民住相期': 'text-red-400',
    '派发期': 'text-red-500 font-bold',
  }
  return map[phase] || 'text-gray-400'
}

function SignalLamp({ lit }: { lit: string[] }) {
  const all = ['龙头乏力', '跟风先跑', '扩散停止', '情绪背离', '资金转向']
  return (
    <div className="flex gap-1 flex-wrap">
      {all.map(s => (
        <span key={s} className={`text-xs px-2 py-0.5 rounded border font-mono ${
          lit.includes(s)
            ? 'bg-red-500/20 border-red-500/50 text-red-400'
            : 'bg-gray-800 border-gray-700 text-gray-500'
        }`}>
          {lit.includes(s) ? '●' : '○'} {s}
        </span>
      ))}
    </div>
  )
}

function IndexCard({ label, close, change }: { label: string; close: number; change: number }) {
  return (
    <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 min-w-[90px]">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-lg font-mono text-white">{close > 0 ? close.toFixed(2) : '--'}</div>
      <div className={`text-sm font-mono ${change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
        {formatPct(change)}
      </div>
    </div>
  )
}

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    A: 'bg-green-500/20 text-green-400 border border-green-500/40',
    B: 'bg-blue-500/20 text-blue-400 border border-blue-500/40',
    C: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
    D: 'bg-red-500/20 text-red-400 border border-red-500/40',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${colors[tier] || ''}`}>
      {tier}
    </span>
  )
}

function CandidateRow({ c }: { c: Candidate }) {
  return (
    <tr className="border-b border-gray-800/60 hover:bg-gray-800/20 transition-colors text-sm">
      <td className="px-3 py-2"><span className="font-mono text-blue-400">{c.code}</span></td>
      <td className="px-3 py-2 text-white">{c.name}</td>
      <td className="px-3 py-2 text-gray-400 text-xs max-w-[180px] truncate">{c.reason}</td>
      <td className="px-3 py-2 text-center">
        {c.lianban_days > 0
          ? <span className="text-red-400 font-bold">{c.lianban_days}连板</span>
          : <span className="text-gray-600">-</span>}
      </td>
      <td className="px-3 py-2 text-gray-400 font-mono">{c.turnover_rate}%</td>
      <td className="px-3 py-2 text-center font-mono text-yellow-400">{c.score}</td>
      <td className="px-3 py-2"><TierBadge tier={c.tier} /></td>
      <td className="px-3 py-2">
        {c.buy_allowed
          ? <span className="text-xs bg-green-600/20 text-green-400 border border-green-500/40 px-2 py-0.5 rounded">可买</span>
          : <span className="text-xs text-gray-600">-</span>}
      </td>
    </tr>
  )
}

// ═══════════════════════════════════════════════════════
// 子Tab组件
// ═══════════════════════════════════════════════════════

function SignalTab({ signal, snapshot }: { signal: SignalResult | null; snapshot: MarketSnapshot | null }) {
  if (!signal) return <LoadingSkeleton />
  const breakdown = signal as any

  return (
    <div className="space-y-4">
      {/* 住相五维 */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-400" />
          住相五维破裂检测
        </h3>
        <SignalLamp lit={signal.lit_signals || []} />
        <div className="mt-3 text-sm text-gray-400">
          点亮 <span className="text-red-400 font-bold text-lg">{signal.signal_count}</span> 个信号
          {' → '}
          {signal.signal_count >= 4 ? '强制清仓' :
           signal.signal_count === 3 ? '减仓 50%' :
           signal.signal_count === 2 ? '控仓' : '正常'}
        </div>
      </div>

      {/* 执念阶段 */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-yellow-400" />
          执念六阶段
        </h3>
        <div className={`text-xl font-bold ${phaseColor(signal.obsession_phase)}`}>
          {signal.obsession_phase}
        </div>
        <div className="text-sm text-gray-400 mt-1">{signal.phase_label}</div>
      </div>

      {/* 确信度 */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-blue-400" />
          确信度评分
        </h3>
        <div className="flex items-center gap-4 mb-3">
          <div className={`text-3xl font-bold px-3 py-1 rounded-lg border ${gradeColor(signal.confidence_grade)}`}>
            {signal.confidence_grade}档
          </div>
          <div>
            <div className="text-2xl font-mono text-white">{signal.confidence_score}分</div>
            <div className="text-xs text-gray-500">置信度综合评分</div>
          </div>
        </div>
      </div>

      {/* 金融三级表 */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          金融三级表
        </h3>
        <div className="text-white font-medium">{signal.financial定性}</div>
        <div className="text-sm text-blue-400 mt-1">{signal.financial_strategy}</div>
      </div>

      {/* 最终动作 */}
      <div className="bg-blue-950/30 rounded-xl border border-blue-800/50 p-5">
        <h3 className="text-sm font-bold text-blue-300 mb-2">操作建议</h3>
        <div className="text-lg text-white font-bold">{signal.final_action}</div>
        <div className="text-sm text-gray-400 mt-1">仓位上限：{signal.position_limit_pct}%</div>
      </div>
    </div>
  )
}

function SnapshotTab({ snapshot }: { snapshot: MarketSnapshot | null }) {
  if (!snapshot) return <LoadingSkeleton />

  const sectors = (snapshot.top_industry_sectors || []).slice(0, 12)

  return (
    <div className="space-y-4">
      {/* 指数 + 关键指标 */}
      <div className="grid grid-cols-6 gap-3">
        <IndexCard label="上证指数" close={snapshot.shanghai_close} change={snapshot.shanghai_change_pct} />
        <IndexCard label="创业板指" close={snapshot.chuangye_close} change={snapshot.chuangye_change_pct} />
        <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 text-center">
          <div className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1"><IconZhangTing size={12} />涨停</div>
          <div className="text-2xl font-bold text-red-400"><CountUp value={snapshot.zt_count || 0} /></div>
        </div>
        <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 text-center">
          <div className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1"><IconDieTing size={12} />跌停</div>
          <div className="text-2xl font-bold text-green-400"><CountUp value={snapshot.dt_count || 0} /></div>
        </div>
        <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 text-center">
          <div className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1"><IconKLineUp size={12} />上涨家数</div>
          <div className="text-2xl font-bold text-white"><CountUp value={snapshot.breadth || 0} /></div>
        </div>
        <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 text-center">
          <div className="text-xs text-gray-500 mb-1">主力净流</div>
          <div className={`text-2xl font-bold font-mono ${(snapshot.main_net_flow || 0) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {formatPct(snapshot.main_net_flow)}
          </div>
        </div>
      </div>

      {/* 板块排行 */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <ArrowUpCircle className="w-4 h-4 text-orange-400" />
          板块涨幅排行
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {sectors.map((s: any, i: number) => (
            <div key={i} className="flex justify-between items-center px-3 py-2 bg-gray-800/40 rounded border border-gray-800">
              <div className="text-xs text-gray-400 truncate max-w-[120px]">{s.板块名称}</div>
              <div className={`text-sm font-mono font-bold ${parseFloat(s.涨跌幅) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                {formatPct(parseFloat(s.涨跌幅))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 采集时间 */}
      <div className="text-xs text-gray-600 text-right">
        数据时间：{snapshot.snapshot_time}
      </div>
    </div>
  )
}

function ScreenTab({ screener, onRefresh }: { screener: ScreenerResult | null; onRefresh: () => void }) {
  // 加载逻辑：当 screener 为空时主动拉一次 leaders 兜底
  if (!screener) {
    return (
      <div className="space-y-4">
        <LeaderBoard mainLine={null} />
        <div className="flex flex-col items-center justify-center h-32 gap-4 bg-gray-900/30 rounded-xl border border-gray-800">
          <div className="text-gray-500">点击启动完整筛选（信号 + 候选 + 回测）</div>
          <button onClick={onRefresh} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm flex items-center gap-2">
            <Filter className="w-4 h-4" /> 启动筛选
          </button>
        </div>
      </div>
    )
  }
  if (!screener) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-gray-500">点击开始筛选</div>
        <button onClick={onRefresh} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm flex items-center gap-2">
          <Filter className="w-4 h-4" /> 启动筛选
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 筛选概览 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`text-sm px-2 py-0.5 rounded border ${gradeColor(screener.confidence_grade)}`}>
            {screener.confidence_grade}档 {screener.confidence_score}分
          </span>
          <span className="text-sm text-white">{screener.obsession_phase}</span>
          <span className="text-xs text-gray-500">共 {screener.total_candidates} 只候选</span>
        </div>
        <button onClick={onRefresh} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-white">
          <RefreshCw className="w-3.5 h-3.5" /> 重新筛选
        </button>
      </div>

      {/* 主线方向 */}
      {screener.main_line && (
        <div className="bg-blue-950/30 rounded-xl border border-blue-800/50 p-4">
          <div className="text-xs text-blue-400 font-bold mb-2">主线方向</div>
          <div className="text-white font-bold">{screener.main_line.market_type}</div>
          <div className="text-xs text-gray-400 mt-1">
            涨停 {screener.main_line.zt_count} | 上涨家数 {screener.main_line.breadth} | 主力净流 {formatPct(screener.main_line.main_net_flow)}
          </div>
        </div>
      )}

      {/* 候选表 */}
      {screener.buyable.length > 0 && (
        <div>
          <div className="text-sm font-bold text-white mb-2 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            可买清单 ({screener.buyable.length})
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-800">
                  <th className="px-3 py-2 text-left">代码</th>
                  <th className="px-3 py-2 text-left">名称</th>
                  <th className="px-3 py-2 text-left">理由</th>
                  <th className="px-3 py-2 text-center">连板</th>
                  <th className="px-3 py-2 text-center">换手</th>
                  <th className="px-3 py-2 text-center">评分</th>
                  <th className="px-3 py-2 text-center">档位</th>
                  <th className="px-3 py-2 text-center">可买</th>
                </tr>
              </thead>
              <tbody>
                {screener.buyable.map(c => <CandidateRow key={c.code} c={c} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* A档 */}
      {screener.picks_A.length > 0 && (
        <div>
          <div className="text-sm font-bold text-white mb-2">A档 ({screener.picks_A.length})</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-800">
                  <th className="px-3 py-2 text-left">代码</th><th className="px-3 py-2 text-left">名称</th>
                  <th className="px-3 py-2 text-left">理由</th><th className="px-3 py-2 text-center">连板</th>
                  <th className="px-3 py-2 text-center">换手</th><th className="px-3 py-2 text-center">评分</th>
                  <th className="px-3 py-2 text-center">档位</th>
                </tr>
              </thead>
              <tbody>{screener.picks_A.map(c => <CandidateRow key={c.code} c={c} />)}</tbody>
            </table>
          </div>
        </div>
      )}

      {/* B档 */}
      {screener.picks_B.length > 0 && (
        <div>
          <div className="text-sm font-bold text-white mb-2">B档 ({screener.picks_B.length})</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-800">
                  <th className="px-3 py-2 text-left">代码</th><th className="px-3 py-2 text-left">名称</th>
                  <th className="px-3 py-2 text-left">理由</th><th className="px-3 py-2 text-center">连板</th>
                  <th className="px-3 py-2 text-center">换手</th><th className="px-3 py-2 text-center">评分</th>
                  <th className="px-3 py-2 text-center">档位</th>
                </tr>
              </thead>
              <tbody>{screener.picks_B.map(c => <CandidateRow key={c.code} c={c} />)}</tbody>
            </table>
          </div>
        </div>
      )}

      {/* 主线龙头：大方向里的细分板块 */}
      <LeaderBoard mainLine={screener.main_line} />
    </div>
  )
}

// 主线龙头展示：从 main_lines 拿 top_leaders，没有就 fallback 到独立 leaders 接口
function LeaderBoard({ mainLine }: { mainLine: any }) {
  const [standalone, setStandalone] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // 优先用 main_line.main_lines[].top_leaders（screen 跑过的话）
  const fromMainLine = mainLine?.main_lines?.filter((l: any) => (l.top_leaders?.length ?? 0) > 0) ?? []

  const needFallback = fromMainLine.length === 0

  useEffect(() => {
    if (!needFallback) return
    setLoading(true)
    client.get<any>('/trading/leaders?top_sectors=5&per_sector=3')
      .then((r) => setStandalone(r.result?.leaders ?? []))
      .catch(() => setStandalone([]))
      .finally(() => setLoading(false))
  }, [needFallback])

  const data = needFallback ? standalone : fromMainLine

  if (loading) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <IconZhuXian size={16} color="#fb923c" />
          主线龙头（细分板块）
        </h3>
        <div className="text-center py-6 text-gray-600">挖掘中...</div>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-orange-950/30 to-gray-900/50 rounded-xl border border-orange-800/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <IconZhuXian size={16} color="#fb923c" />
          主线龙头 · 大方向里的细分板块
          <span className="text-xs text-orange-400 font-normal ml-2">
            {needFallback ? '（实时拉取）' : `共 ${data.length} 条主线`}
          </span>
        </h3>
      </div>

      <div className="space-y-3">
        {data.map((line: any, idx: number) => {
          const leaders = line.top_leaders || line.leaders || []
          const ztCount = line.zt_in_leaders ?? leaders.filter((x: any) => x.is_zt).length
          return (
            <div key={line.sector_code || idx} className="bg-gray-900/60 rounded-lg p-3 border border-gray-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{line.sector_name}</span>
                  <span className="text-xs text-gray-500 font-mono">{line.sector_code}</span>
                </div>
                <div className="flex items-center gap-2">
                  {ztCount > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40">
                      🔥 {ztCount}涨停
                    </span>
                  )}
                  <span className={`text-sm font-mono font-bold ${parseFloat(line.sector_change_pct) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {formatPct(parseFloat(line.sector_change_pct))}
                  </span>
                </div>
              </div>

              {leaders.length > 0 ? (
                <div className="grid grid-cols-3 gap-2">
                  {leaders.map((stk: any) => (
                    <div key={stk.code} className={`flex items-center justify-between px-2 py-1.5 rounded text-xs border ${
                      stk.is_zt
                        ? 'bg-red-950/40 border-red-700/60'
                        : 'bg-gray-800/60 border-gray-700/60'
                    }`}>
                      <div className="flex items-center gap-1 min-w-0">
                        {stk.is_zt && <span className="text-red-400 text-xs">●</span>}
                        <span className="font-mono text-blue-400 text-xs">{stk.code}</span>
                        <span className="text-white truncate">{stk.name}</span>
                      </div>
                      <span className={`font-mono font-bold ml-1 whitespace-nowrap ${
                        stk.change_pct >= 0 ? 'text-red-400' : 'text-green-400'
                      }`}>
                        {formatPct(stk.change_pct)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-600 text-center py-2">暂无龙头数据</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PositionsTab({
  positions, signalCheck, onDelete, onAdd,
}: {
  positions: Position[]
  signalCheck: Position[]
  onDelete: (code: string) => void
  onAdd: () => void
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-400">
          共 {positions.length} 只持仓
        </div>
        <button
          onClick={onAdd}
          className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg"
        >
          <Plus className="w-4 h-4" /> 添加持仓
        </button>
      </div>

      {signalCheck.length === 0 && positions.length === 0 && (
        <div className="text-center py-16 text-gray-600">
          <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-30" />
          暂无持仓，点击右上角添加
        </div>
      )}

      {signalCheck.length > 0 && (
        <div className="space-y-2">
          {signalCheck.map(pos => (
            <div key={pos.stock_code} className={`flex items-center justify-between px-4 py-3 rounded-xl border transition-colors ${
              pos.urgent ? 'bg-red-950/30 border-red-800/50' : 'bg-gray-900/50 border-gray-800'
            }`}>
              <div className="flex items-center gap-4">
                <div>
                  <div className="font-mono text-blue-400 text-sm">{pos.stock_code}</div>
                  <div className="text-white text-sm">{pos.stock_name}</div>
                </div>
                <div className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">{pos.position_type}</div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-mono font-bold ${pnlColor(pos.profit_pct)}`}>
                  {formatPct(pos.profit_pct)}
                </div>
                <div className="text-xs text-gray-500">
                  持仓均价 {pos.avg_cost.toFixed(2)} | 现价 {pos.current_price.toFixed(2)}
                </div>
                <div className={`text-xs mt-0.5 ${pos.urgent ? 'text-red-400' : 'text-gray-500'}`}>
                  {pos.signal_action}
                </div>
              </div>
              <button
                onClick={() => onDelete(pos.stock_code)}
                className="text-gray-600 hover:text-red-400 p-1"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function BacktestTab({
  btStock, setBtStock, btResult, onRun, btLoading,
}: {
  btStock: string; setBtStock: (v: string) => void
  btResult: any; onRun: () => void; btLoading: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <input
          placeholder="输入股票代码（如 000001）"
          value={btStock}
          onChange={e => setBtStock(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onRun()}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm"
        />
        <button
          onClick={onRun}
          disabled={!btStock || btLoading}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm"
        >
          {btLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
          {btLoading ? '回测中...' : '回测'}
        </button>
      </div>

      {btResult && !btResult.error && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800 text-center">
            <div className="text-xs text-gray-500 mb-1">总收益率</div>
            <div className={`text-2xl font-bold font-mono ${btResult.total_return_pct >= 0 ? 'text-red-400' : 'text-green-400'}`}>
              {formatPct(btResult.total_return_pct)}
            </div>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800 text-center">
            <div className="text-xs text-gray-500 mb-1">胜率</div>
            <div className="text-2xl font-bold font-mono text-white">{btResult.win_rate_pct}%</div>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800 text-center">
            <div className="text-xs text-gray-500 mb-1">最大回撤</div>
            <div className="text-2xl font-bold font-mono text-red-400">{btResult.max_drawdown_pct}%</div>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800 text-center">
            <div className="text-xs text-gray-500 mb-1">交易次数</div>
            <div className="text-2xl font-bold font-mono text-white">{btResult.total_trades}</div>
          </div>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════
// 主组件
// ═══════════════════════════════════════════════════════

export default function TradingSystemPanel() {
  const [activeTab, setActiveTab] = useState<'signal' | 'snapshot' | 'screen' | 'positions' | 'backtest'>('signal')
  const [loading, setLoading] = useState(false)
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null)
  const [signal, setSignal] = useState<SignalResult | null>(null)
  const [screener, setScreener] = useState<ScreenerResult | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [signalCheck, setSignalCheck] = useState<Position[]>([])
  const [showAddPos, setShowAddPos] = useState(false)
  const [posForm, setPosForm] = useState({
    stock_code: '', stock_name: '', position_type: 'MID',
    shares: 1000, avg_cost: 0, stop_loss_price: 0,
  })
  const [btStock, setBtStock] = useState('')
  const [btResult, setBtResult] = useState<any>(null)
  const [btLoading, setBtLoading] = useState(false)

  const loadSignal = useCallback(async () => {
    setLoading(true)
    try {
      const r = await client.get<any>('/trading/signal')
      if (r.signal) setSignal(r.signal)
    } catch {}
    setLoading(false)
  }, [])

  const loadSnapshot = useCallback(async () => {
    setLoading(true)
    try {
      const r = await client.get<any>('/trading/snapshot')
      if (r.snapshot) setSnapshot(r.snapshot)
    } catch {}
    setLoading(false)
  }, [])

  const loadScreener = useCallback(async () => {
    setLoading(true)
    try {
      const r = await client.get<any>('/trading/screen')
      if (r.result) setScreener(r.result)
    } catch {}
    setLoading(false)
  }, [])

  const loadPositions = useCallback(async () => {
    try {
      const r = await client.get<any>('/trading/positions')
      if (r.positions) setPositions(r.positions || [])
      if (r.signal_check) setSignalCheck(r.signal_check || [])
    } catch {}
  }, [])

  const refresh = useCallback(() => {
    loadSignal()
    loadSnapshot()
    loadPositions()
  }, [loadSignal, loadSnapshot, loadPositions])

  const runBacktest = async () => {
    if (!btStock) return
    setBtLoading(true)
    try {
      const r = await client.post<any>('/trading/backtest', {
        stock_code: btStock, signal_type: 'ma20_break',
        stop_loss_pct: 7, take_profit_pct: 15, holding_days_max: 10,
      })
      setBtResult(r.result || r)
    } catch {}
    setBtLoading(false)
  }

  const addPosition = async () => {
    try {
      await client.post('/trading/positions', posForm)
      setShowAddPos(false)
      setPosForm({ stock_code: '', stock_name: '', position_type: 'MID', shares: 1000, avg_cost: 0, stop_loss_price: 0 })
      loadPositions()
    } catch {}
  }

  const deletePosition = async (code: string) => {
    try {
      await client.delete(`/trading/positions/${code}`)
      loadPositions()
    } catch {}
  }

  useEffect(() => { refresh() }, [refresh])

  const tabs = [
    { key: 'signal' as const, label: '信号分析', icon: Signal },
    { key: 'snapshot' as const, label: '实时行情', icon: BarChart3 },
    { key: 'screen' as const, label: '筛选', icon: Filter },
    { key: 'positions' as const, label: '持仓', icon: DollarSign },
    { key: 'backtest' as const, label: '回测', icon: FlaskConical },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* 顶栏 */}
      <div className="flex-shrink-0 p-4 border-b border-gray-800 space-y-2">
        {/* 状态行 */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            {signal && (
              <>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${phaseColor(signal.obsession_phase)}`}>
                    {signal.obsession_phase}
                  </span>
                  <span className="text-xs text-gray-600">{signal.phase_label}</span>
                </div>
                <span className="text-gray-700">|</span>
                <span className={`text-sm px-2 py-0.5 rounded border font-bold ${gradeColor(signal.confidence_grade)}`}>
                  {signal.confidence_grade}档 {signal.confidence_score}分
                </span>
                <span className="text-gray-700">|</span>
                <span className="text-sm text-white bg-blue-500/15 px-2 py-0.5 rounded border border-blue-500/40">
                  {signal.market_status}
                </span>
                <SignalLamp lit={signal.lit_signals || []} />
              </>
            )}
          </div>

          <div className="flex items-center gap-4">
            {snapshot && (
              <div className="flex gap-2">
                <IndexCard label="沪指" close={snapshot.shanghai_close} change={snapshot.shanghai_change_pct} />
                <IndexCard label="创业板" close={snapshot.chuangye_close} change={snapshot.chuangye_change_pct} />
                <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 text-center min-w-[70px]">
                  <div className="text-xs text-gray-500">涨停</div>
                  <div className="text-xl font-bold text-red-400">{snapshot.zt_count}</div>
                </div>
                <div className="bg-gray-900/60 rounded-lg p-3 border border-gray-800 text-center min-w-[70px]">
                  <div className="text-xs text-gray-500">上涨家</div>
                  <div className="text-xl font-bold text-white">{snapshot.breadth}</div>
                </div>
              </div>
            )}
            <button onClick={refresh} className="p-2 rounded hover:bg-gray-800 text-gray-500 hover:text-white transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 动作行 */}
        {signal && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-xs text-gray-500">仓位上限：<span className="text-white font-bold">{signal.position_limit_pct}%</span></span>
            <span className="text-gray-700">|</span>
            <span className="text-yellow-400">{signal.final_action}</span>
            <span className="text-gray-700">|</span>
            <span className="text-xs text-gray-500">
              金融三级表：<span className="text-blue-400">{signal.financial定性}</span> {signal.financial_strategy}
            </span>
          </div>
        )}
      </div>

      {/* Tab 栏 */}
      <div className="flex-shrink-0 flex border-b border-gray-800 px-4">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors ${
              activeTab === t.key ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* 内容 */}
      <div className="flex-1 overflow-auto p-4">
        {loading ? <LoadingSkeleton /> :
         activeTab === 'signal' ? <SignalTab signal={signal} snapshot={snapshot} /> :
         activeTab === 'snapshot' ? <SnapshotTab snapshot={snapshot} /> :
         activeTab === 'screen' ? <ScreenTab screener={screener} onRefresh={loadScreener} /> :
         activeTab === 'positions' ? (
           <PositionsTab positions={positions} signalCheck={signalCheck} onDelete={deletePosition} onAdd={() => setShowAddPos(true)} />
         ) : (
           <BacktestTab btStock={btStock} setBtStock={setBtStock} btResult={btResult} onRun={runBacktest} btLoading={btLoading} />
         )}
      </div>

      {/* 添加持仓弹窗 */}
      {showAddPos && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={() => setShowAddPos(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-[420px]" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-white font-bold text-lg">添加持仓</h3>
              <button onClick={() => setShowAddPos(false)} className="text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <div className="flex gap-3">
                <input placeholder="股票代码" value={posForm.stock_code}
                  onChange={e => setPosForm({ ...posForm, stock_code: e.target.value })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
                <input placeholder="名称" value={posForm.stock_name}
                  onChange={e => setPosForm({ ...posForm, stock_name: e.target.value })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div className="flex gap-3">
                <select value={posForm.position_type}
                  onChange={e => setPosForm({ ...posForm, position_type: e.target.value })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="SHORT">SHORT 短线</option>
                  <option value="MID">MID 中线</option>
                  <option value="LONG">LONG 长线</option>
                </select>
                <input type="number" placeholder="数量(手)" value={posForm.shares || ''}
                  onChange={e => setPosForm({ ...posForm, shares: Number(e.target.value) })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div className="flex gap-3">
                <input type="number" placeholder="持仓成本" value={posForm.avg_cost || ''}
                  onChange={e => setPosForm({ ...posForm, avg_cost: Number(e.target.value) })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
                <input type="number" placeholder="止损价" value={posForm.stop_loss_price || ''}
                  onChange={e => setPosForm({ ...posForm, stop_loss_price: Number(e.target.value) })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setShowAddPos(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">取消</button>
              <button onClick={addPosition} className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg">确认添加</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

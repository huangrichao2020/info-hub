import {
  ArrowUpCircle,
  FileText,
  LayoutGrid,
  Radar,
  ScanSearch,
  TrendingUp,
  CandlestickChart,
  CalendarDays,
  AlertTriangle,
  GitMerge,
  type LucideIcon,
} from 'lucide-react'

import type { Section } from '../types'

export interface SectionMeta {
  key: Section
  label: string
  shortLabel: string
  description: string
  dotColor: string
  icon: LucideIcon
  group: 'core' | 'evidence' | 'calendar'
}

export const SECTION_META: Record<Section, SectionMeta> = {
  'trade-desk': {
    key: 'trade-desk',
    label: '交易中枢',
    shortLabel: '中枢',
    description: '以 uwillberich 为核心，统领复盘与转强两条主线。',
    dotColor: 'var(--color-gold)',
    icon: TrendingUp,
    group: 'core',
  },
  'main-wave': {
    key: 'main-wave',
    label: '主升浪机会',
    shortLabel: '机会',
    description: '放量上涨 + MA25 趋势向上的量价共振标的。',
    dotColor: 'var(--color-emerald)',
    icon: ArrowUpCircle,
    group: 'core',
  },
  'investment-calendar': {
    key: 'investment-calendar',
    label: '投资日历',
    shortLabel: '日历',
    description: '未来重要会议、经济数据、政策发布日程及受益板块。',
    dotColor: 'var(--color-accent)',
    icon: CalendarDays,
    group: 'calendar',
  },
  'chan-chart': {
    key: 'chan-chart',
    label: '日K缠论图',
    shortLabel: '缠论',
    description: '看日K、成交量、笔段中枢和一买二买一卖二卖。',
    dotColor: 'var(--color-purple)',
    icon: CandlestickChart,
    group: 'core',
  },
  'review-report': {
    key: 'review-report',
    label: '交易复盘',
    shortLabel: '复盘',
    description: '先分市场状态，再落持仓、情景概率与时间门纪律。',
    dotColor: 'var(--color-accent)',
    icon: FileText,
    group: 'core',
  },
  'strict-turn-strong': {
    key: 'strict-turn-strong',
    label: '严选作战台',
    shortLabel: '严选',
    description: '从宽池中二次压缩，优先给出更少、更硬的出手名单。',
    dotColor: 'var(--color-red)',
    icon: Radar,
    group: 'core',
  },
  'concept-board': {
    key: 'concept-board',
    label: '概念作战图',
    shortLabel: '概念',
    description: '先看概念强弱和板块梯队，再决定是追龙头还是只观察。',
    dotColor: 'var(--color-orange)',
    icon: ScanSearch,
    group: 'core',
  },
  'turn-strong': {
    key: 'turn-strong',
    label: '转强作战台',
    shortLabel: '转强',
    description: '竞价强度、板块共振、消息支撑统一回到市场分类之下。',
    dotColor: 'var(--color-red)',
    icon: Radar,
    group: 'core',
  },
  'fin-news': {
    key: 'fin-news',
    label: '财经新闻',
    shortLabel: '新闻',
    description: '追踪外部冲击与关键催化，作为证据层输入。',
    dotColor: 'var(--color-green)',
    icon: TrendingUp,
    group: 'evidence',
  },
  sectors: {
    key: 'sectors',
    label: '热门板块',
    shortLabel: '板块',
    description: '验证板块强弱、主线扩散与防御集中。',
    dotColor: 'var(--color-orange)',
    icon: LayoutGrid,
    group: 'evidence',
  },
  'zt-analysis': {
    key: 'zt-analysis',
    label: '涨停分析',
    shortLabel: '涨停',
    description: '观察连板高度、情绪温度与高标结构。',
    dotColor: 'var(--color-red)',
    icon: ArrowUpCircle,
    group: 'evidence',
  },
  'obsession-phase': {
    key: 'obsession-phase',
    label: '住相信号',
    shortLabel: '住相',
    description: '执念→住相→破裂信号链可视化，辅助判断买卖时机。',
    dotColor: 'var(--color-red)',
    icon: AlertTriangle,
    group: 'core',
  },
  'cross-validation': {
    key: 'cross-validation',
    label: '交叉验证',
    shortLabel: '验证',
    description: '五视角交叉验证（供需/执念/住相/龙头/宏观），输出共识与行动计划。',
    dotColor: 'var(--color-purple)',
    icon: GitMerge,
    group: 'core',
  },
}

export const SECTION_GROUPS: { key: SectionMeta['group']; label: string; hint: string }[] = [
  { key: 'calendar', label: '前瞻规划', hint: '提前布局未来事件驱动机会' },
  { key: 'core', label: '核心作战', hint: '真正承担交易决策的主流程' },
  { key: 'evidence', label: '证据层', hint: '为方法论提供证据，不替代判断' },
]

export const SECTION_ORDER: Section[] = [
  'trade-desk',
  'main-wave',
  'cross-validation',
  'investment-calendar',
  'chan-chart',
  'concept-board',
  'review-report',
  'strict-turn-strong',
  'turn-strong',
  'fin-news',
  'sectors',
  'zt-analysis',
  'obsession-phase',
]

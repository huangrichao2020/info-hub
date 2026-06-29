/**
 * A股特色图标集 — 替代 lucide-react 在中文交易场景的不足
 *
 * 包含：
 *   - 涨停/跌停/炸板（带颜色）
 *   - 龙头/跟风/卡位/分歧/共振
 *   - 建仓/加仓/减仓/清仓/锁仓
 *   - K线（红涨/绿跌）
 *   - 主线/支线/题材/龙头股/妖股
 *
 * 用法：
 *   import { IconZhangTing, IconLongTou } from '../common/AStockIcons'
 *   <IconZhangTing size={16} />
 *
 * 如需扩展其他 A 股特色图标，直接在下面加 React 组件即可。
 */
import React from 'react'

export interface IconProps {
  size?: number
  className?: string
  color?: string
  strokeWidth?: number
}

const baseProps = (size = 16, color = 'currentColor', strokeWidth = 2) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: color,
  strokeWidth,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
})

// 涨停 — 上箭头带 ⭐
export const IconZhangTing: React.FC<IconProps> = ({ size = 16, className, color = '#ef4444' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M12 2 L4 12 L9 12 L9 22 L15 22 L15 12 L20 12 Z" fill={color} fillOpacity="0.15" />
    <path d="M12 2 L4 12 L9 12 L9 22 L15 22 L15 12 L20 12 Z" />
    <circle cx="18" cy="4" r="2" fill={color} />
  </svg>
)

// 跌停 — 下箭头带 ⚠️
export const IconDieTing: React.FC<IconProps> = ({ size = 16, className, color = '#22c55e' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M12 22 L4 12 L9 12 L9 2 L15 2 L15 12 L20 12 Z" fill={color} fillOpacity="0.15" />
    <path d="M12 22 L4 12 L9 12 L9 2 L15 2 L15 12 L20 12 Z" />
    <line x1="3" y1="3" x2="6" y2="6" />
    <line x1="6" y1="3" x2="3" y2="6" />
  </svg>
)

// 炸板（涨停开板回落）
export const IconZhaBan: React.FC<IconProps> = ({ size = 16, className, color = '#f59e0b' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <line x1="7" y1="10" x2="17" y2="10" />
    <line x1="7" y1="14" x2="13" y2="14" />
    <circle cx="6" cy="6" r="1" fill={color} />
    <circle cx="18" cy="18" r="1" fill={color} />
  </svg>
)

// 龙头股 — 戴皇冠的牛
export const IconLongTou: React.FC<IconProps> = ({ size = 16, className, color = '#fbbf24' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M3 17 L7 11 L10 14 L14 7 L17 12 L21 17 Z" />
    <circle cx="12" cy="6" r="1.5" fill={color} />
    <line x1="9" y1="5" x2="9" y2="2" />
    <line x1="15" y1="5" x2="15" y2="2" />
    <line x1="12" y1="5" x2="12" y2="2" />
  </svg>
)

// 跟风 — 跟在龙头后面的小鱼
export const IconGenFeng: React.FC<IconProps> = ({ size = 16, className, color = '#94a3b8' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M4 14 Q 8 10 12 14 Q 16 18 20 14" />
    <path d="M16 14 L 20 14 L 18 11" />
    <circle cx="7" cy="13" r="0.8" fill={color} />
  </svg>
)

// 主线（粗线连接节点）
export const IconZhuXian: React.FC<IconProps> = ({ size = 16, className, color = '#c0322f' }) => (
  <svg {...baseProps(size, color, 2.5)} className={className}>
    <line x1="4" y1="12" x2="20" y2="12" />
    <circle cx="6" cy="12" r="2.5" fill={color} />
    <circle cx="12" cy="12" r="2.5" fill={color} />
    <circle cx="18" cy="12" r="2.5" fill={color} />
  </svg>
)

// 支线/次线（细线连接）
export const IconZhiXian: React.FC<IconProps> = ({ size = 16, className, color = '#64748b' }) => (
  <svg {...baseProps(size, color, 1.5)} className={className}>
    <line x1="4" y1="12" x2="20" y2="12" strokeDasharray="2 2" />
    <circle cx="8" cy="12" r="1.5" fill={color} />
    <circle cx="16" cy="12" r="1.5" fill={color} />
  </svg>
)

// 建仓（从下往上的填充）
export const IconJianCang: React.FC<IconProps> = ({ size = 16, className, color = '#3b82f6' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <rect x="3" y="14" width="18" height="8" fill={color} fillOpacity="0.3" />
    <path d="M3 14 L9 10 L13 12 L17 6 L21 9" />
    <circle cx="9" cy="10" r="1" fill={color} />
    <circle cx="13" cy="12" r="1" fill={color} />
    <circle cx="17" cy="6" r="1" fill={color} />
  </svg>
)

// 加仓（双箭头向上）
export const IconJiaCang: React.FC<IconProps> = ({ size = 16, className, color = '#22c55e' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M6 14 L12 8 L18 14" />
    <path d="M9 14 L12 11 L15 14" />
    <line x1="3" y1="20" x2="21" y2="20" />
  </svg>
)

// 减仓（双箭头向下）
export const IconJianCangOut: React.FC<IconProps> = ({ size = 16, className, color = '#f97316' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M6 10 L12 16 L18 10" />
    <path d="M9 10 L12 13 L15 10" />
    <line x1="3" y1="20" x2="21" y2="20" />
  </svg>
)

// 清仓（空心方框 + X）
export const IconQingCang: React.FC<IconProps> = ({ size = 16, className, color = '#dc2626' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <rect x="3" y="3" width="18" height="18" />
    <line x1="8" y1="8" x2="16" y2="16" />
    <line x1="16" y1="8" x2="8" y2="16" />
  </svg>
)

// 锁仓（带锁的方框）
export const IconSuoCang: React.FC<IconProps> = ({ size = 16, className, color = '#6366f1' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <rect x="4" y="11" width="16" height="10" rx="1" fill={color} fillOpacity="0.2" />
    <path d="M7 11 V 8 a 5 5 0 0 1 10 0 V 11" />
    <circle cx="12" cy="16" r="1" fill={color} />
  </svg>
)

// K线 — 红涨
export const IconKLineUp: React.FC<IconProps> = ({ size = 16, className, color = '#ef4444' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <line x1="12" y1="2" x2="12" y2="22" />
    <rect x="8" y="8" width="8" height="10" fill={color} fillOpacity="0.8" stroke={color} />
  </svg>
)

// K线 — 绿跌
export const IconKLineDown: React.FC<IconProps> = ({ size = 16, className, color = '#22c55e' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <line x1="12" y1="2" x2="12" y2="22" />
    <rect x="8" y="8" width="8" height="10" fill={color} fillOpacity="0.2" stroke={color} />
  </svg>
)

// 妖股（带⚡的火箭）
export const IconYaoGu: React.FC<IconProps> = ({ size = 16, className, color = '#a855f7' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M14 2 L4 14 L10 14 L8 22 L18 10 L12 10 Z" fill={color} fillOpacity="0.3" />
    <path d="M14 2 L4 14 L10 14 L8 22 L18 10 L12 10 Z" />
    <circle cx="20" cy="4" r="1" fill={color} />
  </svg>
)

// 题材（带🔖的标签）
export const IconTiCai: React.FC<IconProps> = ({ size = 16, className, color = '#06b6d4' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M3 3 H10 L21 14 L14 21 L3 10 Z" />
    <circle cx="7" cy="7" r="1.2" fill={color} />
  </svg>
)

// 卡位（被截断的箭头）
export const IconKaWei: React.FC<IconProps> = ({ size = 16, className, color = '#ec4899' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <line x1="4" y1="20" x2="20" y2="4" />
    <line x1="14" y1="4" x2="20" y2="4" />
    <line x1="20" y1="4" x2="20" y2="10" />
    <line x1="4" y1="20" x2="11" y2="20" />
    <line x1="11" y1="20" x2="11" y2="14" />
  </svg>
)

// 分歧（上下分散箭头）
export const IconFenQi: React.FC<IconProps> = ({ size = 16, className, color = '#f59e0b' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <line x1="12" y1="12" x2="4" y2="4" />
    <line x1="12" y1="12" x2="20" y2="4" />
    <line x1="12" y1="12" x2="4" y2="20" />
    <line x1="12" y1="12" x2="20" y2="20" />
    <circle cx="12" cy="12" r="2" fill={color} />
  </svg>
)

// 共振（多个箭头同方向）
export const IconGongZhen: React.FC<IconProps> = ({ size = 16, className, color = '#10b981' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M4 18 L9 13 L13 16 L20 8" />
    <path d="M4 22 L9 17 L13 20 L20 12" strokeOpacity="0.5" />
    <circle cx="20" cy="8" r="1.5" fill={color} />
  </svg>
)

// 资金流入（带钱的箭头）
export const IconMoneyIn: React.FC<IconProps> = ({ size = 16, className, color = '#eab308' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7 V 17 M9 10 L 12 7 L 15 10" />
    <text x="12" y="14" fontSize="6" fill={color} textAnchor="middle" fontWeight="bold">¥</text>
  </svg>
)

// 看涨（多）
export const IconKanZhang: React.FC<IconProps> = ({ size = 16, className, color = '#dc2626' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M4 12 L9 7 L14 10 L20 4" />
    <circle cx="20" cy="4" r="2" fill={color} />
  </svg>
)

// 看跌（空）
export const IconKanDie: React.FC<IconProps> = ({ size = 16, className, color = '#15803d' }) => (
  <svg {...baseProps(size, color)} className={className}>
    <path d="M4 12 L9 17 L14 14 L20 20" />
    <circle cx="20" cy="20" r="2" fill={color} />
  </svg>
)

// ⭐ iconfont 集成（如果用户提供了 iconfont.css URL，用 font-class 渲染）
// 在 index.html 加：
//   <link rel="stylesheet" href="//at.alicdn.com/t/c/font_xxxxx.css">
// 然后用：
//   <IconFont name="icon-zhangting" size={16} />
export interface IconFontProps {
  name: string  // iconfont 的 class 名，如 'icon-zhangting'
  size?: number
  className?: string
  color?: string
}

export const IconFont: React.FC<IconFontProps> = ({ name, size = 16, className, color }) => (
  <i
    className={`iconfont ${name} ${className || ''}`}
    style={{
      fontSize: size,
      color: color || 'inherit',
    }}
  />
)
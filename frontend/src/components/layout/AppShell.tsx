import { Suspense, lazy, useState, useEffect } from 'react'

import Sidebar from './Sidebar'
import Header from './Header'
import AssistantPanel from '../assistant/AssistantPanel'
import { useAppStore } from '../../stores/appStore'
import LoadingSkeleton from '../common/LoadingSkeleton'
import { SECTION_GROUPS, SECTION_META, SECTION_ORDER } from '../../config/sections'

const PANELS = {
  'trade-desk': lazy(() => import('../dashboard/TradeDeskPanel')),
  'main-wave': lazy(() => import('../dashboard/MainWavePanel')),
  'cross-validation': lazy(() => import('../cross-validation/CrossValidationPanel')),
  'trading-system': lazy(() => import('../trading-system/TradingSystemPanel')),
  'investment-calendar': lazy(() => import('../investment-calendar/InvestmentCalendarPanel')),
  'chan-chart': lazy(() => import('../chan/ChanChartPanel')),
  'concept-board': lazy(() => import('../concept-board/ConceptBoardPanel')),
  'strict-turn-strong': lazy(() => import('../turn-strong/StrictTurnStrongPanel')),
  'fin-news': lazy(() => import('../fin-news/FinNewsPanel')),
  'sectors': lazy(() => import('../sectors/SectorsPanel')),
  'zt-analysis': lazy(() => import('../zt-analysis/ZTPanel')),
  'turn-strong': lazy(() => import('../turn-strong/TurnStrongPanel')),
  'review-report': lazy(() => import('../review-report/ReviewPanel')),
  'obsession-phase': lazy(() => import('../obsession-phase/ObsessionPhasePanel')),
  'cross-validation': lazy(() => import('../dashboard/CrossValidationPanel')),
  'amazingdata-kline': lazy(() => import('../quant/AmazingDataDailyBars')),
  'kline-multi-period': lazy(() => import('../quant/KlineMultiPeriod')),
  'chokepoint': lazy(() => import('../chokepoint/ChokePointPanel')),
  'daily-chance': lazy(() => import('../daily-chance/DailyChancePanel')),
}

/** Mobile top nav bar */
function MobileTopNav() {
  const { activeSection, setSection } = useAppStore()
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)

  // Build group -> items mapping
  const groupItems: Record<string, typeof SECTION_ORDER> = {}
  for (const key of SECTION_ORDER) {
    const meta = SECTION_META[key]
    if (!meta) continue
    if (!groupItems[meta.group]) groupItems[meta.group] = []
    groupItems[meta.group].push(key)
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 60,
      background: 'var(--color-surface)',
      borderBottom: '1px solid var(--color-border)',
    }}>
      {/* Group tabs */}
      <div style={{
        display: 'flex',
        overflowX: 'auto',
        padding: '6px 8px',
        gap: 4,
        scrollbarWidth: 'none',
      }}>
        {SECTION_GROUPS.map(g => {
          const isActive = groupItems[g.key]?.includes(activeSection)
          return (
            <button
              key={g.key}
              onClick={() => setExpandedGroup(expandedGroup === g.key ? null : g.key)}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                border: 'none',
                background: isActive ? 'var(--color-accent-dim)' : 'transparent',
                color: isActive ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
                fontSize: '0.72em',
                fontWeight: 600,
                whiteSpace: 'nowrap',
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              {g.label}
            </button>
          )
        })}
      </div>
      {/* Section chips (expanded) */}
      {expandedGroup && (
        <div style={{
          display: 'flex',
          overflowX: 'auto',
          padding: '0 8px 8px',
          gap: 6,
          scrollbarWidth: 'none',
        }}>
          {(groupItems[expandedGroup] || []).map(key => {
            const meta = SECTION_META[key]
            if (!meta) return null
            const isActive = activeSection === key
            return (
              <button
                key={key}
                onClick={() => { setSection(key); setExpandedGroup(null) }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 10px',
                  borderRadius: 20,
                  border: `1px solid ${isActive ? meta.dotColor : 'var(--color-border)'}`,
                  background: isActive ? `${meta.dotColor}22` : 'transparent',
                  color: isActive ? meta.dotColor : 'var(--color-text-secondary)',
                  fontSize: '0.68em',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                {meta.shortLabel || meta.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

/** Mobile bottom assistant (compact toggle) */
function MobileAssistant() {
  const [isOpen, setIsOpen] = useState(false)
  const { activeSection } = useAppStore()

  if (isOpen) {
    return (
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 60,
        height: '55vh',
        display: 'flex',
        flexDirection: 'column',
        borderTop: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          borderBottom: '1px solid var(--color-border)',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text)' }}>
            复盘大师
          </span>
          <button
            onClick={() => setIsOpen(false)}
            style={{
              padding: 4,
              borderRadius: 6,
              border: 'none',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <AssistantPanel />
        </div>
      </div>
    )
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 60,
      borderTop: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
      padding: '6px 12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <span style={{ fontSize: '0.72em', color: 'var(--color-text-tertiary)' }}>
        {activeSection === 'trade-desk' ? '交易台' : '详情'}
      </span>
      <button
        onClick={() => setIsOpen(true)}
        style={{
          padding: '6px 14px',
          borderRadius: 20,
          border: '1px solid var(--color-accent)',
          background: 'var(--color-accent-dim)',
          color: 'var(--color-accent)',
          fontSize: '0.72em',
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        💬 复盘大师
      </button>
    </div>
  )
}

export default function AppShell() {
  const { activeSection, sidebarCollapsed } = useAppStore()
  const [isMobile, setIsMobile] = useState(false)
  const Panel = PANELS[activeSection]

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Mobile layout: top nav + content + bottom assistant
  if (isMobile) {
    const mobileTopOffset = 70 // top nav height
    const mobileBottomOffset = 44 // bottom bar height

    return (
      <>
        <MobileTopNav />
        <div style={{
          marginTop: mobileTopOffset,
          marginBottom: mobileBottomOffset,
          minHeight: `calc(100vh - ${mobileTopOffset + mobileBottomOffset}px)`,
          overflowY: 'auto',
          padding: '16px 12px 24px',
          background: 'var(--color-bg)',
        }}>
          {Panel && (
            <Suspense fallback={<LoadingSkeleton count={6} />}>
              <Panel />
            </Suspense>
          )}
        </div>
        <MobileAssistant />
      </>
    )
  }

  // Desktop layout: sidebar + content + assistant
  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      background: 'var(--color-bg)',
    }}>
      {/* 左侧导航 */}
      <Sidebar />

      {/* 中间主内容区 */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          marginLeft: sidebarCollapsed ? 64 : 220,
          transition: 'margin-left .3s',
          minWidth: 0,
        }}
      >
        <Header />
        <div style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '20px 24px 40px',
        }}>
          <div style={{
            maxWidth: activeSection === 'trade-desk' ? 1320 : 1240,
            width: '100%',
            margin: '0 auto',
          }}>
            {Panel && (
              <Suspense fallback={<LoadingSkeleton count={activeSection === 'trade-desk' ? 4 : 6} />}>
                <Panel />
              </Suspense>
            )}
          </div>
        </div>
      </div>

      {/* 右侧复盘大师 */}
      <AssistantPanel />
    </div>
  )
}

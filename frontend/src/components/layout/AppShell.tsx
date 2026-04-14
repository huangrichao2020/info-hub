import { Suspense, lazy } from 'react'

import Sidebar from './Sidebar'
import Header from './Header'
import AssistantPanel from '../assistant/AssistantPanel'
import { useAppStore } from '../../stores/appStore'
import LoadingSkeleton from '../common/LoadingSkeleton'

const PANELS = {
  'trade-desk': lazy(() => import('../dashboard/TradeDeskPanel')),
  'investment-calendar': lazy(() => import('../investment-calendar/InvestmentCalendarPanel')),
  'chan-chart': lazy(() => import('../chan/ChanChartPanel')),
  'concept-board': lazy(() => import('../concept-board/ConceptBoardPanel')),
  'strict-turn-strong': lazy(() => import('../turn-strong/StrictTurnStrongPanel')),
  'ai-news': lazy(() => import('../ai-news/AINewsPanel')),
  'trending': lazy(() => import('../trending/TrendingPanel')),
  'article-gen': lazy(() => import('../article-gen/ArticleGenPanel')),
  'fin-news': lazy(() => import('../fin-news/FinNewsPanel')),
  'sectors': lazy(() => import('../sectors/SectorsPanel')),
  'zt-analysis': lazy(() => import('../zt-analysis/ZTPanel')),
  'turn-strong': lazy(() => import('../turn-strong/TurnStrongPanel')),
  'review-report': lazy(() => import('../review-report/ReviewPanel')),
}

export default function AppShell() {
  const { activeSection, sidebarCollapsed } = useAppStore()
  const Panel = PANELS[activeSection]

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      background: 'var(--color-bg)',
    }}>
      {/* 左侧导航 */}
      <Sidebar />

      {/* 中间主内容区 - 独立滚动 */}
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

      {/* 右侧复盘大师 - 固定高度，独立滚动 */}
      <AssistantPanel />
    </div>
  )
}

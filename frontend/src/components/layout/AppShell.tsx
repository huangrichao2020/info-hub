import Sidebar from './Sidebar'
import Header from './Header'
import { useAppStore } from '../../stores/appStore'

import AINewsPanel from '../ai-news/AINewsPanel'
import ViralPanel from '../viral/ViralPanel'
import TrendingPanel from '../trending/TrendingPanel'
import ArticleGenPanel from '../article-gen/ArticleGenPanel'
import FinNewsPanel from '../fin-news/FinNewsPanel'
import SectorsPanel from '../sectors/SectorsPanel'
import ZTPanel from '../zt-analysis/ZTPanel'
import ReviewPanel from '../review-report/ReviewPanel'

const PANELS: Record<string, React.FC> = {
  'ai-news': AINewsPanel,
  'viral': ViralPanel,
  'trending': TrendingPanel,
  'article-gen': ArticleGenPanel,
  'fin-news': FinNewsPanel,
  'sectors': SectorsPanel,
  'zt-analysis': ZTPanel,
  'review-report': ReviewPanel,
}

export default function AppShell() {
  const { activeSection, sidebarCollapsed } = useAppStore()
  const Panel = PANELS[activeSection]

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          marginLeft: sidebarCollapsed ? 64 : 220,
          transition: 'margin-left .3s',
        }}
      >
        <Header />
        <main style={{
          flex: 1,
          padding: '20px 24px 40px',
          overflowY: 'auto',
          maxWidth: 1200,
          width: '100%',
          margin: '0 auto',
        }}>
          {Panel && <Panel />}
        </main>
      </div>
    </div>
  )
}

import {
  Newspaper, Flame, Hash, PenLine, TrendingUp,
  LayoutGrid, ArrowUpCircle, FileText, PanelLeftClose, PanelLeft
} from 'lucide-react'
import { useAppStore } from '../../stores/appStore'
import type { Section } from '../../types'

const NAV_ITEMS: { key: Section; label: string; icon: typeof Newspaper }[] = [
  { key: 'ai-news', label: 'AI 新闻', icon: Newspaper },
  { key: 'viral', label: '自媒体爆款', icon: Flame },
  { key: 'trending', label: '热门话题', icon: Hash },
  { key: 'article-gen', label: '一键写文', icon: PenLine },
  { key: 'fin-news', label: '财经新闻', icon: TrendingUp },
  { key: 'sectors', label: '热门板块', icon: LayoutGrid },
  { key: 'zt-analysis', label: '涨停分析', icon: ArrowUpCircle },
  { key: 'review-report', label: '复盘报告', icon: FileText },
]

export default function Sidebar() {
  const { activeSection, setSection, sidebarCollapsed, toggleSidebar } = useAppStore()

  return (
    <aside
      className="fixed left-0 top-0 h-screen flex flex-col z-50 transition-all duration-300"
      style={{
        width: sidebarCollapsed ? 64 : 220,
        background: 'var(--color-card)',
        borderRight: '1px solid var(--color-border)',
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center px-4"
        style={{ height: 56, borderBottom: '1px solid var(--color-border)' }}
      >
        {!sidebarCollapsed && (
          <h1 style={{ fontSize: '1.3em', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1 }}>
            <span style={{ color: 'var(--color-gold)' }}>i</span>
            <span style={{ color: 'var(--color-text)' }}>nfo</span>
            <span style={{ color: 'var(--color-gold)' }}>Hub</span>
          </h1>
        )}
        <button
          onClick={toggleSidebar}
          className="ml-auto shrink-0 transition-colors"
          style={{
            padding: '6px',
            borderRadius: 8,
            color: 'var(--color-dim)',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          {sidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto" style={{ padding: '10px 8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {NAV_ITEMS.map(({ key, label, icon: Icon }) => {
            const active = activeSection === key
            return (
              <button
                key={key}
                onClick={() => setSection(key)}
                title={label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: sidebarCollapsed ? '10px' : '9px 14px',
                  justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
                  borderRadius: 10,
                  border: `1px solid ${active ? 'rgba(56,189,248,.25)' : 'transparent'}`,
                  background: active ? 'rgba(56,189,248,.08)' : 'transparent',
                  color: active ? 'var(--color-accent)' : 'var(--color-dim)',
                  fontSize: '.84em',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all .15s',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.borderColor = 'var(--color-accent)'
                    e.currentTarget.style.color = 'var(--color-accent)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.borderColor = 'transparent'
                    e.currentTarget.style.color = 'var(--color-dim)'
                  }
                }}
              >
                <Icon size={17} className="shrink-0" />
                {!sidebarCollapsed && <span>{label}</span>}
              </button>
            )
          })}
        </div>
      </nav>

      {/* Footer */}
      <div style={{
        padding: '10px',
        borderTop: '1px solid var(--color-border)',
        fontSize: '.72em',
        color: 'var(--color-dim)',
        textAlign: 'center',
      }}>
        {!sidebarCollapsed && 'Info Hub v0.1'}
      </div>
    </aside>
  )
}

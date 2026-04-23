import { PanelLeftClose, PanelLeft } from 'lucide-react'
import { useAppStore } from '../../stores/appStore'
import { SECTION_GROUPS, SECTION_META, SECTION_ORDER } from '../../config/sections'
import { useEffect, useState } from 'react'
import apiClient from '../../api/client'

interface VersionInfo {
  version: string
  commit: string
  date?: string
  build_time?: string
}

export default function Sidebar() {
  const { activeSection, setSection, sidebarCollapsed, toggleSidebar } = useAppStore()
  const [version, setVersion] = useState<VersionInfo | null>(null)

  useEffect(() => {
    apiClient.get<VersionInfo>('/version')
      .then(r => setVersion(r.data))
      .catch(() => {})
  }, [])

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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {SECTION_GROUPS.map((group) => {
            const items = SECTION_ORDER
              .map((key) => SECTION_META[key])
              .filter((item) => item.group === group.key)

            return (
              <div key={group.key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {!sidebarCollapsed && (
                  <div style={{ padding: '6px 10px 8px' }}>
                    <div style={{ fontSize: '.68em', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--color-dim)', fontWeight: 700 }}>
                      {group.label}
                    </div>
                    <div style={{ marginTop: 2, fontSize: '.7em', color: 'rgba(148,163,184,.72)', lineHeight: 1.4 }}>
                      {group.hint}
                    </div>
                  </div>
                )}

                {items.map(({ key, label, shortLabel, icon: Icon, dotColor }) => {
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
                        borderRadius: 12,
                        border: `1px solid ${active ? 'rgba(56,189,248,.22)' : 'transparent'}`,
                        background: active ? 'linear-gradient(90deg, rgba(56,189,248,.10), rgba(251,191,36,.06))' : 'transparent',
                        color: active ? 'var(--color-text)' : 'var(--color-dim)',
                        fontSize: '.84em',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all .15s',
                        whiteSpace: 'nowrap',
                      }}
                      onMouseEnter={(e) => {
                        if (!active) {
                          e.currentTarget.style.borderColor = 'rgba(56,189,248,.18)'
                          e.currentTarget.style.color = 'var(--color-text)'
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!active) {
                          e.currentTarget.style.borderColor = 'transparent'
                          e.currentTarget.style.color = 'var(--color-dim)'
                        }
                      }}
                    >
                      <span style={{ width: 18, display: 'grid', placeItems: 'center', color: active ? dotColor : 'currentColor' }}>
                        <Icon size={17} className="shrink-0" />
                      </span>
                      {!sidebarCollapsed && (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, width: '100%' }}>
                          <span>{label}</span>
                          <span style={{ fontSize: '.66em', color: active ? dotColor : 'rgba(148,163,184,.72)', fontWeight: 700 }}>
                            {shortLabel}
                          </span>
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
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
        lineHeight: 1.6,
      }}>
        {!sidebarCollapsed && (
          version ? (
            <div>
              <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>
                InfoHub {version.version !== 'dev' ? version.version : ''}
              </div>
              <div style={{ fontSize: '.9em', opacity: 0.7 }}>
                {version.commit} · {version.date || ''}
              </div>
            </div>
          ) : (
            'Info Hub'
          )
        )}
      </div>
    </aside>
  )
}

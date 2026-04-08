import { Sun, Moon, RefreshCw } from 'lucide-react'
import { useAppStore } from '../../stores/appStore'
import { useEffect, useState, useCallback } from 'react'

const SECTION_TITLES: Record<string, string> = {
  'ai-news': 'AI 新闻',
  'viral': '自媒体爆款',
  'trending': '热门话题',
  'article-gen': '一键写文',
  'fin-news': '财经新闻',
  'sectors': '热门板块',
  'zt-analysis': '涨停分析',
  'review-report': '复盘报告',
}

const DOT_COLORS: Record<string, string> = {
  'ai-news': 'var(--color-accent)',
  'viral': 'var(--color-red)',
  'trending': 'var(--color-gold)',
  'article-gen': 'var(--color-purple)',
  'fin-news': 'var(--color-green)',
  'sectors': 'var(--color-orange)',
  'zt-analysis': 'var(--color-red)',
  'review-report': 'var(--color-accent)',
}

export default function Header() {
  const { activeSection, theme, toggleTheme, triggerRefresh } = useAppStore()
  const [time, setTime] = useState('')
  const [spinning, setSpinning] = useState(false)

  // 时钟
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  // 早九晚九自动刷新
  useEffect(() => {
    let firedHours = new Set<string>()

    const check = () => {
      const now = new Date()
      const h = now.getHours()
      const dateKey = `${now.toDateString()}-${h}`
      if ((h === 9 || h === 21) && !firedHours.has(dateKey)) {
        firedHours.add(dateKey)
        triggerRefresh()
      }
    }

    // 每分钟检查一次
    const id = setInterval(check, 60_000)
    check() // 立即检查一次
    return () => clearInterval(id)
  }, [triggerRefresh])

  const handleRefresh = useCallback(() => {
    setSpinning(true)
    triggerRefresh()
    setTimeout(() => setSpinning(false), 800)
  }, [triggerRefresh])

  return (
    <header style={{
      height: 56,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      borderBottom: '1px solid var(--color-border)',
      background: 'var(--color-card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          display: 'inline-block',
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: DOT_COLORS[activeSection] || 'var(--color-accent)',
        }} />
        <h2 style={{ fontSize: '1.15em', fontWeight: 700, color: 'var(--color-text)' }}>
          {SECTION_TITLES[activeSection] || ''}
        </h2>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          fontFamily: 'monospace',
          fontSize: '.8em',
          color: 'var(--color-accent)',
          fontWeight: 700,
        }}>
          {time}
        </span>

        <button
          onClick={handleRefresh}
          title="刷新数据"
          style={{
            padding: 7,
            borderRadius: 8,
            border: `1px solid ${spinning ? 'var(--color-accent)' : 'var(--color-border)'}`,
            background: spinning ? 'rgba(56,189,248,.08)' : 'var(--color-card)',
            color: spinning ? 'var(--color-accent)' : 'var(--color-dim)',
            cursor: 'pointer',
            display: 'flex',
            transition: 'all .2s',
          }}
        >
          <RefreshCw
            size={15}
            style={{
              animation: spinning ? 'spin .8s linear' : 'none',
            }}
          />
        </button>

        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? '切换浅色' : '切换深色'}
          style={{
            padding: 7,
            borderRadius: 8,
            border: '1px solid var(--color-border)',
            background: 'var(--color-card)',
            color: 'var(--color-dim)',
            cursor: 'pointer',
            display: 'flex',
          }}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  )
}

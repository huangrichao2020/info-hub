import { Sun, Moon, RefreshCw, AlertCircle } from 'lucide-react'
import { useAppStore } from '../../stores/appStore'
import { useEffect, useRef, useState, useCallback } from 'react'
import { SECTION_META } from '../../config/sections'

// 刷新频率限制：5分钟内最多3次
const REFRESH_LIMIT_MS = 5 * 60 * 1000
const REFRESH_MAX_CLICKS = 3

export default function Header() {
  const { activeSection, theme, toggleTheme, triggerRefresh } = useAppStore()
  const [time, setTime] = useState('')
  const [spinning, setSpinning] = useState(false)
  const [rateLimited, setRateLimited] = useState(false)
  const [cooldownSec, setCooldownSec] = useState(0)
  const clickTimesRef = useRef<number[]>([])
  const meta = SECTION_META[activeSection]

  // 时钟
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  // 早九晚九自动刷新（不受频率限制）
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

    const id = setInterval(check, 60_000)
    check()
    return () => clearInterval(id)
  }, [triggerRefresh])

  // 冷却倒计时
  useEffect(() => {
    if (!rateLimited) return
    const oldest = clickTimesRef.current[0]
    if (!oldest) return
    const tick = () => {
      const remaining = Math.max(0, REFRESH_LIMIT_MS - (Date.now() - oldest))
      setCooldownSec(Math.ceil(remaining / 1000))
      if (remaining <= 0) {
        setRateLimited(false)
        clickTimesRef.current = clickTimesRef.current.filter(t => Date.now() - t < REFRESH_LIMIT_MS)
      }
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [rateLimited])

  const handleRefresh = useCallback(() => {
    if (rateLimited) return

    const now = Date.now()
    // 清理超过5分钟的旧记录
    clickTimesRef.current = clickTimesRef.current.filter(t => now - t < REFRESH_LIMIT_MS)

    if (clickTimesRef.current.length >= REFRESH_MAX_CLICKS) {
      setRateLimited(true)
      return
    }

    clickTimesRef.current.push(now)
    setSpinning(true)
    triggerRefresh()
    setTimeout(() => setSpinning(false), 800)
  }, [rateLimited, triggerRefresh])

  return (
    <header style={{
      minHeight: 64,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      borderBottom: '1px solid var(--color-border)',
      background: 'rgba(10,14,26,.88)',
      backdropFilter: 'blur(14px)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          display: 'inline-block',
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: meta?.dotColor || 'var(--color-accent)',
        }} />
        <div>
          <h2 style={{ fontSize: '1.08em', fontWeight: 800, color: 'var(--color-text)', letterSpacing: '-0.03em' }}>
            {meta?.label || ''}
          </h2>
          <div style={{ marginTop: 2, fontSize: '.74em', color: 'var(--color-dim)' }}>
            {meta?.description || ''}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          padding: '5px 10px',
          borderRadius: 999,
          border: '1px solid rgba(251,191,36,.18)',
          background: 'rgba(251,191,36,.08)',
          color: 'var(--color-gold)',
          fontSize: '.72em',
          fontWeight: 700,
        }}>
          方法论优先
        </span>
        <span style={{
          fontFamily: 'monospace',
          fontSize: '.8em',
          color: 'var(--color-accent)',
          fontWeight: 700,
        }}>
          {time}
        </span>

        {/* 刷新按钮 - 带频率限制 */}
        <button
          onClick={handleRefresh}
          title={rateLimited ? `频率限制：${cooldownSec}秒后可再次刷新` : '刷新数据'}
          style={{
            padding: 7,
            borderRadius: 8,
            border: `1px solid ${rateLimited ? 'rgba(239,68,68,.3)' : spinning ? 'var(--color-accent)' : 'var(--color-border)'}`,
            background: rateLimited ? 'rgba(239,68,68,.08)' : spinning ? 'rgba(56,189,248,.08)' : 'var(--color-card)',
            color: rateLimited ? 'var(--color-red)' : spinning ? 'var(--color-accent)' : 'var(--color-dim)',
            cursor: rateLimited ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            transition: 'all .2s',
          }}
        >
          {rateLimited ? (
            <span style={{ fontSize: '.7em', fontWeight: 600, whiteSpace: 'nowrap' }}>
              <AlertCircle size={13} /> {cooldownSec}s
            </span>
          ) : (
            <RefreshCw
              size={15}
              style={{
                animation: spinning ? 'spin .8s linear' : 'none',
              }}
            />
          )}
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

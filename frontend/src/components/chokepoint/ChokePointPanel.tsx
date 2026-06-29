import { AlertTriangle } from 'lucide-react'

/**
 * Serenity 卡脖子产业链分析面板
 * 通过 iframe 嵌入静态 HTML 索引页（/chokepoint/index.html）
 * 静态资源在 frontend/public/chokepoint/ 下，由 vite 直接服务
 */
export default function ChokePointPanel() {
  return (
    <div style={{ width: '100%', height: 'calc(100vh - 60px)', overflow: 'hidden' }}>
      <iframe
        src="/chokepoint/index.html"
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          background: '#0a0e1a',
        }}
        title="Serenity 卡脖子产业链分析 · 29 只 A 股标的"
        loading="lazy"
      />
    </div>
  )
}
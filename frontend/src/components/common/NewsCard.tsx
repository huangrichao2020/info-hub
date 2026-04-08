import { motion } from 'framer-motion'
import { ExternalLink } from 'lucide-react'

interface Props {
  title: string
  summary?: string
  source?: string
  time?: string
  url?: string
  tags?: string[]
  index?: number
}

const SOURCE_STYLES: Record<string, { bg: string; color: string }> = {
  eastmoney: { bg: 'rgba(251,146,60,.12)', color: 'var(--color-orange)' },
  sina: { bg: 'rgba(56,189,248,.12)', color: 'var(--color-accent)' },
  cls: { bg: 'rgba(74,222,128,.12)', color: 'var(--color-green)' },
  ths: { bg: 'rgba(251,191,36,.12)', color: 'var(--color-gold)' },
  'google-ai': { bg: 'rgba(56,189,248,.12)', color: 'var(--color-accent)' },
  '36kr': { bg: 'rgba(167,139,250,.12)', color: 'var(--color-purple)' },
}

export default function NewsCard({ title, summary, source, time, url, tags, index = 0 }: Props) {
  const srcStyle = SOURCE_STYLES[source || ''] || { bg: 'rgba(56,189,248,.12)', color: 'var(--color-accent)' }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.25 }}
      style={{
        background: 'var(--color-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 12,
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        cursor: url ? 'pointer' : 'default',
        transition: 'border-color .2s',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
      onClick={() => url && window.open(url, '_blank')}
    >
      {/* Source + Time row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {source && (
          <span style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: 999,
            fontSize: '.7em',
            fontWeight: 600,
            background: srcStyle.bg,
            color: srcStyle.color,
          }}>
            {source}
          </span>
        )}
        {tags?.map((tag) => (
          <span key={tag} style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: 999,
            fontSize: '.68em',
            fontWeight: 600,
            background: 'rgba(167,139,250,.12)',
            color: 'var(--color-purple)',
          }}>
            {tag}
          </span>
        ))}
        {time && (
          <span style={{ fontSize: '.72em', color: 'var(--color-dim)', marginLeft: 'auto' }}>
            {time}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 style={{
        fontSize: '.88em',
        fontWeight: 600,
        lineHeight: 1.55,
        color: 'var(--color-text)',
        margin: 0,
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {title}
      </h3>

      {/* Summary */}
      {summary && (
        <p style={{
          fontSize: '.82em',
          lineHeight: 1.6,
          color: 'var(--color-dim)',
          margin: 0,
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}>
          {summary}
        </p>
      )}

      {/* External link */}
      {url && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <ExternalLink size={12} style={{ color: 'var(--color-dim)' }} />
        </div>
      )}
    </motion.div>
  )
}

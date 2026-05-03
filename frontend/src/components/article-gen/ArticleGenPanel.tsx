import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { useStreamResponse } from '../../hooks/useStreamResponse'

export default function ArticleGenPanel() {
  const [topic, setTopic] = useState('')
  const [platform, setPlatform] = useState<'wechat' | 'toutiao' | 'zhihu'>('wechat')
  const [reference, setReference] = useState('')
  const { content, loading, startStream, reset } = useStreamResponse()

  const handleGenerate = () => {
    if (!topic.trim()) return
    startStream('/info-hub/api/article/generate', {
      topic,
      platform,
      reference_material: reference,
      word_count: platform === 'zhihu' ? 3000 : 2000,
    })
  }

  const PLATFORMS = [
    { key: 'wechat' as const, label: '微信公众号' },
    { key: 'toutiao' as const, label: '今日头条' },
    { key: 'zhihu' as const, label: '知乎' },
  ]

  const inputBase: React.CSSProperties = {
    width: '100%',
    background: 'var(--color-card)',
    border: '1px solid var(--color-border)',
    borderRadius: 10,
    padding: '8px 14px',
    fontSize: '.84em',
    color: 'var(--color-text)',
    outline: 'none',
    resize: 'none',
    transition: 'border-color .15s',
    fontFamily: 'inherit',
  }

  return (
    <div style={{ display: 'flex', gap: 24, height: 'calc(100vh - 8rem)' }}>
      {/* Left: Input */}
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}
      >
        <div>
          <label style={{ fontSize: '.72em', color: 'var(--color-dim)', marginBottom: 4, display: 'block' }}>
            目标平台
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            {PLATFORMS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setPlatform(key)}
                style={{
                  flex: 1,
                  padding: '8px 0',
                  borderRadius: 10,
                  fontSize: '.82em',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all .15s',
                  border: platform === key
                    ? '1px solid var(--color-accent)'
                    : '1px solid var(--color-border)',
                  background: platform === key
                    ? 'rgba(56,189,248,.15)'
                    : 'var(--color-card)',
                  color: platform === key
                    ? 'var(--color-accent)'
                    : 'var(--color-dim)',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label style={{ fontSize: '.72em', color: 'var(--color-dim)', marginBottom: 4, display: 'block' }}>
            文章话题
          </label>
          <textarea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="输入你想写的话题..."
            style={{ ...inputBase, height: 96 }}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
        </div>

        <div>
          <label style={{ fontSize: '.72em', color: 'var(--color-dim)', marginBottom: 4, display: 'block' }}>
            参考素材（可选）
          </label>
          <textarea
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="粘贴参考资料、数据、新闻..."
            style={{ ...inputBase, height: 128 }}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
          style={{
            width: '100%',
            padding: '10px 0',
            borderRadius: 10,
            border: '1px solid var(--color-accent)',
            background: loading || !topic.trim() ? 'rgba(56,189,248,.04)' : 'rgba(56,189,248,.12)',
            color: 'var(--color-accent)',
            fontSize: '.84em',
            fontWeight: 600,
            cursor: loading || !topic.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !topic.trim() ? 0.5 : 1,
            transition: 'all .15s',
          }}
        >
          {loading ? '生成中...' : '一键生成'}
        </button>

        {content && (
          <button
            onClick={reset}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '.72em',
              color: 'var(--color-dim)',
              cursor: 'pointer',
              textAlign: 'left',
              padding: 0,
              transition: 'color .15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-accent)' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-dim)' }}
          >
            清空重写
          </button>
        )}
      </motion.div>

      {/* Right: Preview */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1 }}
        style={{
          flex: 1,
          background: 'var(--color-card)',
          borderRadius: 12,
          border: '1px solid var(--color-border)',
          padding: 24,
          overflowY: 'auto',
        }}
      >
        {content ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--color-dim)',
            fontSize: '.88em',
          }}>
            生成的文章将在这里显示
          </div>
        )}
        {loading && (
          <span style={{
            display: 'inline-block',
            width: 2,
            height: 16,
            background: 'var(--color-accent)',
            marginLeft: 2,
            animation: 'pulse 1s ease-in-out infinite',
          }} />
        )}
      </motion.div>
    </div>
  )
}

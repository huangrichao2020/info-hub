import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles, Trash2, MessageSquare, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useAssistant } from '../../hooks/useAssistant'

export default function AssistantPanel() {
  const { messages, loading, error, sendMessage, clearHistory, suggestions } = useAssistant()
  const [input, setInput] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || loading) return
    sendMessage(input.trim())
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestionClick = (message: string) => {
    sendMessage(message)
  }

  if (collapsed) {
    return (
      <div style={{
        width: 44,
        minWidth: 44,
        borderLeft: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '12px 0',
        gap: 8,
      }}>
        <button
          onClick={() => setCollapsed(false)}
          title="打开复盘大师"
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            border: '1px solid var(--color-border)',
            background: 'var(--color-accent-dim)',
            color: 'var(--color-accent)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Sparkles size={18} />
        </button>
      </div>
    )
  }

  return (
    <div style={{
      width: 500,
      minWidth: 500,
      borderLeft: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={16} style={{ color: 'var(--color-accent)' }} />
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text)' }}>
            复盘大师
          </span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={clearHistory}
            title="清空对话"
            style={{
              padding: 4,
              borderRadius: 6,
              border: 'none',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
            }}
          >
            <Trash2 size={14} />
          </button>
          <button
            onClick={() => setCollapsed(true)}
            title="最小化"
            style={{
              padding: 4,
              borderRadius: 6,
              border: 'none',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
            }}
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
        <AnimatePresence>
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-secondary)' }}
            >
              <MessageSquare size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
              <div style={{ fontSize: 'var(--text-sm)', marginBottom: 20 }}>
                我是你的 A 股交易助手
              </div>
              {/* Suggestions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestionClick(s.message)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 10,
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      fontSize: 'var(--text-xs)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'all .15s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-accent)'
                      e.currentTarget.style.background = 'var(--color-accent-dim)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-border)'
                      e.currentTarget.style.background = 'var(--color-surface)'
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              marginBottom: 12,
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              maxWidth: '85%',
              padding: '10px 14px',
              borderRadius: 12,
              fontSize: 'var(--text-xs)',
              lineHeight: 1.6,
              ...(msg.role === 'user'
                ? {
                    background: 'var(--color-accent)',
                    color: '#0a0e1a',
                    borderBottomRightRadius: 4,
                  }
                : {
                    background: 'rgba(15,23,42,.6)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                    borderBottomLeftRadius: 4,
                  }
              ),
            }}>
              {msg.role === 'assistant' ? (
                <ReactMarkdown
                  components={{
                    p: ({ children }) => <p style={{ margin: '3px 0', lineHeight: 1.5 }}>{children}</p>,
                    ul: ({ children }) => <ul style={{ margin: '3px 0', paddingLeft: 16 }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ margin: '3px 0', paddingLeft: 16 }}>{children}</ol>,
                    li: ({ children }) => <li style={{ margin: '1px 0', fontSize: 'var(--text-xs)' }}>{children}</li>,
                    h1: ({ children }) => <h1 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, margin: '6px 0 2px' }}>{children}</h1>,
                    h2: ({ children }) => <h2 style={{ fontSize: 'var(--text-xs)', fontWeight: 700, margin: '6px 0 2px' }}>{children}</h2>,
                    h3: ({ children }) => <h3 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, margin: '4px 0 2px' }}>{children}</h3>,
                    strong: ({ children }) => <strong style={{ fontWeight: 700, color: msg.role === 'assistant' ? 'var(--color-accent)' : 'inherit' }}>{children}</strong>,
                    em: ({ children }) => <em style={{ fontStyle: 'italic', opacity: 0.8 }}>{children}</em>,
                    code: ({ children }) => (
                      <code style={{ padding: '1px 5px', borderRadius: 4, background: 'rgba(148,163,184,.12)', fontSize: '.85em', fontFamily: 'monospace' }}>
                        {children}
                      </code>
                    ),
                    blockquote: ({ children }) => (
                      <blockquote style={{ margin: '4px 0', paddingLeft: 10, borderLeft: '2px solid var(--color-accent)', opacity: 0.85 }}>
                        {children}
                      </blockquote>
                    ),
                    hr: () => <hr style={{ border: 'none', borderTop: '1px solid var(--color-border)', margin: '6px 0' }} />,
                    a: ({ href, children }) => (
                      <a href={href} target="_blank" rel="noopener" style={{ color: 'var(--color-accent)', textDecoration: 'underline' }}>
                        {children}
                      </a>
                    ),
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              ) : (
                msg.content
              )}
              {msg.role === 'assistant' && i === messages.length - 1 && loading && (
                <span style={{
                  display: 'inline-block',
                  width: 2,
                  height: 14,
                  background: 'var(--color-accent)',
                  marginLeft: 2,
                  animation: 'pulse 1s ease-in-out infinite',
                }} />
              )}
            </div>
          </motion.div>
        ))}

        {error && (
          <div style={{
            padding: '8px 12px',
            borderRadius: 10,
            background: 'var(--color-red-dim)',
            border: '1px solid rgba(239,68,68,.2)',
            color: 'var(--color-red)',
            fontSize: 'var(--text-xs)',
            marginBottom: 12,
          }}>
            {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--color-border)',
      }}>
        <div style={{
          display: 'flex',
          gap: 8,
          alignItems: 'flex-end',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 12,
          padding: '8px 12px',
        }}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px'
            }}
            onKeyDown={handleKeyDown}
            placeholder="输入问题，Enter 发送..."
            rows={1}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--color-text)',
              fontSize: 'var(--text-xs)',
              resize: 'none',
              lineHeight: 1.5,
              maxHeight: 100,
            }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              border: 'none',
              background: loading || !input.trim() ? 'var(--color-border)' : 'var(--color-accent)',
              color: loading || !input.trim() ? 'var(--color-dim)' : '#0a0e1a',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Send size={14} />
          </button>
        </div>
        <div style={{ marginTop: 6, fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', textAlign: 'center' }}>
          基于 uwillberich 方法论 · 数据仅供参考
        </div>
      </div>
    </div>
  )
}

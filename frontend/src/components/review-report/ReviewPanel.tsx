import { useState } from 'react'
import { motion } from 'framer-motion'
import { Plus, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useStreamResponse } from '../../hooks/useStreamResponse'
import type { PortfolioStock } from '../../types'

export default function ReviewPanel() {
  const [portfolio, setPortfolio] = useState<PortfolioStock[]>([])
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [shares, setShares] = useState('')
  const [costPrice, setCostPrice] = useState('')
  const { content, loading, startStream, reset } = useStreamResponse()

  const addStock = () => {
    if (!code || !name) return
    setPortfolio([...portfolio, {
      code: code.trim(),
      name: name.trim(),
      shares: parseInt(shares) || 100,
      cost_price: parseFloat(costPrice) || 0,
    }])
    setCode('')
    setName('')
    setShares('')
    setCostPrice('')
  }

  const removeStock = (i: number) => {
    setPortfolio(portfolio.filter((_, idx) => idx !== i))
  }

  const handleGenerate = () => {
    if (portfolio.length === 0) return
    startStream('/api/review/generate', { portfolio })
  }

  const inputStyle: React.CSSProperties = {
    background: 'var(--color-card)',
    border: '1px solid var(--color-border)',
    borderRadius: 10,
    padding: '8px 14px',
    fontSize: '.84em',
    color: 'var(--color-text)',
    outline: 'none',
    transition: 'border-color .15s',
    fontFamily: 'inherit',
    width: '100%',
    boxSizing: 'border-box',
  }

  return (
    <div style={{ display: 'flex', gap: 24, height: 'calc(100vh - 8rem)' }}>
      {/* Left: Portfolio Input */}
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}
      >
        <div style={{ fontSize: '.72em', color: 'var(--color-dim)' }}>添加持仓股票</div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="股票代码"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="股票名称"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          <input
            value={shares}
            onChange={(e) => setShares(e.target.value)}
            placeholder="持仓数量"
            type="number"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
          <input
            value={costPrice}
            onChange={(e) => setCostPrice(e.target.value)}
            placeholder="成本价"
            type="number"
            step="0.01"
            style={inputStyle}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
          />
        </div>

        <button
          onClick={addStock}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
            padding: '8px 0',
            border: '1px dashed var(--color-border)',
            borderRadius: 10,
            fontSize: '.82em',
            color: 'var(--color-dim)',
            background: 'transparent',
            cursor: 'pointer',
            transition: 'all .15s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--color-accent)'
            e.currentTarget.style.color = 'var(--color-accent)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--color-border)'
            e.currentTarget.style.color = 'var(--color-dim)'
          }}
        >
          <Plus size={14} /> 添加
        </button>

        {/* Portfolio List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {portfolio.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'var(--color-card)',
                borderRadius: 12,
                border: '1px solid var(--color-border)',
                transition: 'border-color .2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)' }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
            >
              <div>
                <span style={{ fontSize: '.84em', color: 'var(--color-text)' }}>{s.name}</span>
                <span style={{ marginLeft: 6, fontSize: '.72em', color: 'var(--color-dim)' }}>{s.code}</span>
                <div style={{ fontSize: '.68em', color: 'var(--color-dim)', marginTop: 2 }}>
                  {s.shares}股 @ {s.cost_price}
                </div>
              </div>
              <button
                onClick={() => removeStock(i)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-dim)',
                  cursor: 'pointer',
                  padding: 4,
                  transition: 'color .15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-red)' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-dim)' }}
              >
                <Trash2 size={14} />
              </button>
            </motion.div>
          ))}
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || portfolio.length === 0}
          style={{
            width: '100%',
            padding: '10px 0',
            borderRadius: 10,
            border: '1px solid var(--color-accent)',
            background: loading || portfolio.length === 0 ? 'rgba(56,189,248,.04)' : 'rgba(56,189,248,.12)',
            color: 'var(--color-accent)',
            fontSize: '.84em',
            fontWeight: 600,
            cursor: loading || portfolio.length === 0 ? 'not-allowed' : 'pointer',
            opacity: loading || portfolio.length === 0 ? 0.5 : 1,
            transition: 'all .15s',
          }}
        >
          {loading ? '生成中...' : '一键生成复盘报告'}
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
            清空重新生成
          </button>
        )}
      </motion.div>

      {/* Right: Report */}
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
            添加持仓后点击生成，复盘报告将在这里显示
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

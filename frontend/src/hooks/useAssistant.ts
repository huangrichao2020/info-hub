import { useCallback, useEffect, useRef, useState } from 'react'

interface AssistantMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

interface UseAssistantReturn {
  messages: AssistantMessage[]
  loading: boolean
  error: string | null
  sendMessage: (content: string) => void
  clearHistory: () => void
  loadHistory: () => void
  suggestions: { label: string; message: string }[]
  loadSuggestions: () => void
}

export function useAssistant(): UseAssistantReturn {
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<{ label: string; message: string }[]>([])
  const eventSourceRef = useRef<EventSource | null>(null)

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch('/info-hub/api/assistant/history?limit=30')
      const data = await res.json()
      const items: AssistantMessage[] = (data.items || []).map((h: any) => ({
        role: h.role as 'user' | 'assistant',
        content: h.content,
        timestamp: h.created_at,
      }))
      setMessages(items)
    } catch {
      // ignore
    }
  }, [])

  const loadSuggestions = useCallback(async () => {
    try {
      const res = await fetch('/info-hub/api/assistant/suggest')
      const data = await res.json()
      setSuggestions(data.suggestions || [])
    } catch {
      // ignore
    }
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!content.trim() || loading) return

    // 立即显示用户消息
    const userMsg: AssistantMessage = { role: 'user', content: content.trim() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    setError(null)

    // 创建占位助手消息
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    // 启用 ReAct Agent 模式，让 LLM 可以使用工具（搜索、行情查询等）
    const body = JSON.stringify({ message: content.trim(), use_react: true })

    fetch('/info-hub/api/assistant/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error('请求失败')
        const data = await res.json()
        const requestId = data.request_id

        if (!requestId) {
          // 如果不是流式，直接解析
          return
        }

        // SSE 流式接收
        const es = new EventSource(`/info-hub/api/assistant/stream/${requestId}`)
        eventSourceRef.current = es

        es.onmessage = (event) => {
          try {
            const chunk = JSON.parse(event.data)
            if (chunk.content) {
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last && last.role === 'assistant') {
                  last.content += chunk.content
                }
                return updated
              })
            }
            if (chunk.done) {
              es.close()
              setLoading(false)
              loadSuggestions()
            }
            if (chunk.error) {
              setError(chunk.error)
              es.close()
              setLoading(false)
            }
          } catch {
            // ignore parse errors
          }
        }

        es.onerror = () => {
          es.close()
          setLoading(false)
        }
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [loading, loadSuggestions])

  const clearHistory = useCallback(async () => {
    await fetch('/info-hub/api/assistant/history', { method: 'DELETE' })
    setMessages([])
    loadSuggestions()
  }, [loadSuggestions])

  useEffect(() => {
    loadHistory()
    loadSuggestions()
    return () => {
      eventSourceRef.current?.close()
    }
  }, [loadHistory, loadSuggestions])

  return { messages, loading, error, sendMessage, clearHistory, loadHistory, suggestions, loadSuggestions }
}


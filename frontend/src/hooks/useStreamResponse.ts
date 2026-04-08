import { useState, useCallback } from 'react'

export function useStreamResponse() {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)

  const startStream = useCallback(async (url: string, body: unknown) => {
    setContent('')
    setLoading(true)

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) return

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.content) {
              setContent((prev) => prev + data.content)
            }
            if (data.done) {
              setLoading(false)
            }
          } catch {
            // skip
          }
        }
      }
    } catch (err) {
      console.error('Stream error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setContent('')
    setLoading(false)
  }, [])

  return { content, loading, startStream, reset }
}

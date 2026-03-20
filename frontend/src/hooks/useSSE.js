/**
 * useSSE — Custom hook for Server-Sent Events with the BI agent backend.
 * Handles fetch-based streaming (needed for POST + SSE) and parses events.
 */
import { useCallback, useRef, useState } from 'react'

export function useSSE() {
  const [isStreaming, setIsStreaming]   = useState(false)
  const [error, setError]              = useState(null)
  const abortRef                        = useRef(null)

  const startStream = useCallback(async (query, sessionId, callbacks = {}) => {
    const { onRouter, onToken, onToolStart, onToolEnd, onDone, onError } = callbacks

    // Abort previous stream if still running
    if (abortRef.current) abortRef.current.abort()
    abortRef.current = new AbortController()
    setIsStreaming(true)
    setError(null)

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`HTTP ${response.status}: ${text}`)
      }

      // Read SSE stream line by line
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const event = JSON.parse(raw)
            switch (event.type) {
              case 'router':   onRouter?.(event);    break
              case 'token':    onToken?.(event);     break
              case 'tool_start': onToolStart?.(event); break
              case 'tool_end':   onToolEnd?.(event);   break
              case 'done':     onDone?.(event);      break
              case 'error':    onError?.(event);     break
              default: break
            }
          } catch {
            // ignore malformed events
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message)
        onError?.({ type: 'error', message: err.message })
      }
    } finally {
      setIsStreaming(false)
    }
  }, [])

  const stopStream = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return { isStreaming, error, startStream, stopStream }
}

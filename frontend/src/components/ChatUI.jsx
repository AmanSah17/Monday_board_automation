/**
 * ChatUI — Streaming chat interface with message history.
 * Left panel of the three-panel layout.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { useSSE } from '../hooks/useSSE'

const SUGGESTED = [
  'What boards do I have?',
  'Show me the pipeline health for my CRM board',
  'Count items by status in the Work Order Tracker',
  'Find items containing "urgent"',
]

function TypingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 3, alignItems: 'center', padding: '2px 0' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 5, height: 5, borderRadius: '50%',
          background: 'var(--accent-blue)',
          animation: `pulse 1.1s ease-in-out ${i * 0.18}s infinite`,
        }} />
      ))}
    </span>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className="fade-in" style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 10, marginBottom: 16, alignItems: 'flex-start',
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 700,
        background: isUser
          ? 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))'
          : 'linear-gradient(135deg, var(--accent-green), #059669)',
        boxShadow: isUser ? 'var(--shadow-glow-blue)' : 'var(--shadow-glow-green)',
      }}>
        {isUser ? 'U' : 'AI'}
      </div>

      {/* Bubble */}
      <div style={{
        maxWidth: '80%',
        background: isUser ? 'var(--accent-blue-dim)' : 'var(--bg-glass-light)',
        border: `1px solid ${isUser ? 'rgba(59,130,246,0.3)' : 'var(--border)'}`,
        borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
        padding: '10px 14px',
        fontSize: 14,
        lineHeight: 1.6,
      }}>
        {isUser ? (
          <span style={{ color: 'var(--text-primary)' }}>{msg.content}</span>
        ) : msg.streaming ? (
          <>
            {msg.content ? (
              <div className="markdown" style={{ color: 'var(--text-secondary)' }}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            ) : null}
            <TypingDots />
          </>
        ) : (
          <div className="markdown">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatUI({ sessionId, onTraceEvent }) {
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [streamingIdx, setIdx]      = useState(null)
  const endRef                      = useRef(null)
  const textareaRef                 = useRef(null)
  const { isStreaming, startStream, stopStream } = useSSE()

  // Auto-scroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addAssistantChunk = useCallback((chunk) => {
    setMessages(prev => prev.map((m, i) =>
      i === prev.length - 1 && m.role === 'assistant'
        ? { ...m, content: m.content + chunk, streaming: true }
        : m
    ))
  }, [])

  const finalizeAssistant = useCallback((answer) => {
    setMessages(prev => prev.map((m, i) =>
      i === prev.length - 1 && m.role === 'assistant'
        ? { ...m, content: answer || m.content, streaming: false }
        : m
    ))
    setIdx(null)
  }, [])

  const sendQuery = useCallback(async (query) => {
    if (!query.trim() || isStreaming) return
    setInput('')

    // Add user bubble
    setMessages(prev => [...prev, { role: 'user', content: query }])
    // Add empty assistant bubble
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    await startStream(query, sessionId, {
      onRouter:    (e) => onTraceEvent?.({ ...e, ts: Date.now() }),
      onToken:     (e) => addAssistantChunk(e.content),
      onToolStart: (e) => onTraceEvent?.({ ...e, ts: Date.now() }),
      onToolEnd:   (e) => onTraceEvent?.({ ...e, ts: Date.now() }),
      onDone:      (e) => { finalizeAssistant(e.answer); onTraceEvent?.({ ...e, ts: Date.now() }) },
      onError:     (e) => {
        finalizeAssistant(`⚠️ Error: ${e.message}`)
        onTraceEvent?.({ ...e, ts: Date.now() })
      },
    })
  }, [isStreaming, sessionId, startStream, addAssistantChunk, finalizeAssistant, onTraceEvent])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(input) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0 }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
        }}>🤖</div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>BI Agent Chat</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <div className="pulse-dot" />
            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
              {isStreaming ? 'Thinking…' : 'Ready'}
            </span>
          </div>
        </div>
        {isStreaming && (
          <button className="btn btn-ghost" onClick={stopStream}
            style={{ marginLeft: 'auto', fontSize: 12, padding: '5px 10px' }}>
            ⏹ Stop
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 16px' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>
              Monday.com BI Agent
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 24 }}>
              Ask anything about your boards, pipelines, and data
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              {SUGGESTED.map(s => (
                <button key={s} className="btn btn-ghost"
                  style={{ fontSize: 12, padding: '6px 12px' }}
                  onClick={() => sendQuery(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => <Message key={i} msg={msg} />)
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 16px', borderTop: '1px solid var(--border)',
        display: 'flex', gap: 8, alignItems: 'flex-end',
      }}>
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your boards, pipeline, metrics…"
          disabled={isStreaming}
          style={{
            flex: 1, resize: 'none', background: 'var(--bg-glass-light)',
            border: input ? '1px solid var(--border-accent)' : '1px solid var(--border)',
            borderRadius: var => '10px',
            padding: '10px 14px', color: 'var(--text-primary)',
            fontFamily: 'var(--font-sans)', fontSize: 14, lineHeight: 1.5,
            outline: 'none', transition: 'var(--transition)',
            maxHeight: 120, overflowY: 'auto',
          }}
        />
        <button className="btn btn-primary"
          onClick={() => sendQuery(input)}
          disabled={!input.trim() || isStreaming}
          style={{ height: 40, paddingInline: 14 }}>
          {isStreaming ? <span className="spinner" style={{ width: 14, height: 14 }} /> : '↑'}
        </button>
      </div>
    </div>
  )
}

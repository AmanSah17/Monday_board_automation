/**
 * TracePanel — Live SSE tool-call event feed (middle panel).
 * Shows each agent step: router intent, tool_start, tool_end, done, error.
 */
import { useEffect, useRef } from 'react'

const EVENT_CONFIG = {
  router:     { icon: '🔀', label: 'Intent Router',   color: 'var(--accent-orange)', bg: 'var(--accent-orange-dim)' },
  tool_start: { icon: '⚡', label: 'Tool Call',        color: 'var(--accent-blue)',   bg: 'var(--accent-blue-dim)' },
  tool_end:   { icon: '✅', label: 'Tool Result',      color: 'var(--accent-green)',  bg: 'var(--accent-green-dim)' },
  done:       { icon: '🏁', label: 'Final Answer',     color: 'var(--accent-purple)', bg: 'var(--accent-purple-dim)' },
  error:      { icon: '❌', label: 'Error',            color: 'var(--accent-red)',    bg: 'rgba(239,68,68,0.1)' },
  token:      { icon: '💬', label: 'Streaming',        color: 'var(--text-muted)',    bg: 'transparent' },
}

function TraceEvent({ event, index }) {
  const cfg = EVENT_CONFIG[event.type] || EVENT_CONFIG.token
  if (event.type === 'token') return null  // skip individual token events

  const ts = event.ts ? new Date(event.ts).toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
  }) : ''

  return (
    <div className="fade-in" style={{
      margin: '6px 0', padding: '10px 12px',
      background: cfg.bg, border: `1px solid ${cfg.color}22`,
      borderLeft: `3px solid ${cfg.color}`,
      borderRadius: var => '8px',
      fontSize: 12,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 14 }}>{cfg.icon}</span>
        <span style={{ color: cfg.color, fontWeight: 600 }}>{cfg.label}</span>
        {event.tool && (
          <code style={{
            background: 'rgba(255,255,255,0.08)', color: 'var(--text-code)',
            padding: '1px 6px', borderRadius: 4, fontSize: 11,
          }}>{event.tool}</code>
        )}
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {ts}
        </span>
      </div>

      {/* Event-specific detail */}
      {event.type === 'router' && (
        <div style={{ color: 'var(--text-secondary)', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <span>Intent: <strong style={{ color: 'var(--accent-orange)' }}>{event.intent}</strong></span>
          <span>Confidence: <strong>{Math.round((event.confidence || 0) * 100)}%</strong></span>
        </div>
      )}

      {event.type === 'tool_start' && event.input && (
        <pre style={{
          background: 'rgba(0,0,0,0.3)', borderRadius: 6, padding: '6px 8px',
          margin: '4px 0 0', fontSize: 11, overflowX: 'auto',
          color: 'var(--text-secondary)', border: '1px solid var(--border)',
          maxHeight: 100,
        }}>
          {typeof event.input === 'string' ? event.input : JSON.stringify(event.input, null, 2)}
        </pre>
      )}

      {event.type === 'tool_end' && event.output && (
        <pre style={{
          background: 'rgba(0,0,0,0.3)', borderRadius: 6, padding: '6px 8px',
          margin: '4px 0 0', fontSize: 11, overflowX: 'auto',
          color: 'var(--text-secondary)', border: '1px solid var(--border)',
          maxHeight: 120, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {event.output.slice(0, 800)}{event.output.length > 800 ? '\n… (truncated)' : ''}
        </pre>
      )}

      {event.type === 'done' && event.answer && (
        <div style={{
          color: 'var(--text-secondary)', marginTop: 4, fontSize: 12,
          maxHeight: 80, overflowY: 'auto', lineHeight: 1.5,
        }}>
          {event.answer.slice(0, 200)}{event.answer.length > 200 ? '…' : ''}
        </div>
      )}

      {event.type === 'error' && (
        <div style={{ color: 'var(--accent-red)', marginTop: 4, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          {event.message}
        </div>
      )}
    </div>
  )
}

export default function TracePanel({ events = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  const visible = events.filter(e => e.type !== 'token')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
        }}>🔍</div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Agent Trace</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
            Live tool-call feed
          </div>
        </div>
        {visible.length > 0 && (
          <span className="badge badge-orange" style={{ marginLeft: 'auto' }}>
            {visible.length}
          </span>
        )}
      </div>

      {/* Legend */}
      <div style={{
        padding: '8px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', gap: 10, flexWrap: 'wrap',
      }}>
        {Object.entries(EVENT_CONFIG).filter(([k]) => k !== 'token').map(([key, cfg]) => (
          <span key={key} style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 10, color: 'var(--text-muted)',
          }}>
            <span>{cfg.icon}</span>
            <span>{cfg.label}</span>
          </span>
        ))}
      </div>

      {/* Events */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {visible.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', gap: 10,
            color: 'var(--text-muted)',
          }}>
            <span style={{ fontSize: 32 }}>⚡</span>
            <p style={{ fontSize: 12, textAlign: 'center' }}>
              Trace events will appear here<br />when you send a query
            </p>
          </div>
        ) : (
          <>
            {visible.map((e, i) => <TraceEvent key={i} event={e} index={i} />)}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  )
}

/**
 * App.jsx — Three-panel layout: Chat | Trace | Board Explorer
 * Responsive: tabs on mobile, side-by-side on desktop.
 */
import { useState, useCallback, useRef } from 'react'
import ChatUI from './components/ChatUI'
import TracePanel from './components/TracePanel'
import BoardExplorer from './components/BoardExplorer'

const PANELS = [
  { id: 'chat',  label: 'Chat',    icon: '💬' },
  { id: 'trace', label: 'Trace',   icon: '🔍' },
  { id: 'board', label: 'Boards',  icon: '📋' },
]

// Stable session ID for the browser session
const SESSION_ID = `browser-${Date.now().toString(36)}`

export default function App() {
  const [traceEvents, setTraceEvents] = useState([])
  const [activePanel, setPanel]       = useState('chat')
  const [newTraceCount, setNewTrace]  = useState(0)

  const handleTraceEvent = useCallback((event) => {
    setTraceEvents(prev => [...prev.slice(-200), event])  // keep last 200
    if (event.type !== 'token') {
      setNewTrace(n => n + 1)
    }
  }, [])

  const clearTrace = () => {
    setTraceEvents([])
    setNewTrace(0)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* ── Top nav bar ── */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', height: 52,
        background: 'rgba(7,9,15,0.9)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0, zIndex: 10,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #10b981 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15,
            boxShadow: 'var(--shadow-glow-blue)',
          }}>📊</div>
          <div>
            <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: '-0.01em' }}>Monday</span>
            <span style={{
              fontWeight: 400, fontSize: 14,
              background: 'linear-gradient(90deg, var(--accent-blue), var(--accent-purple))',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>&nbsp;BI Agent</span>
          </div>
        </div>

        {/* Mobile tab nav */}
        <div style={{
          display: 'flex', gap: 4,
        }}>
          {PANELS.map(p => (
            <button key={p.id} className="btn btn-ghost"
              onClick={() => { setPanel(p.id); if (p.id === 'trace') setNewTrace(0) }}
              style={{
                padding: '5px 12px', fontSize: 12,
                background: activePanel === p.id
                  ? 'linear-gradient(135deg, var(--accent-blue-dim), var(--accent-purple-dim))'
                  : 'transparent',
                borderColor: activePanel === p.id ? 'var(--border-accent)' : 'transparent',
                position: 'relative',
              }}>
              <span>{p.icon}</span>
              <span style={{ marginLeft: 4 }}>{p.label}</span>
              {p.id === 'trace' && newTraceCount > 0 && activePanel !== 'trace' && (
                <span style={{
                  position: 'absolute', top: -4, right: -4,
                  background: 'var(--accent-red)', color: '#fff',
                  fontSize: 9, fontWeight: 700, borderRadius: '99px',
                  padding: '1px 5px', minWidth: 16, textAlign: 'center',
                }}>
                  {newTraceCount > 99 ? '99+' : newTraceCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Right side */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {traceEvents.length > 0 && (
            <button className="btn btn-ghost" onClick={clearTrace}
              style={{ fontSize: 11, padding: '4px 10px' }}>
              Clear trace
            </button>
          )}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'var(--bg-glass-light)', padding: '4px 10px',
            borderRadius: 99, border: '1px solid var(--border)',
          }}>
            <div className="pulse-dot" />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Live
            </span>
          </div>
        </div>
      </header>

      {/* ── Three-panel layout ── */}
      <main style={{ flex: 1, display: 'flex', overflow: 'hidden', gap: 0 }}>

        {/* --- Chat panel --- */}
        <div className="glass" style={{
          flex: activePanel === 'chat' ? 1 : 0,
          minWidth: activePanel === 'chat' ? 300 : 0,
          display: 'flex', flexDirection: 'column',
          borderRadius: 0,  borderTop: 'none',
          borderLeft: 'none', borderBottom: 'none',
          overflow: 'hidden',
          transition: 'flex 0.3s ease',
          // Show on desktop always, show on mobile only when active
        }}>
          <ChatUI sessionId={SESSION_ID} onTraceEvent={handleTraceEvent} />
        </div>

        {/* --- Desktop-only separator --- */}
        <div style={{
          width: 1, background: 'var(--border)', flexShrink: 0,
        }} />

        {/* --- Trace panel --- */}
        <div className="glass" style={{
          width: 360, minWidth: 300, flexShrink: 0,
          display: activePanel !== 'chat' && activePanel !== 'board' ? 'flex' : 'flex',
          flexDirection: 'column', borderRadius: 0,
          borderTop: 'none', borderBottom: 'none',
          overflow: 'hidden',
          // On mobile, hide non-active panels
        }}>
          <TracePanel events={traceEvents} />
        </div>

        {/* --- Separator --- */}
        <div style={{ width: 1, background: 'var(--border)', flexShrink: 0 }} />

        {/* --- Board Explorer panel --- */}
        <div className="glass" style={{
          width: 420, minWidth: 300, flexShrink: 0,
          display: 'flex', flexDirection: 'column',
          borderRadius: 0, borderTop: 'none',
          borderRight: 'none', borderBottom: 'none',
          overflow: 'hidden',
        }}>
          <BoardExplorer />
        </div>
      </main>
    </div>
  )
}

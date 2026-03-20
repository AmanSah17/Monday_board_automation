/**
 * BoardExplorer — Inspect raw Monday.com board data (right panel).
 * Loads boards list, lets you click into any board to see columns + items.
 */
import { useState, useEffect, useCallback } from 'react'

function StatusDot({ state }) {
  const color = state === 'active' ? 'var(--accent-green)' : 'var(--text-muted)'
  return (
    <span style={{
      display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
      background: color, marginRight: 5,
    }} />
  )
}

function BoardCard({ board, isSelected, onClick }) {
  return (
    <button onClick={onClick} style={{
      width: '100%', textAlign: 'left', background: isSelected
        ? 'linear-gradient(135deg, var(--accent-blue-dim), var(--accent-purple-dim))'
        : 'var(--bg-glass-light)',
      border: isSelected ? '1px solid var(--border-accent)' : '1px solid var(--border)',
      borderRadius: 10, padding: '10px 14px', cursor: 'pointer',
      transition: 'var(--transition)', marginBottom: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
          <StatusDot state={board.state} />
          {board.name}
        </span>
        <span className="badge badge-gray" style={{ fontSize: 10 }}>
          {board.items_count} items
        </span>
      </div>
      {board.owner?.name && (
        <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
          Owner: {board.owner.name}
        </div>
      )}
    </button>
  )
}

function ColumnTag({ col }) {
  const typeColors = {
    status: 'badge-blue', text: 'badge-gray', numbers: 'badge-green',
    date: 'badge-orange', checkbox: 'badge-purple', dropdown: 'badge-blue',
    people: 'badge-gray', timeline: 'badge-orange',
  }
  return (
    <span className={`badge ${typeColors[col.type] || 'badge-gray'}`}
      style={{ fontSize: 10, marginRight: 4, marginBottom: 4 }}>
      {col.title}
    </span>
  )
}

export default function BoardExplorer() {
  const [boards, setBoards]             = useState([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState(null)
  const [selectedBoard, setSelected]    = useState(null)
  const [detail, setDetail]             = useState(null)
  const [detailLoading, setDetailLoad]  = useState(false)
  const [searchTerm, setSearch]         = useState('')

  // Load boards list
  useEffect(() => {
    setLoading(true)
    fetch('/boards')
      .then(r => r.json())
      .then(d => { setBoards(d.boards || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  // Load board detail
  const loadDetail = useCallback(async (board) => {
    setSelected(board)
    setDetail(null)
    setDetailLoad(true)
    try {
      const [detailRes, itemsRes] = await Promise.all([
        fetch(`/boards/${board.id}`).then(r => r.json()),
        fetch(`/boards/${board.id}/items?limit=50`).then(r => r.json()),
      ])
      setDetail({ ...detailRes, items: itemsRes.items || [], itemCount: itemsRes.count })
    } catch (e) {
      setDetail({ error: e.message })
    } finally {
      setDetailLoad(false)
    }
  }, [])

  const filtered = boards.filter(b =>
    b.name?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: 'linear-gradient(135deg, #10b981, #3b82f6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
        }}>📋</div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Board Explorer</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
            {boards.length} boards loaded
          </div>
        </div>
        {loading && <div className="spinner" style={{ marginLeft: 'auto' }} />}
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Board list */}
        <div style={{
          width: selectedBoard ? '40%' : '100%',
          borderRight: selectedBoard ? '1px solid var(--border)' : 'none',
          overflowY: 'auto', padding: '12px 14px',
          transition: 'width 0.3s ease',
        }}>
          {/* Search */}
          <input
            type="text"
            placeholder="Search boards…"
            value={searchTerm}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', background: 'var(--bg-glass-light)',
              border: '1px solid var(--border)', borderRadius: 8,
              padding: '7px 12px', color: 'var(--text-primary)',
              fontFamily: 'var(--font-sans)', fontSize: 13,
              outline: 'none', marginBottom: 10,
            }}
          />

          {error ? (
            <div style={{ color: 'var(--accent-red)', fontSize: 12, padding: 8 }}>
              ❌ {error}
            </div>
          ) : filtered.length === 0 && !loading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', padding: 20 }}>
              No boards found
            </div>
          ) : (
            filtered.map(board => (
              <BoardCard
                key={board.id}
                board={board}
                isSelected={selectedBoard?.id === board.id}
                onClick={() => loadDetail(board)}
              />
            ))
          )}
        </div>

        {/* Board detail */}
        {selectedBoard && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
            <button className="btn btn-ghost"
              onClick={() => { setSelected(null); setDetail(null) }}
              style={{ fontSize: 11, marginBottom: 12, padding: '5px 10px' }}>
              ← Back
            </button>

            {detailLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}>
                <div className="spinner" />
              </div>
            ) : detail?.error ? (
              <div style={{ color: 'var(--accent-red)', fontSize: 12 }}>❌ {detail.error}</div>
            ) : detail ? (
              <>
                {/* Board meta */}
                <div style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>
                    {detail.board?.name}
                  </h3>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 8 }}>
                    {detail.board?.description || 'No description'}
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span className="badge badge-green">
                      {detail.board?.items_count} items
                    </span>
                    <span className="badge badge-blue">
                      {detail.columns?.length} columns
                    </span>
                    <span className="badge badge-gray">
                      {detail.board?.groups?.length} groups
                    </span>
                  </div>
                </div>

                {/* Columns */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Columns
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                    {detail.columns?.map(col => <ColumnTag key={col.id} col={col} />)}
                  </div>
                </div>

                {/* Sample items */}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Sample Items ({detail.itemCount})
                  </div>
                  {detail.items?.slice(0, 20).map(item => (
                    <div key={item.id} style={{
                      background: 'var(--bg-glass-light)', border: '1px solid var(--border)',
                      borderRadius: 8, padding: '8px 12px', marginBottom: 6, fontSize: 12,
                    }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                        {item.name}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {item.column_values?.filter(cv => cv.text).slice(0, 5).map(cv => (
                          <span key={cv.id} style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{cv.title}:</span>{' '}
                            {cv.text}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}

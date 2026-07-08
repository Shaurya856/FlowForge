import React, { useEffect, useState, useRef } from 'react'
import {
  getWorkflows, startExecution, getExecutions, cancelExecution
} from '../../api/client'
import { Play, RefreshCw, Clock, CheckCircle, XCircle, Loader, Square } from 'lucide-react'

function formatLocalTime(isoString: string): string {
  let dateString = isoString
  // If no timezone indicator (Z or ±HH:MM), assume UTC
  if (!/Z$|[+-]\d{2}:\d{2}$/.test(dateString)) {
    dateString += 'Z'
  }
  const date = new Date(dateString)
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function StatusBadge({ status }: { status: string }) {
  const map: any = {
    success: 'badge-success', failed: 'badge-danger',
    running: 'badge-warning', pending: 'badge-info',
    cancelled: 'badge-default',
  }
  return <span className={`badge ${map[status] || 'badge-default'}`}>{status}</span>
}

function OutcomeDot({ outcome }: { outcome: string }) {
  const colors: any = { success: 'var(--success)', fail: 'var(--danger)', skipped: 'var(--warning)', pending: 'var(--text-2)' }
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: colors[outcome] || 'var(--text-2)', marginRight: 6 }} />
}

function TracePanel({ executionId }: { executionId: string }) {
  const [traces, setTraces] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null)

  useEffect(() => {
    setTraces([])
    setLoading(true)

    const es = new EventSource(`/api/executions/${executionId}/stream`)

    es.addEventListener('trace', (e: MessageEvent) => {
      const trace = JSON.parse(e.data)
      setLoading(false)
      setTraces(prev => [...prev, trace])
    })

    es.addEventListener('status', (e: MessageEvent) => {
      const { status } = JSON.parse(e.data)
      setLoading(false)
      if (status === 'success' || status === 'failed') es.close()
    })

    es.addEventListener('error', () => {
      setLoading(false)
      es.close()
    })

    return () => es.close()
  }, [executionId])

  if (loading) return <div className="empty-state">Loading traces…</div>
  if (traces.length === 0) return <div className="empty-state">No traces yet — execution may still be running</div>

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th style={{ width: '5%' }}></th>
            <th>Step</th>
            <th>Outcome</th>
            <th>Status Code</th>
            <th>Response Time</th>
            <th>Worker</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {traces.map(t => (
            <React.Fragment key={t.trace_id}>
              <tr onClick={() => setExpandedTraceId(expandedTraceId === t.trace_id ? null : t.trace_id)} style={{ cursor: 'pointer' }}>
                <td style={{ textAlign: 'center', color: 'var(--text-2)', fontSize: 12 }}>{expandedTraceId === t.trace_id ? '▼' : '▶'}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{t.step_name}</td>
                <td><OutcomeDot outcome={t.outcome} />{t.outcome}</td>
                <td>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: t.status_code >= 400 ? 'var(--danger)' : t.status_code >= 200 ? 'var(--success)' : 'var(--text-1)' }}>
                    {t.status_code || '—'}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{t.response_time} ms</td>
                <td style={{ color: 'var(--text-2)', fontSize: 12 }}>W{t.worker_id}</td>
                <td style={{ color: 'var(--text-2)', fontSize: 12 }}>{formatLocalTime(t.timestamp)}</td>
              </tr>
              {expandedTraceId === t.trace_id && (
                <tr>
                  <td colSpan={7} style={{ background: 'var(--bg-3)', padding: '12px 16px' }}>
                    <div style={{ display: 'grid', gap: 12 }}>
                      {t.error && (
                        <div>
                          <div style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 600, marginBottom: 4 }}>Error:</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--danger)', background: 'var(--bg-2)', padding: '8px', borderRadius: 4, wordBreak: 'break-all' }}>
                            {t.error}
                          </div>
                        </div>
                      )}
                      <div>
                        <div style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 600, marginBottom: 4 }}>Response Body:</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, background: 'var(--bg-2)', padding: '8px', borderRadius: 4, maxHeight: 300, overflowY: 'auto', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                          {t.response_body ? (
                            <>
                              {(() => {
                                try {
                                  return JSON.stringify(JSON.parse(t.response_body), null, 2)
                                } catch {
                                  return t.response_body
                                }
                              })()}
                            </>
                          ) : (
                            <span style={{ color: 'var(--text-2)' }}>—</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ExecutionCard({ ex, onSelect, selected }: { ex: any; onSelect: () => void; selected: boolean }) {
  return (
    <div
      onClick={onSelect}
      style={{
        padding: '12px 16px', borderRadius: 8, cursor: 'pointer', marginBottom: 8,
        background: selected ? 'var(--accent-glow)' : 'var(--bg-2)',
        border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
        transition: 'all 0.15s'
      }}
    >
      <div className="flex-between">
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{ex.execution_id.slice(0, 16)}…</span>
        <StatusBadge status={ex.status} />
      </div>
      <div style={{ marginTop: 6, display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-1)' }}>
        <span>✓ {ex.success_rate}%</span>
        <span>⏱ {ex.avg_response_time} ms</span>
        <span>×{ex.concurrency} conc · {ex.iterations} iter</span>
      </div>
    </div>
  )
}

export default function Execution() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [executions, setExecutions] = useState<any[]>([])
  const [selectedExec, setSelectedExec] = useState<string | null>(null)
  const [form, setForm] = useState({ workflow_id: '', concurrency: 1, iterations: 1, use_mock: false })
  const [launching, setLaunching] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getWorkflows().then(r => {
      setWorkflows(r.data)
      if (r.data.length > 0) setForm(f => ({ ...f, workflow_id: r.data[0].workflow_id }))
    })
    loadExecutions()
  }, [])

  const loadExecutions = () => getExecutions().then(r => setExecutions(r.data.reverse()))

  const handleRun = async () => {
    if (!form.workflow_id) { setError('Select a workflow'); return }
    setLaunching(true); setError('')
    try {
      const r = await startExecution(form)
      setSelectedExec(r.data.execution_id)
      setTimeout(loadExecutions, 1000)
      setTimeout(loadExecutions, 3000)
      setTimeout(loadExecutions, 6000)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Execution failed to start')
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Execution Panel</h1>
        <p className="page-subtitle">Run workflows, configure load, inspect execution traces</p>
      </div>

      <div className="grid-2" style={{ gap: 24 }}>
        {/* Left: Config + History */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Run Configuration</div>

            {error && <div style={{ color: 'var(--danger)', marginBottom: 12, fontSize: 13 }}>{error}</div>}

            <div className="form-group">
              <label className="form-label">Workflow</label>
              <select className="form-select" value={form.workflow_id}
                onChange={e => setForm({ ...form, workflow_id: e.target.value })}>
                {workflows.length === 0 && <option value="">No workflows — create one first</option>}
                {workflows.map(wf => (
                  <option key={wf.workflow_id} value={wf.workflow_id}>{wf.name}</option>
                ))}
              </select>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Concurrency</label>
                <input className="form-input" type="number" min={1} max={50}
                  value={form.concurrency}
                  onChange={e => setForm({ ...form, concurrency: +e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Iterations</label>
                <input className="form-input" type="number" min={1} max={100}
                  value={form.iterations}
                  onChange={e => setForm({ ...form, iterations: +e.target.value })} />
              </div>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13 }}>
                <input type="checkbox" checked={form.use_mock}
                  onChange={e => setForm({ ...form, use_mock: e.target.checked })}
                  style={{ width: 16, height: 16 }} />
                <span style={{ color: 'var(--text-0)', fontWeight: 600 }}>Use Mock API</span>
                <span style={{ color: 'var(--text-2)', fontSize: 12 }}>(no real HTTP calls)</span>
              </label>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" onClick={handleRun} disabled={launching} style={{ flex: 1 }}>
                {launching ? <><Loader size={14} className="spin" /> Starting…</> : <><Play size={14} /> Run Workflow</>}
              </button>
              <button className="btn btn-secondary" onClick={loadExecutions}><RefreshCw size={14} /></button>
            </div>

            {form.concurrency > 1 && (
              <div style={{ marginTop: 12, padding: '8px 12px', background: 'rgba(251,191,36,0.08)', border: '1px solid var(--warning)', borderRadius: 6, fontSize: 12, color: 'var(--warning)' }}>
                ⚡ Load test: {form.concurrency * form.iterations} total workflow instances will run concurrently
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title flex-between">
              <span>Execution History</span>
              <span style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 400 }}>{executions.length} total</span>
            </div>
            {executions.length === 0
              ? <div className="empty-state" style={{ padding: 20 }}>No executions yet</div>
              : executions.slice(0, 12).map(ex => (
                <ExecutionCard
                  key={ex.execution_id}
                  ex={ex}
                  selected={selectedExec === ex.execution_id}
                  onSelect={() => setSelectedExec(ex.execution_id)}
                />
              ))
            }
          </div>
        </div>

        {/* Right: Traces */}
        <div className="card">
          <div className="card-title flex-between">
            <span>
              {selectedExec ? `Execution Traces · ${selectedExec.slice(0, 12)}…` : 'Execution Traces'}
            </span>
            {selectedExec && (() => {
              const ex = executions.find(e => e.execution_id === selectedExec)
              const cancellable = ex && (ex.status === 'running' || ex.status === 'pending')
              if (!cancellable) return null
              return (
                <button
                  className="btn btn-danger btn-sm"
                  onClick={async () => {
                    await cancelExecution(selectedExec)
                    loadExecutions()
                  }}
                  title="Stop this execution"
                >
                  <Square size={12} /> Cancel
                </button>
              )
            })()}
          </div>
          {!selectedExec
            ? <div className="empty-state">Select an execution from the left to view traces</div>
            : <TracePanel executionId={selectedExec} />
          }
        </div>
      </div>

      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

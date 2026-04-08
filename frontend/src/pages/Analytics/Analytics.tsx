import { useEffect, useState } from 'react'
import { getExecutions, getMetrics, getWorkflows } from '../../api/client'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

function MetricCard({ label, value, unit, color }: { label: string; value: any; unit?: string; color?: string }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: color || 'var(--text-0)', fontSize: 24 }}>
        {value ?? '—'}{unit && <span style={{ fontSize: 13, color: 'var(--text-1)', marginLeft: 4 }}>{unit}</span>}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-1)', marginBottom: 6 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</div>
      ))}
    </div>
  )
}

export default function Analytics() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [executions, setExecutions] = useState<any[]>([])
  const [selectedWf, setSelectedWf] = useState<string>('all')
  const [detailMetrics, setDetailMetrics] = useState<any>(null)
  const [selectedExec, setSelectedExec] = useState<string>('')

  useEffect(() => {
    getWorkflows().then(r => setWorkflows(r.data))
    getExecutions().then(r => setExecutions(r.data.reverse()))
  }, [])

  const filteredExecs = selectedWf === 'all'
    ? executions
    : executions.filter(e => e.workflow_id === selectedWf)

  const loadDetail = async (execId: string) => {
    setSelectedExec(execId)
    const r = await getMetrics(execId)
    setDetailMetrics(r.data)
  }

  // Chart data: response times over executions
  const trendData = filteredExecs.slice(0, 20).map((e, i) => ({
    name: `#${i + 1}`,
    avg_ms: e.avg_response_time,
    success: e.success_rate,
  }))

  // Step breakdown chart
  const stepData = detailMetrics?.step_summary
    ? Object.entries(detailMetrics.step_summary).map(([name, s]: any) => ({
        name: name.length > 14 ? name.slice(0, 14) + '…' : name,
        avg_ms: s.avg_response_time,
        max_ms: s.max_response_time,
        success: s.success_count,
        fail: s.fail_count,
      }))
    : []

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Performance metrics and execution analysis</p>
        </div>
        <select className="form-select" style={{ width: 220 }}
          value={selectedWf} onChange={e => setSelectedWf(e.target.value)}>
          <option value="all">All Workflows</option>
          {workflows.map(wf => <option key={wf.workflow_id} value={wf.workflow_id}>{wf.name}</option>)}
        </select>
      </div>

      {/* Summary stats */}
      <div className="stat-grid" style={{ marginBottom: 24 }}>
        <MetricCard label="Total Executions" value={filteredExecs.length} />
        <MetricCard
          label="Avg Success Rate"
          value={filteredExecs.length ? Math.round(filteredExecs.reduce((a, e) => a + e.success_rate, 0) / filteredExecs.length) : 0}
          unit="%" color="var(--success)"
        />
        <MetricCard
          label="Avg Latency"
          value={filteredExecs.length ? Math.round(filteredExecs.reduce((a, e) => a + e.avg_response_time, 0) / filteredExecs.length) : 0}
          unit="ms" color="var(--accent)"
        />
        <MetricCard
          label="Failed Executions"
          value={filteredExecs.filter(e => e.status === 'failed').length}
          color="var(--danger)"
        />
      </div>

      {/* Response time trend */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">Response Time Trend (last 20 executions)</div>
        {trendData.length === 0
          ? <div className="empty-state">No execution data — run a workflow first</div>
          : <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="var(--text-2)" tick={{ fontSize: 11 }} />
              <YAxis stroke="var(--text-2)" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="avg_ms" name="Avg Response (ms)" stroke="var(--accent)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        }
      </div>

      <div className="grid-2" style={{ gap: 20 }}>
        {/* Execution list */}
        <div className="card">
          <div className="card-title">Executions — click to inspect</div>
          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {filteredExecs.length === 0
              ? <div className="empty-state" style={{ padding: 20 }}>No executions</div>
              : filteredExecs.map(e => (
                <div key={e.execution_id}
                  onClick={() => loadDetail(e.execution_id)}
                  style={{
                    padding: '10px 12px', borderRadius: 6, cursor: 'pointer', marginBottom: 6,
                    background: selectedExec === e.execution_id ? 'var(--accent-glow)' : 'var(--bg-2)',
                    border: `1px solid ${selectedExec === e.execution_id ? 'var(--accent)' : 'var(--border)'}`,
                  }}>
                  <div className="flex-between">
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{e.execution_id.slice(0, 14)}…</span>
                    <span className={`badge ${e.status === 'success' ? 'badge-success' : e.status === 'failed' ? 'badge-danger' : 'badge-warning'}`}>{e.status}</span>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-1)' }}>
                    {e.success_rate}% success · {e.avg_response_time}ms · {e.total_steps} steps
                  </div>
                </div>
              ))
            }
          </div>
        </div>

        {/* Step breakdown */}
        <div className="card">
          <div className="card-title">
            {detailMetrics ? 'Step Performance Breakdown' : 'Step Breakdown — select execution'}
          </div>
          {!detailMetrics
            ? <div className="empty-state">Click an execution to see step-level metrics</div>
            : <>
              <div className="stat-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr', marginBottom: 16 }}>
                <MetricCard label="Total Steps" value={detailMetrics.total_steps} />
                <MetricCard label="Success" value={detailMetrics.success} color="var(--success)" />
                <MetricCard label="Failed" value={detailMetrics.failed} color="var(--danger)" />
              </div>
              {stepData.length > 0 && (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={stepData}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="var(--text-2)" tick={{ fontSize: 10 }} />
                    <YAxis stroke="var(--text-2)" tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="avg_ms" name="Avg ms" fill="var(--accent)" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="max_ms" name="Max ms" fill="var(--purple)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </>
          }
        </div>
      </div>
    </div>
  )
}

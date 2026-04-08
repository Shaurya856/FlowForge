import { useEffect, useState } from 'react'
import { getExecutions, getAnomalies, getBaseline, getWorkflows } from '../../api/client'
import { AlertTriangle, Zap, Info, CheckCircle, Brain } from 'lucide-react'

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === 'critical') return <AlertTriangle size={15} color="var(--danger)" />
  if (severity === 'warning') return <Zap size={15} color="var(--warning)" />
  return <Info size={15} color="var(--info)" />
}

function AnomalyCard({ anomaly }: { anomaly: any }) {
  const borderColor = anomaly.severity === 'critical' ? 'var(--danger)' : anomaly.severity === 'warning' ? 'var(--warning)' : 'var(--info)'
  const bgColor = anomaly.severity === 'critical' ? 'rgba(248,113,113,0.06)' : anomaly.severity === 'warning' ? 'rgba(251,191,36,0.06)' : 'rgba(96,165,250,0.06)'

  return (
    <div style={{
      padding: '14px 16px', borderRadius: 8, marginBottom: 10,
      background: bgColor, border: `1px solid ${borderColor}`,
    }}>
      <div className="flex-between" style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SeverityIcon severity={anomaly.severity} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: borderColor }}>
            {anomaly.type}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text-2)' }}>
            confidence: {Math.round(anomaly.confidence * 100)}%
          </span>
          <span className={`badge ${anomaly.severity === 'critical' ? 'badge-danger' : anomaly.severity === 'warning' ? 'badge-warning' : 'badge-info'}`}>
            {anomaly.severity}
          </span>
        </div>
      </div>

      <div style={{ fontSize: 13, color: 'var(--text-0)', marginBottom: 8 }}>{anomaly.description}</div>

      <div style={{ display: 'flex', gap: 20, fontSize: 12, color: 'var(--text-1)' }}>
        <span>Step: <strong style={{ color: 'var(--text-0)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{anomaly.step_name}</strong></span>
        <span>Response: <strong style={{ color: borderColor, fontFamily: 'var(--font-mono)' }}>{anomaly.response_time} ms</strong></span>
        <span>Baseline avg: <strong style={{ fontFamily: 'var(--font-mono)' }}>{anomaly.baseline_avg} ms</strong></span>
        <span>Worker: W{anomaly.worker_id}</span>
      </div>

      <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
        {new Date(anomaly.timestamp).toLocaleString()}
      </div>
    </div>
  )
}

export default function AIInsights() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [executions, setExecutions] = useState<any[]>([])
  const [selectedExec, setSelectedExec] = useState<string>('')
  const [anomalyData, setAnomalyData] = useState<any>(null)
  const [baseline, setBaseline] = useState<any>(null)
  const [selectedWf, setSelectedWf] = useState<string>('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getWorkflows().then(r => {
      setWorkflows(r.data)
      if (r.data.length > 0) setSelectedWf(r.data[0].workflow_id)
    })
    getExecutions().then(r => setExecutions(r.data.reverse()))
  }, [])

  const handleAnalyze = async () => {
    if (!selectedExec) return
    setLoading(true)
    try {
      const r = await getAnomalies(selectedExec)
      setAnomalyData(r.data)
    } finally {
      setLoading(false)
    }
  }

  const handleBaseline = async () => {
    if (!selectedWf) return
    const r = await getBaseline(selectedWf)
    setBaseline(r.data)
  }

  const criticalCount = anomalyData?.critical_count || 0
  const warningCount = anomalyData?.warning_count || 0

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">AI Insights</h1>
        <p className="page-subtitle">Statistical anomaly detection using Z-score and IQR analysis</p>
      </div>

      <div className="grid-2" style={{ gap: 24 }}>
        {/* Left: Controls */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Brain size={14} /> Anomaly Detection
            </div>

            <div className="form-group">
              <label className="form-label">Select Execution to Analyze</label>
              <select className="form-select" value={selectedExec}
                onChange={e => setSelectedExec(e.target.value)}>
                <option value="">— choose an execution —</option>
                {executions.map(e => (
                  <option key={e.execution_id} value={e.execution_id}>
                    {e.execution_id.slice(0, 16)}… · {e.status} · {e.success_rate}%
                  </option>
                ))}
              </select>
            </div>

            <button className="btn btn-primary" onClick={handleAnalyze} disabled={!selectedExec || loading}
              style={{ width: '100%' }}>
              {loading ? 'Analyzing…' : '⚡ Run Anomaly Detection'}
            </button>

            <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--bg-2)', borderRadius: 6, fontSize: 12, color: 'var(--text-1)', lineHeight: 1.7 }}>
              <strong style={{ color: 'var(--text-0)' }}>Detection methods:</strong><br />
              • <strong>Z-score</strong>: flags values &gt; 2.5σ from mean<br />
              • <strong>IQR</strong>: flags values outside 1.5× interquartile range<br />
              • <strong>Error rate</strong>: flags steps with &gt;20% failure rate<br />
              <span style={{ color: 'var(--success)', marginTop: 4, display: 'block' }}>✓ Runs locally — no LLM, no cloud, no GPU required</span>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Performance Baseline</div>
            <div className="form-group">
              <label className="form-label">Workflow</label>
              <select className="form-select" value={selectedWf} onChange={e => setSelectedWf(e.target.value)}>
                {workflows.map(wf => <option key={wf.workflow_id} value={wf.workflow_id}>{wf.name}</option>)}
              </select>
            </div>
            <button className="btn btn-secondary" onClick={handleBaseline} style={{ width: '100%' }}>
              Build Baseline from History
            </button>

            {baseline && !baseline.error && (
              <div style={{ marginTop: 14 }}>
                <div style={{ fontSize: 12, color: 'var(--text-1)', marginBottom: 8 }}>
                  Built from <strong style={{ color: 'var(--text-0)' }}>{baseline.execution_count}</strong> executions
                </div>
                {Object.entries(baseline.step_baselines).map(([step, stats]: any) => (
                  <div key={step} style={{ padding: '8px 10px', background: 'var(--bg-2)', borderRadius: 6, marginBottom: 6, fontSize: 12 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-0)', marginBottom: 4 }}>{step}</div>
                    <div style={{ display: 'flex', gap: 14, color: 'var(--text-1)' }}>
                      <span>avg: <strong style={{ color: 'var(--accent)' }}>{stats.avg}ms</strong></span>
                      <span>std: {stats.std}ms</span>
                      <span>n={stats.sample_count}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {baseline?.error && (
              <div style={{ marginTop: 10, color: 'var(--warning)', fontSize: 13 }}>{baseline.error}</div>
            )}
          </div>
        </div>

        {/* Right: Results */}
        <div className="card">
          <div className="card-title">Detection Results</div>

          {!anomalyData ? (
            <div className="empty-state">Select an execution and click Run to detect anomalies</div>
          ) : (
            <>
              {/* Summary banner */}
              <div style={{
                padding: '12px 14px', borderRadius: 8, marginBottom: 16,
                background: criticalCount > 0 ? 'rgba(248,113,113,0.08)' : warningCount > 0 ? 'rgba(251,191,36,0.08)' : 'rgba(52,211,153,0.08)',
                border: `1px solid ${criticalCount > 0 ? 'var(--danger)' : warningCount > 0 ? 'var(--warning)' : 'var(--success)'}`,
                display: 'flex', alignItems: 'center', gap: 10
              }}>
                {criticalCount > 0
                  ? <AlertTriangle size={16} color="var(--danger)" />
                  : warningCount > 0
                  ? <Zap size={16} color="var(--warning)" />
                  : <CheckCircle size={16} color="var(--success)" />}
                <span style={{ fontSize: 13 }}>{anomalyData.summary}</span>
              </div>

              {/* Counts */}
              <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                <div style={{ flex: 1, padding: '10px 12px', background: 'var(--bg-2)', borderRadius: 6, textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontFamily: 'var(--font-mono)', color: 'var(--danger)', fontWeight: 700 }}>{criticalCount}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Critical</div>
                </div>
                <div style={{ flex: 1, padding: '10px 12px', background: 'var(--bg-2)', borderRadius: 6, textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontFamily: 'var(--font-mono)', color: 'var(--warning)', fontWeight: 700 }}>{warningCount}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Warnings</div>
                </div>
                <div style={{ flex: 1, padding: '10px 12px', background: 'var(--bg-2)', borderRadius: 6, textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontFamily: 'var(--font-mono)', color: 'var(--text-0)', fontWeight: 700 }}>{anomalyData.anomaly_count}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Total</div>
                </div>
              </div>

              {/* Anomaly list */}
              <div style={{ maxHeight: 420, overflowY: 'auto' }}>
                {anomalyData.anomalies.length === 0
                  ? <div className="empty-state" style={{ padding: 30 }}>
                    <CheckCircle size={28} color="var(--success)" style={{ margin: '0 auto 10px' }} />
                    <div>All steps within normal parameters</div>
                  </div>
                  : anomalyData.anomalies.map((a: any, i: number) => (
                    <AnomalyCard key={i} anomaly={a} />
                  ))
                }
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

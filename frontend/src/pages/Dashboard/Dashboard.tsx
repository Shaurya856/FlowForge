import { useEffect, useState } from 'react'
import { getDashboard } from '../../api/client'
import { Activity, GitBranch, Play, CheckCircle, Clock } from 'lucide-react'

function StatusBadge({ status }: { status: string }) {
  const map: any = {
    success: 'badge-success', failed: 'badge-danger',
    running: 'badge-warning', pending: 'badge-info'
  }
  return <span className={`badge ${map[status] || 'badge-default'}`}>{status}</span>
}

export default function Dashboard() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard()
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="empty-state">Loading dashboard…</div>
  if (!data) return <div className="empty-state">Backend not reachable — start the FastAPI server</div>

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Platform overview — Scenario-Based API Workflow Execution System</p>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Total Workflows</div>
          <div className="stat-value accent">{data.total_workflows}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Executions</div>
          <div className="stat-value">{data.total_executions}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Now</div>
          <div className="stat-value warning">{data.active_executions}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Success Rate</div>
          <div className="stat-value success">{data.avg_success_rate}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Latency</div>
          <div className="stat-value">{data.avg_latency_ms}<span style={{fontSize:14,color:'var(--text-1)'}}> ms</span></div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Recent Executions</div>
        {data.recent_executions?.length === 0 ? (
          <div className="empty-state">No executions yet — run a workflow to see results here</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Execution ID</th>
                  <th>Workflow</th>
                  <th>Status</th>
                  <th>Success Rate</th>
                  <th>Avg Latency</th>
                  <th>Concurrency</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_executions?.map((e: any) => (
                  <tr key={e.execution_id}>
                    <td className="text-mono">{e.execution_id.slice(0, 12)}…</td>
                    <td className="text-mono" style={{fontSize:11}}>{e.workflow_id.slice(0, 10)}…</td>
                    <td><StatusBadge status={e.status} /></td>
                    <td>{e.success_rate}%</td>
                    <td>{e.avg_response_time} ms</td>
                    <td>{e.concurrency}×{e.iterations}</td>
                    <td className="text-muted text-sm">{e.start_time ? new Date(e.start_time).toLocaleTimeString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

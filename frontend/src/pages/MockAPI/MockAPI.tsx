import { useEffect, useState } from 'react'
import { getMockConfigs, createMockConfig, deleteMockConfig } from '../../api/client'
import { Plus, Trash2, Server } from 'lucide-react'

const BUILTIN_MOCKS = [
  { method: 'GET', path: '/mock/health', description: 'Health check — returns {status: ok}', status: 200 },
  { method: 'POST', path: '/mock/login', description: 'Login — returns JWT token + user_id', status: 200 },
  { method: 'GET', path: '/mock/users', description: 'User list — returns paginated users', status: 200 },
  { method: 'POST', path: '/mock/data', description: 'Create data — returns 201 with id', status: 201 },
  { method: 'GET', path: '/mock/items', description: 'Item catalog — returns items list', status: 200 },
  { method: 'DELETE', path: '/mock/item', description: 'Delete item — returns {deleted: true}', status: 200 },
  { method: 'PUT', path: '/mock/update', description: 'Update item — returns {updated: true}', status: 200 },
]

const METHOD_COLORS: any = {
  GET: 'var(--success)', POST: 'var(--accent)',
  PUT: 'var(--warning)', PATCH: 'var(--purple)', DELETE: 'var(--danger)'
}

export default function MockAPI() {
  const [configs, setConfigs] = useState<any[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    endpoint: '', http_method: 'GET',
    response_template: '{\n  "status": "ok",\n  "data": {}\n}',
    latency_min: 10, latency_max: 100,
    error_rate: 0, status_code: 200
  })
  const [formError, setFormError] = useState('')

  const load = () => getMockConfigs().then(r => setConfigs(r.data))
  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.endpoint) { setFormError('Endpoint is required'); return }
    try {
      const template = JSON.parse(form.response_template)
      await createMockConfig({
        ...form,
        response_template: template,
        error_rate: form.error_rate / 100,
      })
      setShowCreate(false)
      setFormError('')
      load()
    } catch {
      setFormError('Invalid JSON in response template')
    }
  }

  const handleDelete = async (id: string) => {
    await deleteMockConfig(id)
    load()
  }

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Mock API</h1>
          <p className="page-subtitle">Configure simulated API endpoints for isolated testing</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> Add Mock Endpoint
        </button>
      </div>

      {/* Built-in mocks */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Server size={13} /> Built-in Mock Endpoints
          <span style={{ fontSize: 11, color: 'var(--text-2)', fontWeight: 400, marginLeft: 4 }}>
            — always available, no config needed
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {BUILTIN_MOCKS.map(m => (
            <div key={m.path} style={{ padding: '10px 12px', background: 'var(--bg-2)', borderRadius: 6, border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: METHOD_COLORS[m.method], minWidth: 44 }}>{m.method}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-0)' }}>{m.path}</span>
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--success)' }}>{m.status}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>{m.description}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--bg-0)', borderRadius: 6, fontSize: 12, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
          Base URL for mock endpoints: <span style={{ color: 'var(--accent)' }}>http://localhost:8000</span>
          &nbsp;— use this as your endpoint URL in workflow steps with "Use Mock API" enabled
        </div>
      </div>

      {/* Custom configs */}
      <div className="card">
        <div className="card-title">Custom Mock Configurations ({configs.length})</div>
        {configs.length === 0 ? (
          <div className="empty-state">No custom configs yet — add one to override built-in behaviour or create new endpoints</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Endpoint</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Error Rate</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {configs.map(c => (
                  <tr key={c.mock_id}>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: METHOD_COLORS[c.http_method] }}>
                        {c.http_method}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{c.endpoint}</td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: c.status_code < 400 ? 'var(--success)' : 'var(--danger)' }}>
                        {c.status_code}
                      </span>
                    </td>
                    <td style={{ fontSize: 12 }}>{c.latency_min}–{c.latency_max} ms</td>
                    <td style={{ fontSize: 12, color: c.error_rate > 0.1 ? 'var(--warning)' : 'var(--text-1)' }}>
                      {Math.round(c.error_rate * 100)}%
                    </td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c.mock_id)}>
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">Add Custom Mock Endpoint</div>
            {formError && <div style={{ color: 'var(--danger)', marginBottom: 12, fontSize: 13 }}>{formError}</div>}

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Endpoint Path</label>
                <input className="form-input" placeholder="/api/v1/resource"
                  value={form.endpoint} onChange={e => setForm({ ...form, endpoint: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">HTTP Method</label>
                <select className="form-select" value={form.http_method}
                  onChange={e => setForm({ ...form, http_method: e.target.value })}>
                  {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Response Template (JSON)</label>
              <textarea className="form-textarea" style={{ minHeight: 100 }}
                value={form.response_template}
                onChange={e => setForm({ ...form, response_template: e.target.value })} />
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Latency Min (ms)</label>
                <input className="form-input" type="number" min={0}
                  value={form.latency_min} onChange={e => setForm({ ...form, latency_min: +e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Latency Max (ms)</label>
                <input className="form-input" type="number" min={0}
                  value={form.latency_max} onChange={e => setForm({ ...form, latency_max: +e.target.value })} />
              </div>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Error Rate (%)</label>
                <input className="form-input" type="number" min={0} max={100}
                  value={form.error_rate} onChange={e => setForm({ ...form, error_rate: +e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Status Code</label>
                <input className="form-input" type="number"
                  value={form.status_code} onChange={e => setForm({ ...form, status_code: +e.target.value })} />
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleCreate}><Plus size={14} /> Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { updateStep } from '../../api/client'

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

export default function EditStepModal({ step, onClose, onSaved }: { step: any; onClose: () => void; onSaved: () => void }) {
  const parseJson = (v: any) => {
    if (typeof v === 'string') return v
    return JSON.stringify(v, null, 2)
  }
  const [form, setForm] = useState({
    name: step.name || '',
    endpoint: step.endpoint || '',
    http_method: step.http_method || 'GET',
    headers: parseJson(step.headers || '{}'),
    body: parseJson(step.body || '{}'),
    extract_vars: parseJson(step.extract_vars || '{}'),
    condition: step.condition || '',
    retry_count: step.retry_count ?? 0,
    execution_order: step.execution_order ?? 0,
    timeout_seconds: step.timeout_seconds ?? 30,
  })
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.name || !form.endpoint) { setError('Name and endpoint are required'); return }
    try {
      const headers = JSON.parse(form.headers || '{}')
      const body = JSON.parse(form.body || '{}')
      const extract_vars = JSON.parse(form.extract_vars || '{}')
      await updateStep(step.step_id, { ...form, headers, body, extract_vars })
      onSaved()
      onClose()
    } catch (e: any) {
      setError(e.message || 'Invalid JSON in headers/body/extract_vars')
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">Edit Step</div>
        {error && <div style={{ color: 'var(--danger)', marginBottom: 12, fontSize: 13 }}>{error}</div>}

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Step Name</label>
            <input className="form-input" value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">HTTP Method</label>
            <select className="form-select" value={form.http_method}
              onChange={e => setForm({ ...form, http_method: e.target.value })}>
              {HTTP_METHODS.map(m => <option key={m}>{m}</option>)}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Endpoint URL</label>
          <input className="form-input" value={form.endpoint}
            onChange={e => setForm({ ...form, endpoint: e.target.value })} />
        </div>

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Headers (JSON)</label>
            <textarea className="form-textarea" value={form.headers}
              onChange={e => setForm({ ...form, headers: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Body (JSON)</label>
            <textarea className="form-textarea" value={form.body}
              onChange={e => setForm({ ...form, body: e.target.value })} />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Extract Variables (JSON)</label>
          <textarea className="form-textarea" style={{ minHeight: 50 }} value={form.extract_vars}
            onChange={e => setForm({ ...form, extract_vars: e.target.value })} />
        </div>

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Condition <span style={{ color: 'var(--text-2)', fontWeight: 400 }}>e.g. status == 200</span></label>
            <input className="form-input" value={form.condition}
              onChange={e => setForm({ ...form, condition: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Execution Order</label>
            <input className="form-input" type="number" min={0} value={form.execution_order}
              onChange={e => setForm({ ...form, execution_order: +e.target.value })} />
          </div>
        </div>

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Retry Count</label>
            <input className="form-input" type="number" min={0} max={5} value={form.retry_count}
              onChange={e => setForm({ ...form, retry_count: +e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Timeout (seconds)</label>
            <input className="form-input" type="number" min={1} max={600} value={form.timeout_seconds}
              onChange={e => setForm({ ...form, timeout_seconds: +e.target.value })} />
          </div>
        </div>

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}>Save Changes</button>
        </div>
      </div>
    </div>
  )
}

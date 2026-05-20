import { useState } from 'react'
import { Plus } from 'lucide-react'
import { createStep } from '../../api/client'

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

export default function AddStepModal({ workflowId, onClose, onAdded }: { workflowId: string; onClose: () => void; onAdded: () => void }) {
  const [fileInfo, setFileInfo] = useState<{filename: string, content_b64: string, field_name: string} | null>(null)
  const [form, setForm] = useState({
    name: '', endpoint: '', http_method: 'GET',
    headers: '{}', body: '{}', extract_vars: '{}',
    condition: '', retry_count: 0, execution_order: 0, timeout_seconds: 30
  })
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.name || !form.endpoint) { setError('Name and endpoint are required'); return }
    try {
      const headers = JSON.parse(form.headers || '{}')
      const body = JSON.parse(form.body || '{}')
      let extract_vars = JSON.parse(form.extract_vars || '{}')

      // Embed file info into extract_vars under __file__ key; engine peels it back out
      if (fileInfo) {
        extract_vars = { ...extract_vars, __file__: fileInfo }
      }

      await createStep(workflowId, { ...form, headers, body, extract_vars })
      onAdded()
      onClose()
    } catch (e: any) {
      setError(e.message || 'Invalid JSON in headers/body/extract_vars')
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">Add Workflow Step</div>
        {error && <div style={{ color: 'var(--danger)', marginBottom: 12, fontSize: 13 }}>{error}</div>}

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Step Name</label>
            <input className="form-input" placeholder="e.g. Login Request"
              value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
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
          <input className="form-input" placeholder="http://localhost:8000/mock/login or {{base_url}}/endpoint"
            value={form.endpoint} onChange={e => setForm({ ...form, endpoint: e.target.value })} />
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
          <label className="form-label">Extract Variables (JSON) <span style={{ color: 'var(--text-2)', fontWeight: 400 }}>e.g. {"{ \"token\": \"token\" }"}</span></label>
          <textarea className="form-textarea" style={{ minHeight: 50 }} value={form.extract_vars}
            onChange={e => setForm({ ...form, extract_vars: e.target.value })} />
        </div>

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Condition <span style={{ color: 'var(--text-2)', fontWeight: 400 }}>e.g. status == 200</span></label>
            <input className="form-input" placeholder="status == 200"
              value={form.condition} onChange={e => setForm({ ...form, condition: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Execution Order</label>
            <input className="form-input" type="number" min={0}
              value={form.execution_order} onChange={e => setForm({ ...form, execution_order: +e.target.value })} />
          </div>
        </div>

        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Retry Count</label>
            <input className="form-input" type="number" min={0} max={5}
              value={form.retry_count} onChange={e => setForm({ ...form, retry_count: +e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Timeout (seconds)</label>
            <input className="form-input" type="number" min={1} max={600}
              value={form.timeout_seconds} onChange={e => setForm({ ...form, timeout_seconds: +e.target.value })} />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">
            File Upload
            <span style={{ color: 'var(--text-2)', fontWeight: 400, marginLeft: 6 }}>
              (optional — for multipart/form-data endpoints)
            </span>
          </label>
          <input
            type="file"
            style={{
              width: '100%', background: 'var(--bg-2)', border: '1px solid var(--border)',
              borderRadius: 6, padding: '7px 12px', color: 'var(--text-0)',
              fontSize: 13, cursor: 'pointer'
            }}
            onChange={e => {
              const file = e.target.files?.[0]
              if (!file) { setFileInfo(null); return }
              const reader = new FileReader()
              reader.onload = () => {
                const b64 = (reader.result as string).split(',')[1]
                setFileInfo({ filename: file.name, content_b64: b64, field_name: 'file' })
              }
              reader.readAsDataURL(file)
            }}
          />
          {fileInfo && (
            <div style={{ marginTop: 6, fontSize: 12, color: 'var(--success)' }}>
              ✓ {fileInfo.filename} — will be sent as multipart/form-data
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}><Plus size={14} /> Add Step</button>
        </div>
      </div>
    </div>
  )
}

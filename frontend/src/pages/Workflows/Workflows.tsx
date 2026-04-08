import { useEffect, useState } from 'react'
import {
  getWorkflows, createWorkflow, deleteWorkflow,
  getSteps, createStep, deleteStep, validateWorkflow
} from '../../api/client'
import { Plus, Trash2, ChevronDown, ChevronRight, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

function StepRow({ step, onDelete }: { step: any; onDelete: () => void }) {
  const methodColors: any = {
    GET: 'var(--success)', POST: 'var(--accent)',
    PUT: 'var(--warning)', PATCH: 'var(--purple)', DELETE: 'var(--danger)'
  }
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 14px', background: 'var(--bg-2)',
      borderRadius: 6, marginBottom: 6, border: '1px solid var(--border)'
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
        color: methodColors[step.http_method] || 'var(--text-1)',
        minWidth: 52
      }}>{step.http_method}</span>
      <span style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-0)' }}>{step.name}</span>
      <span style={{ flex: 2, fontSize: 12, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{step.endpoint}</span>
      <span style={{ fontSize: 11, color: 'var(--text-2)' }}>order: {step.execution_order}</span>
      <button className="btn btn-danger btn-sm" onClick={onDelete}><Trash2 size={13} /></button>
    </div>
  )
}

function AddStepModal({ workflowId, onClose, onAdded }: { workflowId: string; onClose: () => void; onAdded: () => void }) {
  const [form, setForm] = useState({
    name: '', endpoint: '', http_method: 'GET',
    headers: '{}', body: '{}', extract_vars: '{}',
    condition: '', retry_count: 0, execution_order: 0
  })
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.name || !form.endpoint) { setError('Name and endpoint are required'); return }
    try {
      const headers = JSON.parse(form.headers || '{}')
      const body = JSON.parse(form.body || '{}')
      const extract_vars = JSON.parse(form.extract_vars || '{}')
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

        <div className="form-group">
          <label className="form-label">Retry Count</label>
          <input className="form-input" type="number" min={0} max={5}
            value={form.retry_count} onChange={e => setForm({ ...form, retry_count: +e.target.value })} />
        </div>

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}><Plus size={14} /> Add Step</button>
        </div>
      </div>
    </div>
  )
}

function WorkflowRow({ wf, onDelete }: { wf: any; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [steps, setSteps] = useState<any[]>([])
  const [showAddStep, setShowAddStep] = useState(false)
  const [validation, setValidation] = useState<any>(null)

  const loadSteps = async () => {
    const r = await getSteps(wf.workflow_id)
    setSteps(r.data)
  }

  const handleExpand = () => {
    if (!expanded) loadSteps()
    setExpanded(!expanded)
  }

  const handleValidate = async () => {
    const r = await validateWorkflow(wf.workflow_id)
    setValidation(r.data)
  }

  const handleDeleteStep = async (stepId: string) => {
    await deleteStep(stepId)
    loadSteps()
  }

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="flex-between">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }} onClick={handleExpand}>
          {expanded ? <ChevronDown size={16} color="var(--text-1)" /> : <ChevronRight size={16} color="var(--text-1)" />}
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 14 }}>{wf.name}</div>
            <div style={{ fontSize: 12, color: 'var(--text-1)', marginTop: 2 }}>{wf.description || 'No description'}</div>
          </div>
        </div>
        <div className="flex-gap">
          <span className="text-mono" style={{ color: 'var(--text-2)' }}>{wf.workflow_id.slice(0, 8)}…</span>
          <button className="btn btn-secondary btn-sm" onClick={handleValidate}>Validate</button>
          <button className="btn btn-danger btn-sm" onClick={onDelete}><Trash2 size={13} /></button>
        </div>
      </div>

      {validation && (
        <div style={{
          marginTop: 12, padding: '8px 12px', borderRadius: 6,
          background: validation.valid ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)',
          border: `1px solid ${validation.valid ? 'var(--success)' : 'var(--danger)'}`,
          display: 'flex', alignItems: 'center', gap: 8, fontSize: 13
        }}>
          {validation.valid
            ? <><CheckCircle size={14} color="var(--success)" /> <span style={{ color: 'var(--success)' }}>Workflow is valid and ready for execution</span></>
            : <><XCircle size={14} color="var(--danger)" /> <span style={{ color: 'var(--danger)' }}>{validation.errors.join(', ')}</span></>}
        </div>
      )}

      {expanded && (
        <div style={{ marginTop: 16 }}>
          <div className="flex-between" style={{ marginBottom: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-1)', fontWeight: 600 }}>
              {steps.length} step{steps.length !== 1 ? 's' : ''}
            </span>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAddStep(true)}>
              <Plus size={13} /> Add Step
            </button>
          </div>
          {steps.length === 0
            ? <div className="empty-state" style={{ padding: 20 }}>No steps yet — add your first API step</div>
            : steps.map(s => (
              <StepRow key={s.step_id} step={s} onDelete={() => handleDeleteStep(s.step_id)} />
            ))
          }
          {showAddStep && (
            <AddStepModal
              workflowId={wf.workflow_id}
              onClose={() => setShowAddStep(false)}
              onAdded={loadSteps}
            />
          )}
        </div>
      )}
    </div>
  )
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const load = () => getWorkflows().then(r => setWorkflows(r.data))
  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    await createWorkflow({ name: newName, description: newDesc })
    setNewName(''); setNewDesc(''); setShowCreate(false)
    load()
  }

  const handleDelete = async (id: string) => {
    await deleteWorkflow(id)
    load()
  }

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Workflows</h1>
          <p className="page-subtitle">Define and manage multi-step API workflows</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> New Workflow
        </button>
      </div>

      {workflows.length === 0
        ? <div className="empty-state">No workflows yet — create one to get started</div>
        : workflows.map(wf => (
          <WorkflowRow key={wf.workflow_id} wf={wf} onDelete={() => handleDelete(wf.workflow_id)} />
        ))
      }

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">Create New Workflow</div>
            <div className="form-group">
              <label className="form-label">Workflow Name</label>
              <input className="form-input" placeholder="e.g. User Auth Flow"
                value={newName} onChange={e => setNewName(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <input className="form-input" placeholder="What does this workflow test?"
                value={newDesc} onChange={e => setNewDesc(e.target.value)} />
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

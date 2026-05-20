import { useEffect, useRef, useState } from 'react'
import { getWorkflows, createWorkflow, deleteWorkflow, importWorkflow } from '../../api/client'
import { Plus, Upload } from 'lucide-react'
import WorkflowRow from './WorkflowRow'

export default function Workflows() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [importError, setImportError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''  // reset so picking the same file again re-triggers
    if (!file) return
    setImportError('')
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      await importWorkflow(data)
      load()
    } catch (err: any) {
      setImportError(err.response?.data?.detail || err.message || 'Import failed')
    }
  }

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Workflows</h1>
          <p className="page-subtitle">Define and manage multi-step API workflows</p>
        </div>
        <div className="flex-gap">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            style={{ display: 'none' }}
            onChange={handleImportFile}
          />
          <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()}>
            <Upload size={15} /> Import
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={15} /> New Workflow
          </button>
        </div>
      </div>

      {importError && (
        <div style={{
          marginBottom: 16, padding: '10px 14px', borderRadius: 6,
          background: 'rgba(248,113,113,0.08)', border: '1px solid var(--danger)',
          color: 'var(--danger)', fontSize: 13,
        }}>
          Import failed: {importError}
        </div>
      )}

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

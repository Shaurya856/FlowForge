import { useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight, CheckCircle, XCircle, Download } from 'lucide-react'
import { getSteps, deleteStep, validateWorkflow, exportWorkflow } from '../../api/client'
import StepRow from './StepRow'
import AddStepModal from './AddStepModal'
import EditStepModal from './EditStepModal'

export default function WorkflowRow({ wf, onDelete }: { wf: any; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [steps, setSteps] = useState<any[]>([])
  const [showAddStep, setShowAddStep] = useState(false)
  const [editingStep, setEditingStep] = useState<any>(null)
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

  const handleExport = async () => {
    const r = await exportWorkflow(wf.workflow_id)
    const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const slug = wf.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'workflow'
    a.href = url
    a.download = `${slug}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
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
          <button className="btn btn-secondary btn-sm" onClick={handleExport} title="Download workflow as JSON">
            <Download size={13} />
          </button>
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
              <StepRow key={s.step_id} step={s}
                onDelete={() => handleDeleteStep(s.step_id)}
                onEdit={() => setEditingStep(s)} />
            ))
          }
          {showAddStep && (
            <AddStepModal
              workflowId={wf.workflow_id}
              onClose={() => setShowAddStep(false)}
              onAdded={loadSteps}
            />
          )}
          {editingStep && (
            <EditStepModal
              step={editingStep}
              onClose={() => setEditingStep(null)}
              onSaved={() => { setEditingStep(null); loadSteps() }}
            />
          )}
        </div>
      )}
    </div>
  )
}

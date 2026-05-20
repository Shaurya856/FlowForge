import { Pencil, Trash2 } from 'lucide-react'

export default function StepRow({ step, onDelete, onEdit }: { step: any; onDelete: () => void; onEdit: () => void }) {
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
      <button className="btn btn-secondary btn-sm" onClick={onEdit}><Pencil size={13} /></button>
      <button className="btn btn-danger btn-sm" onClick={onDelete}><Trash2 size={13} /></button>
    </div>
  )
}

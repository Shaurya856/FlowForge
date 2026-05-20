import { Component, ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div style={{ padding: 32 }}>
        <div className="card" style={{ borderColor: 'var(--danger)' }}>
          <div className="card-title" style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={18} />
            Something went wrong on this page
          </div>
          <pre style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            color: 'var(--text-1)',
            background: 'var(--bg-2)',
            padding: 12,
            borderRadius: 6,
            border: '1px solid var(--border)',
            overflowX: 'auto',
            whiteSpace: 'pre-wrap',
          }}>
            {this.state.error.message}
          </pre>
          <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
            <button className="btn btn-primary" onClick={this.reset}>Try again</button>
            <button className="btn btn-secondary" onClick={() => window.location.reload()}>Reload page</button>
          </div>
        </div>
      </div>
    )
  }
}

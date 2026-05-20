import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard/Dashboard'
import Workflows from './pages/Workflows/Workflows'
import Execution from './pages/Execution/Execution'
import Analytics from './pages/Analytics/Analytics'
import AIInsights from './pages/AIInsights/AIInsights'
import MockAPI from './pages/MockAPI/MockAPI'
import ErrorBoundary from './components/ErrorBoundary'
import {
  LayoutDashboard, GitBranch, Play, BarChart2,
  Brain, Server, Zap
} from 'lucide-react'
import './App.css'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/workflows', label: 'Workflows', icon: GitBranch },
  { to: '/execution', label: 'Execution', icon: Play },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/ai-insights', label: 'AI Insights', icon: Brain },
  { to: '/mock-api', label: 'Mock API', icon: Server },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-brand">
            <Zap size={22} className="brand-icon" />
            <span>FlowForge</span>
          </div>
          <nav className="sidebar-nav">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={17} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-footer">
            <span>BCSE301P · 23BAI0185</span>
          </div>
        </aside>
        <main className="main-content">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/execution" element={<Execution />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/ai-insights" element={<AIInsights />} />
              <Route path="/mock-api" element={<MockAPI />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </BrowserRouter>
  )
}

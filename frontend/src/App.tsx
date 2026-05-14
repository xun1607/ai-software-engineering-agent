import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, BookOpen, FlaskConical, TestTube, BarChart3, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard'
import SkillBrowser from './pages/SkillBrowser'
import SkillDetail from './pages/SkillDetail'
import EvaluationPage from './pages/EvaluationPage'
import TestingPage from './pages/TestingPage'
import ReportsPage from './pages/ReportsPage'
import { skillsApi } from './api/client'

export default function App() {
  const [registryCount, setRegistryCount] = useState<number | null>(null)

  useEffect(() => {
    skillsApi.registryStatus()
      .then((d: { loaded_skills: number }) => setRegistryCount(d.loaded_skills))
      .catch(() => setRegistryCount(null))
  }, [])

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>⚡ Skill Library</h1>
          <p>AI Agent Platform</p>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section">
            <div className="nav-section-label">Overview</div>
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <LayoutDashboard size={15} className="icon" /> Dashboard
            </NavLink>
          </div>
          <div className="nav-section">
            <div className="nav-section-label">Skills</div>
            <NavLink to="/skills" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <BookOpen size={15} className="icon" /> Skill Browser
            </NavLink>
          </div>
          <div className="nav-section">
            <div className="nav-section-label">Services</div>
            <NavLink to="/evaluation" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <FlaskConical size={15} className="icon" /> Evaluation
            </NavLink>
            <NavLink to="/testing" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <TestTube size={15} className="icon" /> Testing
            </NavLink>
            <NavLink to="/reports" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <BarChart3 size={15} className="icon" /> Reports
            </NavLink>
          </div>
        </nav>
        <div className="sidebar-footer">
          <div className="registry-badge">
            <div className="dot" />
            <span>{registryCount !== null ? `${registryCount} skills loaded` : 'Connecting...'}</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/skills" element={<SkillBrowser />} />
          <Route path="/skills/:id" element={<SkillDetail />} />
          <Route path="/evaluation" element={<EvaluationPage />} />
          <Route path="/testing" element={<TestingPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </main>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { reportingApi, DashboardData } from '../api/client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { BookOpen, FlaskConical, TestTube, FileCheck, RefreshCw } from 'lucide-react'

const COLORS = ['#6366f1', '#22d3ee', '#a78bfa', '#fbbf24', '#f87171', '#34d399']

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    reportingApi.dashboard()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const categoryChart = data
    ? Object.entries(data.by_category).map(([name, count]) => ({ name: name.split('/').pop(), full: name, count }))
    : []

  return (
    <div>
      <div className="page-header flex items-center justify-between">
        <div>
          <h2>Dashboard</h2>
          <p>Real-time overview of your skill library</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : !data ? (
        <div className="empty-state"><h3>Unable to connect to services</h3><p>Make sure all backend services are running.</p></div>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-card" onClick={() => navigate('/skills')} style={{ cursor: 'pointer' }}>
              <div className="stat-label">Total Skills</div>
              <div className="stat-value accent">{data.skills.total}</div>
              <div className="stat-sub">{data.registry_loaded} in registry</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Test Runs</div>
              <div className="stat-value" style={{ color: 'var(--green)' }}>{data.test_runs.total}</div>
              <div className="stat-sub">{data.test_runs.pass_rate}% pass rate</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Doc Reviews</div>
              <div className="stat-value" style={{ color: 'var(--purple)' }}>{data.doc_reviews.total}</div>
              <div className="stat-sub">{data.doc_reviews.pass_rate}% pass rate</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Evaluations</div>
              <div className="stat-value" style={{ color: 'var(--yellow)' }}>{data.evaluations.total}</div>
              <div className="stat-sub">test-case runs</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-sm">Skills by Category</h3>
              </div>
              {categoryChart.length === 0 ? (
                <div className="empty-state" style={{ padding: '30px' }}>No categories yet</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={categoryChart} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#0f1420', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, color: '#f1f5f9' }}
                      formatter={(v, _, p) => [v, p.payload.full]}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {categoryChart.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="card">
              <h3 className="font-bold text-sm mb-4">Skills by Level</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Object.entries(data.by_level).map(([level, count]) => (
                  <div key={level}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={`badge badge-${level}`}>{level}</span>
                      <span className="text-sm font-bold">{count}</span>
                    </div>
                    <div style={{ background: 'var(--border)', borderRadius: 4, height: 6 }}>
                      <div style={{
                        width: `${data.skills.total ? (count / data.skills.total * 100) : 0}%`,
                        height: '100%',
                        borderRadius: 4,
                        background: level === 'atomic' ? 'var(--accent)' : 'var(--purple)',
                        transition: 'width 0.8s ease',
                      }} />
                    </div>
                  </div>
                ))}
              </div>

              <hr className="divider" />
              <h3 className="font-bold text-sm mb-3">Quick Actions</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button className="btn btn-secondary w-full" onClick={() => navigate('/skills')}>
                  <BookOpen size={14} /> Browse Skills
                </button>
                <button className="btn btn-secondary w-full" onClick={() => navigate('/evaluation')}>
                  <FlaskConical size={14} /> Run Evaluation
                </button>
                <button className="btn btn-secondary w-full" onClick={() => navigate('/reports')}>
                  <FlaskConical size={14} /> View Reports
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

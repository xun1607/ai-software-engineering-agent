import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { evaluationApi, skillsApi, SkillSummary, FullEvaluation } from '../api/client'
import { Play, CheckCircle, XCircle } from 'lucide-react'

export default function EvaluationPage() {
  const location = useLocation()
  const initialSkillId = location.state?.skillId || ''
  
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [selectedSkill, setSelectedSkill] = useState(initialSkillId)
  const [result, setResult] = useState<FullEvaluation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    skillsApi.list().then(res => setSkills(res.items)).catch(console.error)
  }, [])

  const handleEvaluate = async () => {
    if (!selectedSkill) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await evaluationApi.evaluateAll(selectedSkill, true)
      setResult(res)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Evaluation</h2>
        <p>Run documentation reviews and automated test cases for skills</p>
      </div>

      <div className="card mb-6 flex gap-3 items-end">
        <div className="form-group mb-0 flex-1">
          <label className="form-label">Select Skill to Evaluate</label>
          <select 
            className="form-input form-select" 
            value={selectedSkill} 
            onChange={e => setSelectedSkill(e.target.value)}
          >
            <option value="">-- Choose a skill --</option>
            {skills.map(s => <option key={s.id} value={s.id}>{s.name} ({s.level})</option>)}
          </select>
        </div>
        <button 
          className="btn btn-primary" 
          onClick={handleEvaluate} 
          disabled={!selectedSkill || loading}
          style={{ height: 40 }}
        >
          {loading ? <div className="spinner" style={{ width: 16, height: 16 }} /> : <Play size={16} />} 
          Run Evaluation
        </button>
      </div>

      {error && (
        <div className="card mb-6" style={{ borderColor: 'var(--red)', background: 'rgba(248,113,113,0.05)' }}>
          <h3 className="text-red font-bold flex items-center gap-2"><XCircle size={18} /> Error</h3>
          <p className="mt-2 text-sm">{error}</p>
        </div>
      )}

      {result && (
        <div className="grid-2">
          {result.doc_review && (
            <div className="card">
              <h3 className="font-bold text-sm mb-4">Documentation Score</h3>
              <div className={`score-circle ${result.doc_review.passed ? 'pass' : 'fail'}`}>
                <div className="score-num">{result.doc_review.doc_score}</div>
                <div className="score-denom">/ {result.doc_review.max_score}</div>
              </div>
              <div className="text-center mb-6">
                <span className={`badge ${result.doc_review.passed ? 'badge-pass' : 'badge-fail'}`}>
                  {result.doc_review.passed ? 'PASSED' : 'FAILED'}
                </span>
                <div className="text-xs text-muted mt-2">Threshold: {result.doc_review.threshold}</div>
              </div>
              
              <div className="mt-4 border-t border-[rgba(255,255,255,0.08)] pt-4 max-h-[300px] overflow-y-auto">
                {result.doc_review.criteria.map((c, i) => (
                  <div key={i} className="criterion-row">
                    <div className="criterion-icon">
                      {c.passed ? <CheckCircle size={14} className="text-green" /> : <XCircle size={14} className="text-red" />}
                    </div>
                    <div className="criterion-desc">
                      <div>{c.description}</div>
                      {c.note && <div className="criterion-note">{c.note}</div>}
                    </div>
                    <div className={`criterion-pts ${c.passed ? 'pts-pass' : 'pts-fail'}`}>
                      {c.passed ? '+' : ''}{c.points}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.evaluation ? (
            <div className="card">
              <h3 className="font-bold text-sm mb-4">Test Execution (Mock)</h3>
              <div className={`score-circle ${result.evaluation.summary.failed === 0 ? 'pass' : 'fail'}`}>
                <div className="score-num">{result.evaluation.summary.pass_rate_pct}%</div>
                <div className="score-denom">Pass Rate</div>
              </div>
              <div className="flex justify-center gap-4 mb-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green">{result.evaluation.summary.passed}</div>
                  <div className="text-xs text-muted uppercase tracking-wide">Passed</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red">{result.evaluation.summary.failed}</div>
                  <div className="text-xs text-muted uppercase tracking-wide">Failed</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">{result.evaluation.summary.total}</div>
                  <div className="text-xs text-muted uppercase tracking-wide">Total</div>
                </div>
              </div>

              <div className="mt-4 border-t border-[rgba(255,255,255,0.08)] pt-4">
                <h4 className="text-xs font-bold text-muted uppercase tracking-wider mb-3">Metrics</h4>
                <div className="grid-2 gap-4">
                  <div className="bg-[rgba(255,255,255,0.03)] p-3 rounded-lg border border-[rgba(255,255,255,0.05)]">
                    <div className="text-xs text-muted mb-1">Accuracy</div>
                    <div className="text-sm font-bold">{result.evaluation.metrics.accuracy_pct}%</div>
                  </div>
                  <div className="bg-[rgba(255,255,255,0.03)] p-3 rounded-lg border border-[rgba(255,255,255,0.05)]">
                    <div className="text-xs text-muted mb-1">Latency p95</div>
                    <div className="text-sm font-bold">{result.evaluation.metrics.latency_p95_ms}ms</div>
                  </div>
                  <div className="bg-[rgba(255,255,255,0.03)] p-3 rounded-lg border border-[rgba(255,255,255,0.05)]">
                    <div className="text-xs text-muted mb-1">Avg Tokens</div>
                    <div className="text-sm font-bold">{result.evaluation.metrics.avg_tokens}</div>
                  </div>
                  <div className="bg-[rgba(255,255,255,0.03)] p-3 rounded-lg border border-[rgba(255,255,255,0.05)]">
                    <div className="text-xs text-muted mb-1">Retry Rate</div>
                    <div className="text-sm font-bold">{result.evaluation.metrics.retry_rate_pct}%</div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card flex items-center justify-center text-muted">
              No test cases defined for this skill
            </div>
          )}
        </div>
      )}
    </div>
  )
}

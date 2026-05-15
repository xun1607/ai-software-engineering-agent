import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { evaluationApi, skillsApi, SkillSummary, DocReview, ValidationResult } from '../api/client'
import { Play, CheckCircle, XCircle, Settings, Save, RefreshCw, ShieldCheck, Code } from 'lucide-react'

export default function EvaluationPage() {
  const location = useLocation()
  const initialSkillId = location.state?.skillId || ''
  
  const [activeTab, setActiveTab] = useState<'evaluation' | 'criteria' | 'validation'>('evaluation')
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [selectedSkill, setSelectedSkill] = useState(initialSkillId)
  const [result, setResult] = useState<DocReview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  const [criteriaXml, setCriteriaXml] = useState('')
  const [criteriaLoading, setCriteriaLoading] = useState(false)
  const [criteriaSaving, setCriteriaSaving] = useState(false)

  const [valResult, setValResult] = useState<ValidationResult | null>(null)
  const [valXml, setValXml] = useState('')
  const [valLoading, setValLoading] = useState(false)

  useEffect(() => {
    skillsApi.list().then(res => setSkills(res.items)).catch(console.error)
    loadCriteria()
  }, [])

  const loadCriteria = async () => {
    setCriteriaLoading(true)
    try {
      const xml = await evaluationApi.getCriteria()
      setCriteriaXml(xml)
    } catch (err) {
      console.error('Failed to load criteria', err)
    } finally {
      setCriteriaLoading(false)
    }
  }

  const handleSaveCriteria = async () => {
    setCriteriaSaving(true)
    try {
      await evaluationApi.updateCriteria(criteriaXml)
      alert('Criteria updated successfully')
    } catch (err: any) {
      alert('Failed to update criteria: ' + (err.response?.data?.detail || err.message))
    } finally {
      setCriteriaSaving(false)
    }
  }

  const handleEvaluate = async () => {
    if (!selectedSkill) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await evaluationApi.evaluateDoc(selectedSkill)
      setResult(res)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async () => {
    if (!selectedSkill) return
    setValLoading(true)
    try {
      const [res, xml] = await Promise.all([
        evaluationApi.validateSkill(selectedSkill),
        evaluationApi.getSkillXml(selectedSkill)
      ])
      setValResult(res)
      setValXml(xml)
    } catch (err: any) {
      setError('Validation failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setValLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header flex justify-between items-center">
        <div>
          <h2>Evaluation & Validation</h2>
          <p>Review quality and validate structure against XML Schemas</p>
        </div>
        <div className="flex gap-2 bg-[rgba(255,255,255,0.05)] p-1 rounded-lg">
          <button 
            className={`btn btn-sm ${activeTab === 'evaluation' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab('evaluation')}
          >
            <Play size={14} /> Doc Review
          </button>
          <button 
            className={`btn btn-sm ${activeTab === 'validation' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab('validation')}
          >
            <ShieldCheck size={14} /> XML Validation
          </button>
          <button 
            className={`btn btn-sm ${activeTab === 'criteria' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab('criteria')}
          >
            <Settings size={14} /> Criteria XML
          </button>
        </div>
      </div>

      {(activeTab === 'evaluation' || activeTab === 'validation') && (
        <div className="card mb-6 flex gap-3 items-end">
          <div className="form-group mb-0 flex-1">
            <label className="form-label">Select Skill</label>
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
            onClick={activeTab === 'evaluation' ? handleEvaluate : handleValidate} 
            disabled={!selectedSkill || loading || valLoading}
            style={{ height: 40 }}
          >
            {(loading || valLoading) ? <div className="spinner" style={{ width: 16, height: 16 }} /> : <Play size={16} />} 
            {activeTab === 'evaluation' ? 'Run Doc Review' : 'Run XML Validation'}
          </button>
        </div>
      )}

      {error && (
        <div className="card mb-6" style={{ borderColor: 'var(--red)', background: 'rgba(248,113,113,0.05)' }}>
          <h3 className="text-red font-bold flex items-center gap-2"><XCircle size={18} /> Error</h3>
          <p className="mt-2 text-sm">{error}</p>
        </div>
      )}

      {activeTab === 'evaluation' && result && (
        <div className="flex justify-center">
          <div className="card" style={{ maxWidth: 700, width: '100%' }}>
            <h3 className="font-bold text-sm mb-4">Documentation Score</h3>
            <div className={`score-circle ${result.passed ? 'pass' : 'fail'}`}>
              <div className="score-num">{result.doc_score}</div>
              <div className="score-denom">/ {result.max_score}</div>
            </div>
            <div className="text-center mb-6">
              <span className={`badge ${result.passed ? 'badge-pass' : 'badge-fail'}`}>
                {result.passed ? 'PASSED' : 'FAILED'}
              </span>
              <div className="text-xs text-muted mt-2">Threshold: {result.threshold}</div>
            </div>
            
            <div className="mt-4 border-t border-[rgba(255,255,255,0.08)] pt-4">
              {result.criteria.map((c, i) => (
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
        </div>
      )}

      {activeTab === 'validation' && valResult && (
        <div className="flex flex-col gap-6">
          <div className="grid-2">
            <div className="card">
              <h3 className="font-bold mb-4 flex items-center gap-2">
                <ShieldCheck size={18} className="text-accent" /> XSD Content Validation
              </h3>
              <div className="flex items-center gap-3 mb-4">
                <div className={`status-dot ${valResult.content.valid ? 'bg-green' : 'bg-red'}`} style={{ width: 12, height: 12, borderRadius: '50%' }} />
                <span className={`font-bold ${valResult.content.valid ? 'text-green' : 'text-red'}`}>
                  {valResult.content.valid ? 'SCHEMA VALID' : 'SCHEMA INVALID'}
                </span>
              </div>
              {!valResult.content.valid && (
                <div className="mt-2 p-3 bg-[rgba(248,113,113,0.1)] rounded border border-[rgba(248,113,113,0.2)]">
                  <h4 className="text-xs font-bold text-red uppercase mb-2">Schema Errors:</h4>
                  {valResult.content.errors.map((err, i) => (
                    <div key={i} className="text-xs text-red mb-1">• {err}</div>
                  ))}
                </div>
              )}
              <p className="mt-4 text-xs text-muted">
                This check converts the skill to XML and validates it against <code>skill.xsd</code>.
              </p>
            </div>
            
            <div className="card">
              <h3 className="font-bold mb-4 flex items-center gap-2">
                <ShieldCheck size={18} className="text-accent" /> Format Validation
              </h3>
              <div className="flex items-center gap-3">
                <div className={`status-dot ${valResult.format.valid ? 'bg-green' : 'bg-red'}`} style={{ width: 12, height: 12, borderRadius: '50%' }} />
                <span className={`font-bold ${valResult.format.valid ? 'text-green' : 'text-red'}`}>
                  {valResult.format.valid ? 'FORMAT VALID' : 'FORMAT INVALID'}
                </span>
              </div>
              {!valResult.format.valid && (
                <div className="mt-3 p-3 bg-[rgba(248,113,113,0.1)] rounded border border-[rgba(248,113,113,0.2)]">
                  <h4 className="text-xs font-bold text-red uppercase mb-2">Format Errors:</h4>
                  {valResult.format.errors.map((err, i) => (
                    <div key={i} className="text-xs text-red mb-1">• {err}</div>
                  ))}
                </div>
              )}
              <p className="mt-4 text-xs text-muted">
                Checks for essential Markdown structure and YAML frontmatter.
              </p>
            </div>
          </div>

          <div className="card">
            <h3 className="font-bold mb-4 flex items-center gap-2"><Code size={18} /> Generated XML</h3>
            <pre className="code-block" style={{ fontSize: 12, maxHeight: 400, overflow: 'auto', background: 'rgba(0,0,0,0.3)' }}>
              {valXml}
            </pre>
          </div>
        </div>
      )}

      {activeTab === 'criteria' && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="font-bold">Evaluation Criteria (XML)</h3>
              <p className="text-xs text-muted">Define the rules for automated documentation review</p>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-secondary btn-sm" onClick={loadCriteria} disabled={criteriaLoading}>
                <RefreshCw size={14} /> Reload
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleSaveCriteria} disabled={criteriaSaving}>
                <Save size={14} /> {criteriaSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
          
          {criteriaLoading ? (
            <div className="loading-center" style={{ height: 300 }}><div className="spinner" /></div>
          ) : (
            <textarea
              className="form-input form-textarea"
              value={criteriaXml}
              onChange={e => setCriteriaXml(e.target.value)}
              style={{ minHeight: 500, fontFamily: 'var(--font-mono)', fontSize: 13, background: 'rgba(0,0,0,0.2)' }}
            />
          )}
        </div>
      )}
    </div>
  )
}

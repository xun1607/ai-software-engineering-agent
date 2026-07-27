import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { skillsApi, SkillRead } from '../api/client'
import { ArrowLeft, Edit, Trash2, Download, Play, CheckCircle, Save, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

export default function SkillDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [skill, setSkill] = useState<SkillRead | null>(null)
  const [loading, setLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [editedInstruction, setEditedInstruction] = useState('')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState('')

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const load = () => {
    if (!id) return
    setLoading(true)
    skillsApi.get(id)
      .then(setSkill)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [id])

  const handleDelete = async () => {
    if (!skill || !confirm(`Delete skill "${skill.name}"?`)) return
    try {
      await skillsApi.delete(skill.id)
      navigate('/skills')
    } catch (e) {
      showToast('❌ Delete failed')
    }
  }

  const handleSave = async () => {
    if (!skill) return
    setSaving(true)
    try {
      await skillsApi.update(skill.id, { full_markdown: editedInstruction })
      showToast('✅ Skill updated successfully')
      setIsEditing(false)
      load()
    } catch (err: any) {
      showToast(`❌ Update failed: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (!skill) return <div className="empty-state">Skill not found</div>

  const stripFrontmatter = (content: string) => {
    return content.replace(/^---[\s\S]*?---\s*/, '')
  }

  const renderedContent = stripFrontmatter(skill.raw_content || '')

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button className="btn btn-ghost" onClick={() => navigate('/skills')}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex-1">
          <h2 style={{ fontSize: 24, fontWeight: 700, margin: 0, fontFamily: 'var(--font-mono)' }}>{skill.name}</h2>
          <div className="flex gap-2 items-center mt-1">
            <span className={`badge badge-${skill.level}`}>{skill.level}</span>
            <span className="text-sm text-muted">{skill.category}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <a className="btn btn-secondary" href={skillsApi.exportUrl(skill.id)} download>
            <Download size={14} /> Export
          </a>
          <button className="btn btn-danger" onClick={handleDelete}>
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>

      <div className="grid-3" style={{ gridTemplateColumns: '2fr 1fr' }}>
        <div className="flex" style={{ flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-sm">Instructions (.md)</h3>
              <div className="flex gap-2">
                <button
                  className={`btn btn-sm ${isEditing ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => {
                    if (isEditing) {
                      handleSave()
                    } else {
                      setEditedInstruction(skill.raw_content)
                      setIsEditing(true)
                    }
                  }}
                  disabled={saving}
                >
                  {isEditing ? (saving ? 'Saving...' : <><Save size={12} /> Save</>) : <><Edit size={12} /> Edit</>}
                </button>
                {isEditing && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsEditing(false)}
                    disabled={saving}
                  >
                    <X size={12} /> Cancel
                  </button>
                )}
              </div>
            </div>

            {isEditing ? (
              <textarea
                className="form-input form-textarea"
                value={editedInstruction}
                onChange={e => setEditedInstruction(e.target.value)}
                style={{ minHeight: 600, fontFamily: 'var(--font-mono)', fontSize: 13, background: 'rgba(0,0,0,0.3)', color: '#fff' }}
                placeholder="Enter full SKILL.md content..."
              />
            ) : (
              <div className="markdown-container">
                <div className="markdown-body">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus as any}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {renderedContent || 'No content found.'}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-sm">Action Shortcuts</h3>
            </div>
            <div className="flex gap-3">
              <button className="btn btn-primary" onClick={() => navigate('/evaluation', { state: { skillId: skill.id } })}>
                <CheckCircle size={14} /> Evaluate
              </button>
              <button className="btn btn-secondary" onClick={() => navigate('/testing', { state: { skillId: skill.id } })}>
                <Play size={14} /> Test
              </button>
            </div>
          </div>
        </div>

        <div className="flex" style={{ flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <h3 className="font-bold text-sm mb-3">Metadata</h3>
            <div className="mb-3">
              <div className="text-xs text-muted mb-1 uppercase tracking-wider">Description</div>
              <div className="text-sm">{skill.metadata?.description || '—'}</div>
            </div>
            {skill.metadata?.goal && (
              <div className="mb-3">
                <div className="text-xs text-muted mb-1 uppercase tracking-wider">Goal</div>
                <div className="text-sm">{skill.metadata.goal}</div>
              </div>
            )}
            <div className="mb-3">
              <div className="text-xs text-muted mb-1 uppercase tracking-wider">Tags</div>
              <div className="flex flex-wrap gap-2 mt-1">
                {skill.tags.map((t: string) => <span key={t} className="badge badge-tag">{t}</span>)}
              </div>
            </div>
            {(skill.metadata?.sub_skills || []).length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-muted mb-1 uppercase tracking-wider">Sub Skills</div>
                <div className="flex flex-col gap-1 mt-1">
                  {(skill.metadata.sub_skills || []).map((s: string) => <div key={s} className="text-sm font-mono text-accent">{s}</div>)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}

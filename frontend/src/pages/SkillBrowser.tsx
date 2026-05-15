import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { skillsApi, SkillSummary } from '../api/client'
import { Search, Plus, Upload, RefreshCw, X, Folder, FolderOpen, FileText } from 'lucide-react'

interface TreeNode {
  name: string
  skills: SkillSummary[]
  children: { [key: string]: TreeNode }
}

function buildTree(skills: SkillSummary[]): TreeNode {
  const root: TreeNode = { name: 'Root', skills: [], children: {} }
  
  skills.forEach(skill => {
    const parts = skill.category.split('/')
    let current = root
    parts.forEach(part => {
      if (!current.children[part]) {
        current.children[part] = { name: part, skills: [], children: {} }
      }
      current = current.children[part]
    })
    current.skills.push(skill)
  })
  
  return root
}

export default function SkillBrowser() {
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQ, setSearchQ] = useState('')
  const [searching, setSearching] = useState(false)
  const [filterLevel, setFilterLevel] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [importing, setImporting] = useState(false)
  const [toast, setToast] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'tree'>('grid')
  const navigate = useNavigate()

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const load = useCallback(() => {
    setLoading(true)
    skillsApi.list({ level: filterLevel || undefined, category: filterCategory || undefined })
      .then(d => setSkills(d.items))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filterLevel, filterCategory])

  useEffect(() => { load() }, [load])

  const handleSearch = async () => {
    if (!searchQ.trim()) return load()
    setSearching(true)
    try {
      const res = await skillsApi.search(searchQ, 10)
      setSkills(res.results.map(r => r.skill))
    } finally {
      setSearching(false)
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      await skillsApi.importFile(file)
      showToast('✅ Skill imported successfully')
      load()
    } catch (err: any) {
      showToast(`❌ Import failed: ${err.response?.data?.detail || err.message}`)
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (id: string, name: string, ev: React.MouseEvent) => {
    ev.stopPropagation()
    if (!confirm(`Delete skill "${name}"?`)) return
    try {
      await skillsApi.delete(id)
      showToast('Skill deleted')
      load()
    } catch { showToast('Delete failed') }
  }

  const categories = [...new Set(skills.map(s => s.category))].sort()

  return (
    <div>
      <div className="page-header flex items-center justify-between">
        <div>
          <h2>Skill Browser</h2>
          <p>Browse and manage your skill library</p>
        </div>
        <div className="flex gap-2">
          <label className="btn btn-secondary btn-sm" style={{ cursor: importing ? 'not-allowed' : 'pointer' }}>
            <Upload size={13} /> {importing ? 'Importing...' : 'Import .md'}
            <input type="file" accept=".md" style={{ display: 'none' }} onChange={handleImport} />
          </label>
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
            <Plus size={13} /> New Skill
          </button>
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="flex gap-2 mb-4">
        <button 
          className={`btn btn-sm ${viewMode === 'grid' ? 'btn-primary' : 'btn-secondary'}`} 
          onClick={() => setViewMode('grid')}
        >
          Grid View
        </button>
        <button 
          className={`btn btn-sm ${viewMode === 'tree' ? 'btn-primary' : 'btn-secondary'}`} 
          onClick={() => setViewMode('tree')}
        >
          Hierarchy View
        </button>
      </div>

      {/* Search + Filters */}
      <div className="flex gap-3 mb-6" style={{ flexWrap: 'wrap' }}>
        <div className="search-bar" style={{ flex: '1 1 300px' }}>
          <Search size={14} className="search-icon" />
          <input
            placeholder="Search skills by name, description, tags..."
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <select className="form-input form-select" style={{ width: 160 }}
          value={filterLevel} onChange={e => { setFilterLevel(e.target.value); setSearchQ('') }}>
          <option value="">All Levels</option>
          <option value="atomic">Atomic</option>
          <option value="composite">Composite</option>
        </select>
        <select className="form-input form-select" style={{ width: 200 }}
          value={filterCategory} onChange={e => { setFilterCategory(e.target.value); setSearchQ('') }}>
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <button className="btn btn-secondary btn-sm" onClick={() => { setSearchQ(''); setFilterLevel(''); setFilterCategory(''); load() }}>
          <RefreshCw size={13} />
        </button>
      </div>

      {/* Content */}
      {loading || searching ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : skills.length === 0 ? (
        <div className="empty-state">
          <h3>No skills found</h3>
          <p>Import a SKILL.md file or create a new skill to get started.</p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="skill-grid">
          {skills.map(skill => (
            <div key={skill.id} className="skill-card" onClick={() => navigate(`/skills/${skill.id}`)}>
              <div className="skill-card-header">
                <span className="skill-card-name">{skill.name}</span>
                <span className={`badge badge-${skill.level}`}>{skill.level}</span>
              </div>
              <p className="skill-card-desc">{skill.description}</p>
              <div className="skill-card-meta">
                {skill.tags.slice(0, 4).map(t => (
                  <span key={t} className="badge badge-tag">{t}</span>
                ))}
                {skill.tags.length > 4 && <span className="badge badge-tag">+{skill.tags.length - 4}</span>}
              </div>
              <div className="skill-card-footer">
                <span className="skill-card-category">{skill.category}</span>
                <div className="flex gap-2" onClick={e => e.stopPropagation()}>
                  <span className="text-xs text-muted">v{skill.version}</span>
                  <button className="btn btn-ghost btn-sm text-red" style={{ padding: '2px 6px' }}
                    onClick={e => handleDelete(skill.id, skill.name, e)}>
                    <X size={12} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <TreeView skills={skills} navigate={navigate} />
      )}

      {showCreate && <CreateSkillModal onClose={() => setShowCreate(false)} onCreated={() => { load(); setShowCreate(false); showToast('✅ Skill created!') }} />}
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}

function TreeView({ skills, navigate }: { skills: SkillSummary[], navigate: any }) {
  const tree = buildTree(skills)
  
  return (
    <div className="card" style={{ background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(12px)' }}>
      <h3 className="font-bold text-sm mb-4 border-b border-[rgba(255,255,255,0.08)] pb-2">Skill Hierarchy</h3>
      <div className="pl-2">
        {Object.values(tree.children).map(node => (
          <TreeNodeView key={node.name} node={node} level={0} navigate={navigate} />
        ))}
      </div>
    </div>
  )
}

function TreeNodeView({ node, level, navigate }: { node: TreeNode, level: number, navigate: any }) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = Object.keys(node.children).length > 0 || node.skills.length > 0
  
  return (
    <div style={{ marginLeft: level > 0 ? 20 : 0 }}>
      <div 
        className="flex items-center gap-2 py-2 cursor-pointer hover:text-accent transition-colors"
        onClick={() => setExpanded(!expanded)}
        style={{ fontSize: 15 }}
      >
        <span className="text-muted" style={{ width: 16, display: 'inline-block' }}>
          {hasChildren ? (expanded ? '▼' : '▶') : ' '}
        </span>
        {hasChildren ? (
          expanded ? <FolderOpen size={16} className="text-yellow-400" /> : <Folder size={16} className="text-yellow-400" />
        ) : (
          <Folder size={16} className="text-yellow-400" />
        )}
        <span className="font-semibold text-slate-200">{node.name}</span>
      </div>
      
      {expanded && (
        <div className="border-l border-[rgba(255,255,255,0.05)] ml-2">
          {Object.values(node.children).map(child => (
            <TreeNodeView key={child.name} node={child} level={level + 1} navigate={navigate} />
          ))}
          {node.skills.map(skill => (
            <div 
              key={skill.id} 
              className="flex items-center gap-2 py-2 cursor-pointer hover:bg-[rgba(255,255,255,0.02)] pl-6 transition-colors"
              onClick={() => navigate(`/skills/${skill.id}`)}
              style={{ fontSize: 14 }}
            >
              <FileText size={14} className="text-cyan-400" />
              <span className="text-slate-300">{skill.name}</span>
              <span className={`badge badge-${skill.level} text-xs`} style={{ transform: 'scale(0.8)' }}>{skill.level}</span>
              <span className="text-xs text-muted ml-auto">{(skill.description || '').slice(0, 60)}...</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CreateSkillModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '', description: '', version: '1.0.0', level: 'atomic',
    category: '', goal: '', tags: '', instruction: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setLoading(true); setError('')
    try {
      await skillsApi.create({
        metadata: {
          name: form.name, description: form.description, version: form.version,
          level: form.level as 'atomic' | 'composite', category: form.category,
          goal: form.goal || undefined,
          tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
          sub_skills: [],
        },
        instruction: form.instruction,
      })
      onCreated()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create skill')
    } finally { setLoading(false) }
  }

  const f = (k: string) => (e: React.ChangeEvent<any>) => setForm(p => ({ ...p, [k]: e.target.value }))

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }}>
      <div className="card" style={{ width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold">Create New Skill</h3>
          <button className="btn btn-ghost" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Name *</label>
            <input className="form-input" placeholder="e.g. debug-python-error" value={form.name} onChange={f('name')} />
          </div>
          <div className="form-group">
            <label className="form-label">Version</label>
            <input className="form-input" value={form.version} onChange={f('version')} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Description *</label>
          <input className="form-input" placeholder="Brief description of what this skill does" value={form.description} onChange={f('description')} />
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Category *</label>
            <input className="form-input" placeholder="e.g. python/debugging" value={form.category} onChange={f('category')} />
          </div>
          <div className="form-group">
            <label className="form-label">Level</label>
            <select className="form-input form-select" value={form.level} onChange={f('level')}>
              <option value="atomic">Atomic</option>
              <option value="composite">Composite</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Goal</label>
          <input className="form-input" placeholder="Specific goal of this skill" value={form.goal} onChange={f('goal')} />
        </div>
        <div className="form-group">
          <label className="form-label">Tags (comma separated)</label>
          <input className="form-input" placeholder="python, debug, error" value={form.tags} onChange={f('tags')} />
        </div>
        <div className="form-group">
          <label className="form-label">Instructions *</label>
          <textarea className="form-input form-textarea" placeholder="Step-by-step instructions for the AI agent..." value={form.instruction} onChange={f('instruction')} style={{ minHeight: 140 }} />
        </div>
        {error && <p style={{ color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>{error}</p>}
        <div className="flex gap-2">
          <button className="btn btn-secondary flex-1" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary flex-1" onClick={submit} disabled={loading || !form.name || !form.description || !form.category || !form.instruction}>
            {loading ? 'Creating...' : 'Create Skill'}
          </button>
        </div>
      </div>
    </div>
  )
}

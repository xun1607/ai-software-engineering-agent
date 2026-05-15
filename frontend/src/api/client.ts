import axios from 'axios'

const BASE = {
  management: '/api/management',
  evaluation: '/api/evaluation',
  testing: '/api/testing',
  reporting: '/api/reporting',
}

const mgmt = axios.create({ baseURL: BASE.management })
const eval_ = axios.create({ baseURL: BASE.evaluation })
const test_ = axios.create({ baseURL: BASE.testing })
const report = axios.create({ baseURL: BASE.reporting })

// ── Types ─────────────────────────────────────────────────────────────────

export interface SkillMetadata {
  name: string
  version: string
  level: string
  category: string
  tags: string[]
  description?: string
  goal?: string
  sub_skills?: string[]
  [key: string]: any
}

export interface SkillSummary extends SkillMetadata {
  id: string
  metadata: Record<string, any>
  updated_at: string
}

export interface SkillRead extends SkillSummary {
  raw_content: string
  full_markdown: string
}

export interface SkillList {
  items: SkillSummary[]
  total: number
}

export interface SkillSearchResult {
  skill: SkillSummary
  score: number
}

export interface DocCriterion {
  id: string
  layer: string
  description: string
  points: number
  passed: boolean
  note: string
}

export interface DocReview {
  skill_id?: string
  skill_name: string
  doc_score: number
  max_score: number
  passed: boolean
  threshold: number
  criteria: DocCriterion[]
}

export interface EvaluationReport {
  skill_id?: string
  skill_name: string
  skill_version: string
  mock_mode: boolean
  summary: { total: number; passed: number; failed: number; pass_rate_pct: number }
  metrics: { accuracy_pct: number; latency_p50_ms: number; latency_p95_ms: number; avg_tokens: number; retry_rate_pct: number }
  metric_checks: Record<string, boolean>
  test_results: Array<{
    id: string; name: string; passed: boolean; latency_ms: number
    tokens: number; retries: number; error: string
    criteria: Array<{ expr: string; passed: boolean; error: string }>
  }>
}

export interface FullEvaluation {
  doc_review?: DocReview
  evaluation?: EvaluationReport
}

export interface DashboardData {
  skills: { total: number }
  evaluations: { total: number }
  test_runs: { total: number; passed: number; pass_rate: number }
  doc_reviews: { total: number; passed: number; pass_rate: number }
  by_category: Record<string, number>
  by_level: Record<string, number>
  registry_loaded: number
}

// ── Management API ────────────────────────────────────────────────────────

export const skillsApi = {
  list: (params?: { category?: string; level?: string; tag?: string }) =>
    mgmt.get<SkillList>('/skills', { params }).then(r => r.data),

  search: (q: string, top_k = 5) =>
    mgmt.get<{ query: string; results: SkillSearchResult[] }>('/skills/search', { params: { q, top_k } }).then(r => r.data),

  get: (id: string) =>
    mgmt.get<SkillRead>(`/skills/${id}`).then(r => r.data),

  create: (payload: { metadata: SkillMetadata; instruction: string }) =>
    mgmt.post<SkillRead>('/skills', payload).then(r => r.data),

  update: (id: string, payload: { metadata?: Record<string, any>; instruction?: string; full_markdown?: string; raw_content?: string }) =>
    mgmt.put<SkillRead>(`/skills/${id}`, payload).then(r => r.data),

  delete: (id: string, removeFile = false) =>
    mgmt.delete(`/skills/${id}`, { params: { remove_file: removeFile } }).then(r => r.data),

  importFile: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return mgmt.post<SkillRead>('/skills/import', form).then(r => r.data)
  },

  exportUrl: (id: string) => `${BASE.management}/skills/${id}/export`,

  registryStatus: () =>
    mgmt.get('/registry/status').then(r => r.data),

  registryReload: () =>
    mgmt.post('/registry/reload').then(r => r.data),
}

// ── Evaluation API ────────────────────────────────────────────────────────

export const evaluationApi = {
  evaluateDoc: (skillId: string) =>
    eval_.post<DocReview>(`/evaluate/${skillId}/doc`).then(r => r.data),

  evaluateRun: (skillId: string, mockMode = true) =>
    eval_.post<EvaluationReport>(`/evaluate/${skillId}/run`, { mock_mode: mockMode }).then(r => r.data),

  evaluateAll: (skillId: string, mockMode = true) =>
    eval_.post<FullEvaluation>(`/evaluate/${skillId}/all`, { mock_mode: mockMode }).then(r => r.data),

  history: (skillId: string) =>
    eval_.get(`/evaluate/${skillId}/history`).then(r => r.data),
}

// ── Testing API ───────────────────────────────────────────────────────────

export const testingApi = {
  runSkillTests: (skillId: string, mockMode = true) =>
    test_.post(`/tests/run/${skillId}`, { mock_mode: mockMode }).then(r => r.data),

  getResults: (skillId: string) =>
    test_.get(`/tests/${skillId}/results`).then(r => r.data),

  chat: (messages: {role: string, content: string}[], model: string, apiKey: string) =>
    test_.post(`/tests/chat`, { messages, model, api_key: apiKey }).then(r => r.data),

  orchestrate: (task: string) =>
    test_.post(`/orchestrate`, { task }).then(r => r.data),
}

// ── Reporting API ─────────────────────────────────────────────────────────

export const reportingApi = {
  dashboard: () =>
    report.get<DashboardData>('/reports/dashboard').then(r => r.data),

  skillsSummary: () =>
    report.get('/reports/skills/summary').then(r => r.data),

  testsSummary: () =>
    report.get('/reports/tests/summary').then(r => r.data),

  evaluationsSummary: () =>
    report.get('/reports/evaluations/summary').then(r => r.data),

  docReviewsSummary: () =>
    report.get('/reports/doc-reviews/summary').then(r => r.data),

  registryStatus: () =>
    report.get('/reports/registry/status').then(r => r.data),

  skillHistory: (skillId: string) =>
    report.get(`/reports/skills/${skillId}/history`).then(r => r.data),
}

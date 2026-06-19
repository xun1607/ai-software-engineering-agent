import { useState, useRef, useEffect } from 'react'
import { testingApi } from '../api/client'
import { Play, Settings, Send, User, Bot, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

export default function TestingPage() {
  const [messages, setMessages] = useState<{role: string, content: string}[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'agent' | 'orchestrator' | 'test_suite'>('agent')
  const [model, setModel] = useState('deepseek-chat')
  const [apiKey, setApiKey] = useState('')
  const [showSettings, setShowSettings] = useState(true)
  
  // Test Suite States
  const [testResults, setTestResults] = useState<any[]>([])
  const [suiteSummary, setSuiteSummary] = useState<any | null>(null)
  const [suiteLoading, setSuiteLoading] = useState(false)

  // Toggle active log folders on Frontend UI
  const [expandedLogs, setExpandedLogs] = useState<Record<string, boolean>>({})

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const toggleLog = (id: string) => {
    setExpandedLogs(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const handleRunTestSuite = async () => {
    setTestResults([])
    setSuiteSummary(null)
    setSuiteLoading(true)
    setExpandedLogs({})

    try {
      const response = await fetch('http://127.0.0.1:8002/api/orchestrate/run-test-suite', {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error(`Server API trả về mã lỗi: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      if (reader) {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const cleanedLine = line.trim()
            if (cleanedLine.startsWith('data: ')) {
              try {
                const dataStr = cleanedLine.slice(6)
                const data = JSON.parse(dataStr)

                if (data.status === 'RUNNING') {
                  setTestResults(prev => {
                    const idx = prev.findIndex(r => r.id === data.id)
                    if (idx > -1) {
                      const updated = [...prev]
                      updated[idx] = { ...updated[idx], status: 'RUNNING', message: data.message, steps: updated[idx].steps || [] }
                      return updated
                    } else {
                      return [...prev, { id: data.id, status: 'RUNNING', message: data.message, steps: [] }]
                    }
                  })
                } else if (data.status === 'STEP') {
                  setTestResults(prev => {
                    const idx = prev.findIndex(r => r.id === data.id)
                    if (idx > -1) {
                      const updated = [...prev]
                      const currentSteps = updated[idx].steps || []
                      const stepExists = currentSteps.some((s: any) => s.node === data.node && s.step_count === data.step_count)
                      if (!stepExists) {
                        const newStep = {
                          node: data.node,
                          step_count: data.step_count,
                          current_step_idx: data.current_step_idx,
                          plan: data.plan,
                          last_observation: data.last_observation,
                          selected_skill: data.selected_skill
                        }
                        updated[idx] = {
                          ...updated[idx],
                          message: `Đang chạy: ${data.node} (Bước ${data.step_count})`,
                          steps: [...currentSteps, newStep]
                        }
                      }
                      return updated
                    }
                    return prev
                  })
                } else if (data.status === 'COMPLETED') {
                  setTestResults(prev => {
                    const idx = prev.findIndex(r => r.id === data.id)
                    const updated = [...prev]
                    const completedItem = {
                      id: data.id,
                      status: 'COMPLETED',
                      passed: data.passed,
                      step_count: data.step_count,
                      final_answer: data.final_answer,
                      latency: data.latency,
                      steps: idx > -1 ? (updated[idx].steps || []) : []
                    }
                    if (idx > -1) {
                      updated[idx] = completedItem
                    } else {
                      updated.push(completedItem)
                    }
                    return updated
                  })
                  // Tự động mở rộng xem logs khi một test case hoàn thành
                  setExpandedLogs(prev => ({ ...prev, [data.id]: true }))
                } else if (data.status === 'SUMMARY') {
                  setSuiteSummary(data)
                }
              } catch (e) {
                // Bỏ qua lỗi parse dở dang
              }
            }
          }
        }
      }
    } catch (err: any) {
      console.error(err)
      alert(`Lỗi chạy test suite: ${err.message}`)
    } finally {
      setSuiteLoading(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim()) return
    
    const newMessages = [...messages, { role: 'user', content: input }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    
    try {
      if (mode === 'orchestrator') {
        // 1. Tạo tin nhắn Assistant rỗng để bắt đầu hiển thị tiến trình
        setMessages([...newMessages, { role: 'assistant', content: '📡 Connecting to AG2 Orchestrator...' }])
        
        // Trích xuất mã nguồn nếu người dùng paste block code dạng ```java ... ```
        const codeMatch = input.match(/```(?:java)?\s*([\s\S]*?)\s*```/)
        const codeContent = codeMatch ? codeMatch[1] : `public class LoginService {
    // Dòng 42 bị NullPointerException
    public void login(User user) {
        String name = user.getName();
    }
}`
        const filename = "LoginService.java"
        const stacktrace = input.includes("error") || input.includes("Exception") ? input : "NullPointerException at LoginService:42"

        // 2. Gửi request SSE tới AG2 Orchestrator Server (cổng 8002)
        const response = await fetch('http://127.0.0.1:8002/api/orchestrate/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code_content: codeContent,
            filename: filename,
            stacktrace: stacktrace,
            message: input
          })
        })

        if (!response.ok) {
          throw new Error(`Server API trả về mã lỗi: ${response.status}`)
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        let assistantContent = '📡 Đang kết nối và khởi tạo AG2 Orchestrator...\n\n'
        
        if (reader) {
          while (true) {
            const { value, done } = await reader.read()
            if (done) break
            
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              const cleanedLine = line.trim()
              if (cleanedLine.startsWith('data: ')) {
                try {
                  const dataStr = cleanedLine.slice(6)
                  const data = JSON.parse(dataStr)
                  
                  if (data.error) {
                    assistantContent += `❌ **Lỗi hệ thống:** ${data.error}\n`
                  } else {
                    const { node, step_count, plan, last_observation, is_finished, final_answer } = data
                    
                    // Định dạng tiến trình hiển thị
                    assistantContent = `🤖 **AG2 ORCHESTRATOR PROGRESS** (Bước ${step_count})\n`
                    assistantContent += `========================================\n\n`
                    
                    if (plan && plan.length > 0) {
                      assistantContent += `📝 **Kế hoạch hành động:**\n`
                      plan.forEach((step: string, idx: number) => {
                        assistantContent += `  ${idx + 1}. ${step}\n`
                      })
                      assistantContent += `\n`
                    }
                    
                    assistantContent += `⚙️ **Đang xử lý tại node:** \`${node}\`\n\n`
                    
                    if (last_observation) {
                      // Format observation JSON cho đẹp mắt
                      let obsText = last_observation
                      try {
                        const obsJson = JSON.parse(last_observation)
                        obsText = JSON.stringify(obsJson, null, 2)
                      } catch (e) {}
                      assistantContent += `📦 **Quan sát (Observation):**\n\`\`\`json\n${obsText}\n\`\`\`\n\n`
                    }
                    
                    if (is_finished) {
                      assistantContent += `========================================\n`
                      assistantContent += `🏁 **Kết quả cuối cùng:**\n${final_answer}\n`
                    }
                  }
                  
                  // Cập nhật giao diện theo thời gian thực
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
                    return updated
                  })
                  
                } catch (e) {
                  // Bỏ qua lỗi parse dở dang
                }
              }
            }
          }
        }
      } else {
        const res = await testingApi.chat(newMessages, model, apiKey)
        setMessages(res.messages)
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Chat failed'
      setMessages([...newMessages, { role: 'assistant', content: `**Error:** ${errorMsg}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-container flex gap-6">
      {/* Main Area */}
      <div className="flex-1 flex flex-col bg-[var(--bg-card)] rounded-xl border border-[var(--border)] overflow-hidden">
        {mode === 'test_suite' ? (
          /* Test Suite Panel */
          <div className="flex-1 flex flex-col bg-[#0a0f18] p-6 overflow-y-auto space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center border-b border-[var(--border)] pb-4">
              <div>
                <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-[var(--accent)] to-[#60a5fa]">
                  Test Suite Realtime Runner
                </h2>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Khởi chạy chuỗi kịch bản kiểm thử tích hợp và xem dòng tiến trình SSE thời gian thực.
                </p>
              </div>
              <button
                className="btn btn-primary flex items-center gap-2"
                onClick={handleRunTestSuite}
                disabled={suiteLoading}
              >
                {suiteLoading ? (
                  <div className="spinner" style={{ width: 16, height: 16 }} />
                ) : (
                  <Play size={16} />
                )}
                Run Test Suite
              </button>
            </div>

            {/* Suite Summary Card */}
            {suiteSummary && (
              <div className="p-6 rounded-xl border border-[rgba(255,255,255,0.06)] bg-gradient-to-r from-[#101b2d] to-[#0d1525] shadow-lg flex justify-between items-center animate-fade-in">
                <div>
                  <h4 className="text-xs font-bold text-muted uppercase tracking-wider">Test Suite Summary</h4>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">
                      {suiteSummary.pass_rate}
                    </span>
                    <span className="text-sm text-[var(--text-muted)]">Pass Rate</span>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-2">
                    Thời gian quét: <span className="font-semibold text-white">{suiteSummary.total_latency}</span>
                  </p>
                </div>
                <div className="flex gap-6 border-l border-[rgba(255,255,255,0.08)] pl-8">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green">{suiteSummary.passed_count}</div>
                    <div className="text-xs text-[var(--text-muted)] uppercase mt-1">Passed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red">
                      {suiteSummary.total_count - suiteSummary.passed_count}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] uppercase mt-1">Failed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{suiteSummary.total_count}</div>
                    <div className="text-xs text-[var(--text-muted)] uppercase mt-1">Total</div>
                  </div>
                </div>
              </div>
            )}

            {/* Test Cases List */}
            <div className="space-y-4">
              {testResults.length === 0 && !suiteLoading ? (
                <div className="p-12 border border-dashed border-[var(--border)] rounded-xl text-center text-[var(--text-muted)]">
                  Chưa chạy kiểm thử. Bấm nút <strong>Run Test Suite</strong> ở trên để khởi động.
                </div>
              ) : (
                testResults.map((result) => {
                  const isExpanded = !!expandedLogs[result.id]
                  return (
                    <div
                      key={result.id}
                      className={`p-5 rounded-xl border transition-all duration-300 ${
                        result.status === 'RUNNING'
                          ? 'border-[var(--accent)] bg-[#0d1726] shadow-[0_0_15px_rgba(37,99,235,0.1)]'
                          : result.status === 'COMPLETED'
                          ? result.passed
                            ? 'border-green-500/20 bg-green-500/5 hover:bg-green-500/10'
                            : 'border-red-500/20 bg-red-500/5 hover:bg-red-500/10'
                          : 'border-[var(--border)] bg-[#101726]'
                      }`}
                    >
                      <div className="flex justify-between items-center cursor-pointer" onClick={() => toggleLog(result.id)}>
                        <div className="flex items-center gap-3">
                          {result.status === 'RUNNING' && (
                            <div className="spinner" style={{ width: 18, height: 18 }} />
                          )}
                          {result.status === 'COMPLETED' && (
                            result.passed ? (
                              <CheckCircle className="text-green-400" size={20} />
                            ) : (
                              <XCircle className="text-red-400" size={20} />
                            )
                          )}
                          <div>
                            <h4 className="font-bold text-sm text-white">{result.id}</h4>
                            <p className="text-xs text-[var(--text-muted)] mt-1">
                              {result.status === 'RUNNING' ? result.message : `Latency: ${result.latency} | Steps: ${result.step_count}`}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-xs font-semibold px-2.5 py-1 rounded-full uppercase ${
                              result.status === 'RUNNING'
                                ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                : result.status === 'COMPLETED'
                                ? result.passed
                                  ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                                  : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                : 'bg-gray-500/10 text-gray-400'
                            }`}
                          >
                            {result.status}
                          </span>
                          <span className="text-xs text-[var(--text-muted)]">{isExpanded ? '▼' : '▶'}</span>
                        </div>
                      </div>

                      {/* Realtime Node steps log */}
                      {isExpanded && (
                        <div className="mt-4 border-t border-[rgba(255,255,255,0.06)] pt-4 space-y-3 animate-fade-in">
                          {/* Inner steps block */}
                          {result.steps && result.steps.length > 0 && (
                            <div className="space-y-2">
                              <div className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
                                Tiến trình thực thi đồ thị ({result.steps.length} bước)
                              </div>
                              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                                {result.steps.map((step: any, sIdx: number) => (
                                  <div key={sIdx} className="bg-[rgba(0,0,0,0.3)] p-3 rounded-lg border border-[rgba(255,255,255,0.03)] text-[11px] font-mono text-gray-300">
                                    <div className="flex justify-between items-center text-[var(--accent)] font-semibold mb-1">
                                      <span>[Bước {step.step_count}] Trực thuộc Node: {step.node}</span>
                                      {step.selected_skill && (
                                        <span className="text-[9px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/20">
                                          kỹ năng: {step.selected_skill}
                                        </span>
                                      )}
                                    </div>
                                    {step.plan && step.plan.length > 0 && (
                                      <div className="text-[10px] text-gray-500 mb-1">
                                        Kế hoạch hiện tại: [{step.plan.join(', ')}]
                                      </div>
                                    )}
                                    {step.last_observation && (
                                      <div className="mt-1 text-[10px] text-gray-400 bg-[rgba(0,0,0,0.4)] p-2 rounded overflow-x-auto whitespace-pre-wrap max-h-[100px]">
                                        Obs: {(() => {
                                          try {
                                            const parsed = JSON.parse(step.last_observation)
                                            return JSON.stringify(parsed, null, 2)
                                          } catch (e) {
                                            return step.last_observation
                                          }
                                        })()}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Final Answer code snippet */}
                          {result.status === 'COMPLETED' && result.final_answer && (
                            <div className="space-y-2">
                              <div className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
                                Kết quả phân tích cuối cùng
                              </div>
                              <div className="p-3 rounded-lg bg-[rgba(0,0,0,0.5)] border border-[rgba(255,255,255,0.05)] text-xs font-mono text-gray-400 whitespace-pre-wrap">
                                {result.final_answer}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="p-4 border-b border-[var(--border)] bg-[rgba(0,0,0,0.2)] flex justify-between items-center">
              <div>
                <h2 className="text-lg font-bold">Agent Chat</h2>
                <p className="text-xs text-[var(--text-muted)]">Interact with an autonomous agent powered by SWE skills</p>
              </div>
              <button 
                className={`btn ${showSettings ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setShowSettings(!showSettings)}
              >
                <Settings size={16} /> {showSettings ? 'Hide Settings' : 'Settings'}
              </button>
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#0a0f18]">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-[var(--text-muted)] opacity-50">
                  <Bot size={48} className="mb-4" />
                  <p className="text-center">Start a conversation to test the agent's capabilities.</p>
                  <p className="text-xs mt-2 text-center max-w-md">
                    Example: "fix bug file /home/user/buggy_code.py"<br/>
                    The agent will plan and execute composite skills dynamically.
                  </p>
                </div>
              ) : (
                messages.filter(m => m.role !== 'system').map((msg, i) => (
                  <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                      msg.role === 'user' ? 'bg-[var(--accent)] text-white' : 'bg-[#1e293b] text-[var(--accent-glow)]'
                    }`}>
                      {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                    </div>
                    <div className={`max-w-80 rounded-lg p-4 shadow-md ${
                      msg.role === 'user' 
                        ? 'bg-opacity-20 border border-[var(--accent)] border-opacity-30' 
                        : 'bg-[var(--bg-secondary)] border border-[var(--border)]'
                    }`}>
                      <pre className="font-sans whitespace-pre-wrap text-sm">{msg.content}</pre>
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex gap-3">
                   <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-[#1e293b] text-[var(--accent-glow)]">
                      <Bot size={16} />
                    </div>
                    <div className="max-w-80 rounded-lg p-4 shadow-md bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center gap-2 text-[var(--text-muted)] text-sm">
                      <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                      Agent is thinking and executing skills...
                    </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-[var(--border)] bg-[#101726]">
              <div className="flex gap-2 relative">
                <textarea
                  className="form-input flex-1 pr-12 resize-none"
                  placeholder="Ask the agent to perform a task..."
                  rows={2}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  style={{ background: '#0a0f18', minHeight: '60px' }}
                />
                <button 
                  className="absolute right-2 bottom-2 p-2 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white disabled:opacity-50 transition-colors"
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                >
                  <Send size={18} />
                </button>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-2 flex items-center gap-1">
                <AlertCircle size={10} /> The agent will automatically discover and execute skills based on your prompt.
              </div>
            </div>
          </>
        )}
      </div>

      {/* Settings Sidebar */}
      {showSettings && (
        <div className="w-300 shrink-0 bg-[var(--bg-card)] rounded-xl border border-[var(--border)] p-5 flex flex-col gap-5 h-fit">
          <div>
            <h3 className="font-bold text-sm mb-4 border-b border-[var(--border)] pb-2">Agent Settings</h3>
            
            <div className="form-group">
              <label className="form-label">Mode</label>
              <select
                className="form-input form-select"
                value={mode}
                onChange={e => setMode(e.target.value as 'agent' | 'orchestrator' | 'test_suite')}
              >
                <option value="agent">Agent Chat</option>
                <option value="orchestrator">Orchestrator</option>
                <option value="test_suite">Run Test Suite (Realtime SSE)</option>
              </select>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                {mode === 'test_suite' 
                  ? 'Khởi chạy toàn bộ các testcase từ JSON bằng SSE trực tiếp.'
                  : 'Orchestrator trả về plan + log thực thi chi tiết.'
                }
              </p>
            </div>

            {mode !== 'test_suite' && mode === 'agent' && (
              <div className="form-group">
                <label className="form-label">Model Selection</label>
                <select 
                  className="form-input form-select" 
                  value={model} 
                  onChange={e => setModel(e.target.value)}
                >
                  <option value="deepseek-chat">DeepSeek Chat (V3)</option>
                  <option value="deepseek-reasoner">DeepSeek Reasoner (R1)</option>
                  <option value="gpt-4o">OpenAI GPT-4o</option>
                  <option value="gpt-4o-mini">OpenAI GPT-4o-mini</option>
                </select>
                <p className="text-[11px] text-[var(--text-muted)] mt-1">DeepSeek connects via api.deepseek.com</p>
              </div>
            )}

            {mode !== 'test_suite' && (
              <div className="form-group">
                <label className="form-label">API Key</label>
                <input 
                  type="password" 
                  className="form-input" 
                  placeholder="sk-..." 
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                />
                <p className="text-[11px] text-[var(--text-muted)] mt-1">Key is only stored in memory during this session.</p>
              </div>
            )}
            
          </div>
          
          <div className="mt-auto pt-4 border-t border-[var(--border)]">
             <button className="btn btn-secondary w-full justify-center" onClick={() => setMessages([])}>
                Clear Chat History
             </button>
          </div>
        </div>
      )}
    </div>
  )
}

import { auth } from '../store/auth.js'
import http from './http.js'

// 流式接口用不了 axios（要读 SSE stream），所以单独拼一下鉴权头。
// 普通 JSON 接口（下面 getAiHistory）仍然走 http 实例，能享受 401 自动登出。
function authHeaders() {
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

// AI 聊天记录：GET /ai_jl/{id}
// id 是当前登录人 id（后端 ai_jl.name_id），返回 [{ HumanMessage, AIMessage }]
export function getAiHistory(id) {
  return http.get(`/ai_jl/${id}`)
}

// RAG 问答：POST /ai/{id}  { premot }，SSE 流式
// 事件类型：contexts（本轮检索到的片段）、thinking（思考过程）、answer（正文）
// id 为当前登录人 id，后端用它把问答写进 ai_jl.name_id，并取这段记忆
export async function askRag(premot, id, { onThinking, onAnswer, onContexts, onDone, onError } = {}) {
  try {
    const resp = await fetch(`/api/ai/${id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders()
      },
      body: JSON.stringify({ premot })
    })

    if (!resp.ok || !resp.body) {
      const text = await resp.text()
      onError && onError(new Error(text || '请求失败'))
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const raw = trimmed.slice(5).trim()
        if (!raw || raw === '[DONE]') continue
        try {
          const obj = JSON.parse(raw)
          if (obj.type === 'thinking') {
            onThinking && onThinking(obj.content || '')
          } else if (obj.type === 'answer') {
            onAnswer && onAnswer(obj.content || '')
          } else if (obj.type === 'contexts') {
            onContexts && onContexts(Array.isArray(obj.content) ? obj.content : [])
          }
        } catch {
          // 忽略无法解析的行
        }
      }
    }

    onDone && onDone()
  } catch (e) {
    onError && onError(e)
  }
}

// RAGAS 评估：POST /ragas  { question, answer, contexts, ground_truth?, metrics? }
// 只返回 metrics 里点名的指标，都是 0~1；不传 metrics 时后端默认算前三个
// 四个指标都算出来时，后端会直接把这一条写进 RAGAS 表（前端不传分数）
export function evaluateRagas({ question, answer, contexts, ground_truth = '', metrics }) {
  return http.post('/ragas', { question, answer, contexts, ground_truth, metrics }, { timeout: 120000 })
}

// 历史评估记录：GET /ragas?limit=N
// 只读库里已经存下的结果，不重新打分。name 是当时被评分的问题
// 返回 [{ id, name, faithfulness, answer_relevancy, Context_Precision, context_recall }]
export function getRagasHistory(limit = 20) {
  return http.get('/ragas', { params: { limit } })
}

// MQ 运行状态：GET /mq/status
// 返回 { connected, queue, handlers, stats: { received, success, failed, processing, last_handler, last_time } }
export function getMqStatus() {
  return http.get('/mq/status')
}

// Agent 流式问答：POST /agent  { request }，SSE 流式
//
// 同一浏览器会话固定一个 session_id（sessionStorage），
// 后端据此算出同一个 thread_id：多轮记忆、人工审核恢复都落在同一个线程上。
const AGENT_SESSION_KEY = 'bizflow_agent_session'

function agentSessionId() {
  let id = sessionStorage.getItem(AGENT_SESSION_KEY)
  if (!id) {
    id = window.crypto?.randomUUID?.() || `s-${Date.now()}-${Math.random().toString(16).slice(2)}`
    sessionStorage.setItem(AGENT_SESSION_KEY, id)
  }
  return id
}

// 通用 SSE 读取：两种 Agent 接口（运行 / 审核恢复）共用同一套解析逻辑
async function streamSse(url, body, { onData, onError, onDone } = {}) {
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders()
      },
      body: JSON.stringify(body)
    })

    if (!resp.ok || !resp.body) {
      const text = await resp.text()
      onError && onError(new Error(text || '请求失败'))
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const raw = line.slice(5).trim()
          if (!raw) continue
          try {
            const obj = JSON.parse(raw)
            onData && onData(obj)
          } catch {
            // 忽略无法解析的行
          }
        }
      }
    }

    onDone && onDone()
  } catch (e) {
    onError && onError(e)
  }
}

export function askAgent(request, handlers = {}) {
  return streamSse('/api/agent', { request, session_id: agentSessionId() }, handlers)
}

// 人工审核结果：POST /agent/approval  { approve, note, interrupt_id, session_id }，SSE 流式
// 同意 -> 图从审核点继续执行工具；拒绝 -> 模型收到"无权限"的工具结果并给出回复
// interrupt_id 原样回传弹窗收到的那一个，后端据此拒绝重复提交/过期弹窗
export function resumeAgent({ approve, note = '', interruptId = null }, handlers = {}) {
  return streamSse(
    '/api/agent/approval',
    { approve, note, interrupt_id: interruptId, session_id: agentSessionId() },
    handlers
  )
}
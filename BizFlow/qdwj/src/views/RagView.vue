<template>
  <div class="page">
    <h2>📚 员工守则助手</h2>

    <div class="layout">
      <aside class="side">
        <h3 class="side-title">历史评估记录</h3>
        <p class="side-desc">
          读库里已经存下的评估结果，最新在前。右边点「RAGAS 评估」会自动存一条。
        </p>

        <button class="eval-btn side-btn" type="button" :disabled="historyLoading" @click="loadHistory">
          {{ historyLoading ? '⏳ 读取中…' : '📋 查看历史记录' }}
        </button>

        <p v-if="historyError" class="eval-error">{{ historyError }}</p>

        <div v-if="historyResult" class="side-result">
          <p v-if="!historyResult.length" class="side-desc">
            还没有评估记录，先去右边点「RAGAS 评估」。
          </p>
          <template v-else>
            <p class="side-desc">最近 {{ historyResult.length }} 条，均值：</p>

            <div v-for="row in historyRows(historyAverages)" :key="row.key" class="eval-row">
              <span class="eval-label">{{ row.label }}</span>
              <span class="eval-bar"><i :style="{ width: row.pct + '%', background: row.color }"></i></span>
              <span class="eval-score" :style="{ color: row.color }">{{ row.pct }}%</span>
            </div>

            <p class="side-desc side-warn">忠=忠实度 关=相关性 精=精度 召=召回率</p>

            <ul class="hist-list">
              <li v-for="r in historyResult" :key="r.id" class="hist-item">
                <p class="hist-q" :title="r.name">{{ r.name }}</p>
                <p class="hist-scores">
                  忠 {{ pct(r.faithfulness) }} · 关 {{ pct(r.answer_relevancy) }} ·
                  精 {{ pct(r.Context_Precision) }} · 召 {{ pct(r.context_recall) }}
                </p>
              </li>
            </ul>
          </template>
        </div>
        <p v-else-if="!historyLoading && !historyError" class="side-desc side-empty">
          点上面按钮读记录。
        </p>
      </aside>

      <section class="chat">
        <div class="chat-head">
          <span class="chat-avatar">📚</span>
          <p class="chat-desc">基于员工手册知识库，解答公司规章制度</p>
        </div>

        <div class="chat-body">
          <p v-if="!messages.length" class="chat-empty">
            输入问题，助手将基于员工守则为你解答 👇
          </p>

          <template v-for="m in messages" :key="m.id">
            <div v-if="m.role === 'thinking'" class="thinking">
              <span class="thinking-label">💭 思考中</span>
              <span class="thinking-text">{{ m.content }}</span>
            </div>
            <template v-else>
              <div
                class="bubble"
                :class="m.role === 'user' ? 'bubble--user' : m.role === 'error' ? 'bubble--error' : 'bubble--ai'"
              >{{ m.content }}</div>

              <!-- 只有拿到本轮检索片段（contexts）的回答才能算忠实度/召回率，历史记录不给入口 -->
              <div v-if="m.role === 'ai' && !m.streaming && m.content && m.contexts?.length" class="eval">
                <div class="eval-actions">
                  <button class="eval-btn" type="button" :disabled="m.evalLoading" @click="runEval(m)">
                    {{ m.evalLoading ? '⏳ 评估中…' : m.eval ? '↻ 重新评估' : '📊 RAGAS 评估' }}
                  </button>
                  <button class="eval-btn" type="button" :disabled="m.recallLoading" @click="runRecall(m)">
                    {{ m.recallLoading ? '⏳ 评估中…' : m.recall ? '↻ 重新评估' : '📄 Context Recall 评估' }}
                  </button>
                </div>

                <p v-if="m.evalError" class="eval-error">{{ m.evalError }}</p>
                <p v-if="m.recallError" class="eval-error">{{ m.recallError }}</p>

                <div v-if="m.eval || m.recall" class="eval-cards">
                  <div v-if="m.eval" class="eval-card">
                    <p class="eval-title">RAGAS 评估</p>
                    <div v-for="row in evalRows(m.eval)" :key="row.key" class="eval-row">
                      <span class="eval-label">{{ row.label }}</span>
                      <span class="eval-bar"><i :style="{ width: row.pct + '%', background: row.color }"></i></span>
                      <span class="eval-score" :style="{ color: row.color }">{{ row.pct }}%</span>
                    </div>
                    <p class="eval-desc">
                      忠实度 = 回答里能被检索片段支撑的声明占比（防幻觉）；
                      相关性 = 回答与问题的语义贴近程度（防跑题）。
                      这次结果会写进数据库，左侧「历史记录」可横向对比。
                    </p>
                  </div>

                  <div v-if="m.recall" class="eval-card">
                    <p class="eval-title">Context Recall 评估</p>
                    <div v-for="row in recallRows(m.recall)" :key="row.key" class="eval-row">
                      <span class="eval-label">{{ row.label }}</span>
                      <span class="eval-bar"><i :style="{ width: row.pct + '%', background: row.color }"></i></span>
                      <span class="eval-score" :style="{ color: row.color }">{{ row.pct }}%</span>
                    </div>
                    <p class="eval-desc">
                      召回率 = 参考答案里能被检索片段覆盖的声明占比。
                      当前没有人工标注答案，参考文本就是回答本身，所以它和忠实度同算法同输入，
                      分数会完全一致 —— 这是指标定义决定的，不是 bug。
                    </p>
                  </div>
                </div>
              </div>
            </template>
          </template>

          <div v-if="loading" class="chat-loading">思考中…</div>
        </div>

        <footer class="chat-input">
          <input
            v-model="question"
            placeholder="输入问题，如：公司年假怎么请？"
            @keyup.enter="onSubmit"
          />
          <button class="btn" type="button" :disabled="loading || !question.trim()" @click="onSubmit">
            发送
          </button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { askRag, getAiHistory, evaluateRagas, getRagasHistory } from '../api/ai.js'
import { auth } from '../store/auth.js'

const question = ref('')
const messages = ref([])
const loading = ref(false)

// 左侧历史记录：只读库里存下的评估结果，不重新打分
const historyLoading = ref(false)
const historyResult = ref(null)
const historyError = ref('')

// 把当前列表的四项指标算成均值，顶端进度条用
const historyAverages = computed(() => {
  const rows = historyResult.value || []
  const keys = ['faithfulness', 'answer_relevancy', 'Context_Precision', 'context_recall']
  const out = {}
  for (const k of keys) {
    out[k] = rows.length ? rows.reduce((s, r) => s + Number(r[k] ?? 0), 0) / rows.length : 0
  }
  return out
})

// 每条消息一个自增 id，当 v-for 的 key：用下标做 key，
// 在 splice 删掉空的 thinking 气泡后，Vue 会复用错节点。
let seq = 0
function pushMessage(role, content = '', extra = {}) {
  messages.value.push({ id: ++seq, role, content, ...extra })
  return messages.value[messages.value.length - 1]
}

// 进页面先把该登录人的历史问答拉回来（GET /ai_jl/{id}），
// id 固定取登录人，前端不可改
onMounted(async () => {
  if (!auth.id) return
  try {
    const rows = await getAiHistory(auth.id)
    for (const r of Array.isArray(rows) ? rows : []) {
      if (r?.HumanMessage) pushMessage('user', r.HumanMessage)
      if (r?.AIMessage) pushMessage('ai', r.AIMessage)
    }
  } catch {
    // 历史拉取失败不打断新对话
  }
})

async function onSubmit() {
  if (loading.value) return
  const q = question.value.trim()
  if (!q) return

  pushMessage('user', q)
  question.value = ''
  loading.value = true

  const thinkingMsg = pushMessage('thinking')
  const answerMsg = pushMessage('ai', '', { streaming: true, contexts: [] })

  await askRag(q, auth.id, {
    onContexts(c) {
      // 后端流的第一帧，存住检索片段，点评估时回传
      answerMsg.contexts = c
    },
    onThinking(t) {
      thinkingMsg.content += t
    },
    onAnswer(a) {
      answerMsg.content += a
    },
    onDone() {
      answerMsg.streaming = false
      // 没有思考过程时，移除空的 thinking 气泡
      if (!thinkingMsg.content) {
        const idx = messages.value.findIndex((m) => m.id === thinkingMsg.id)
        if (idx >= 0) messages.value.splice(idx, 1)
      }
      loading.value = false
    },
    onError(err) {
      answerMsg.streaming = false
      const idx = messages.value.findIndex((m) => m.id === thinkingMsg.id)
      if (idx >= 0) messages.value.splice(idx, 1)
      answerMsg.role = 'error'
      answerMsg.content = err?.message || 'AI 问答失败'
      loading.value = false
    }
  })
}

// RAGAS 分档：>=0.8 绿、>=0.5 黄、其余红
function scoreColor(v) {
  if (v >= 0.8) return '#22c55e'
  if (v >= 0.5) return '#f59e0b'
  return '#f43f5e'
}

function evalRows(r) {
  return [
    { key: 'faithfulness', label: '忠实度', value: Number(r?.faithfulness ?? 0) },
    { key: 'relevancy', label: '相关性', value: Number(r?.answer_relevancy ?? 0) }
  ].map((row) => ({
    ...row,
    pct: Math.round(row.value * 100),
    color: scoreColor(row.value)
  }))
}

// 单条回答的 Context Recall 只有一个指标
function recallRows(r) {
  const value = Number(r?.context_recall ?? 0)
  return [{ key: 'context_recall', label: '召回率', pct: Math.round(value * 100), color: scoreColor(value) }]
}

// 左侧汇总的四项指标（字段名跟后端 Ragas 模型保持一致）
function historyRows(avg) {
  return [
    { key: 'faithfulness', label: '忠实' },
    { key: 'answer_relevancy', label: '相关' },
    { key: 'Context_Precision', label: '精度' },
    { key: 'context_recall', label: '召回' }
  ].map((row) => {
    const value = Number(avg?.[row.key] ?? 0)
    return { ...row, pct: Math.round(value * 100), color: scoreColor(value) }
  })
}

function pct(v) {
  return Math.round(Number(v ?? 0) * 100) + '%'
}

// 一条回答对应的提问：往前找最近的一条 user 消息
function findQuestionFor(m) {
  const idx = messages.value.findIndex((x) => x.id === m.id)
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') return messages.value[i].content
  }
  return ''
}

async function runEval(m) {
  if (m.evalLoading) return
  m.evalLoading = true
  m.evalError = ''
  try {
    // 一次算全四个：后端只在这四个都齐了的时候才存库，缺项的行没法横着对比
    const res = await evaluateRagas({
      question: findQuestionFor(m),
      answer: m.content,
      contexts: m.contexts || [],
      metrics: ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
    })
    m.eval = res
    // 同一个响应里已经有召回率，顺手填上，省得再点一次
    m.recall = res
  } catch (e) {
    m.evalError = e?.response?.data?.detail || e?.message || '评估失败，请重试'
  } finally {
    m.evalLoading = false
  }
}

async function runRecall(m) {
  if (m.recallLoading) return
  m.recallLoading = true
  m.recallError = ''
  try {
    m.recall = await evaluateRagas({
      question: findQuestionFor(m),
      answer: m.content,
      contexts: m.contexts || [],
      metrics: ['context_recall']
    })
  } catch (e) {
    m.recallError = e?.response?.data?.detail || e?.message || '评估失败，请重试'
  } finally {
    m.recallLoading = false
  }
}

async function loadHistory() {
  if (historyLoading.value) return
  historyLoading.value = true
  historyError.value = ''
  try {
    const rows = await getRagasHistory(20)
    historyResult.value = Array.isArray(rows) ? rows : []
  } catch (e) {
    historyError.value = e?.response?.data?.detail || e?.message || '读取失败，请重试'
  } finally {
    historyLoading.value = false
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  align-items: stretch;
  gap: 16px;
}

.chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  height: calc(100vh - 200px);
  min-height: 400px;
}

/* ---------- 左侧历史评估栏 ---------- */
.side {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  height: calc(100vh - 200px);
  min-height: 400px;
  overflow-y: auto;
}

.side-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.side-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-2);
}

.side-warn {
  opacity: 0.75;
}

.side-empty {
  opacity: 0.6;
}

.side-btn {
  align-self: flex-start;
}

.side-result {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.hist-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hist-item {
  padding: 7px 9px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-2);
}

.hist-q {
  font-size: 12px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hist-scores {
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}

.chat-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.02);
}

.chat-avatar {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: rgba(109, 139, 255, 0.16);
  box-shadow: 0 0 18px rgba(109, 139, 255, 0.22);
  flex-shrink: 0;
}

.chat-desc {
  font-size: 14px;
  color: var(--text-2);
}

.chat-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-empty {
  color: var(--text-2);
  font-size: 15px;
  text-align: center;
  margin: auto;
  line-height: 1.8;
}

.chat-loading {
  color: var(--primary-2);
  font-size: 14px;
}

.bubble {
  max-width: 86%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 16px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble--ai {
  align-self: flex-start;
  background: linear-gradient(135deg, rgba(109, 139, 255, 0.22), rgba(34, 211, 238, 0.12));
  border: 1px solid rgba(109, 139, 255, 0.28);
  color: var(--text);
  border-bottom-left-radius: 4px;
}

.bubble--user {
  align-self: flex-end;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble--error {
  align-self: flex-start;
  background: rgba(244, 63, 94, 0.14);
  border: 1px solid rgba(244, 63, 94, 0.32);
  color: var(--danger);
  border-bottom-left-radius: 4px;
}

.thinking {
  align-self: flex-start;
  max-width: 86%;
  font-size: 14px;
  color: var(--text-2);
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed var(--border);
  border-radius: 12px;
  padding: 10px 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.thinking-label {
  font-size: 12px;
  color: var(--primary-2);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.thinking-text {
  white-space: pre-wrap;
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--border);
}

.chat-input input {
  flex: 1;
  padding: 12px 15px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-2);
  color: var(--text);
  font-size: 16px;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.chat-input input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.chat-input input::placeholder {
  color: #5b6478;
}

/* ---------- RAGAS 评估 ---------- */
.eval {
  align-self: flex-start;
  max-width: 86%;
  margin-top: -6px;
}

.eval-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.eval-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.eval-btn {
  padding: 5px 11px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-2);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}

.eval-btn:hover:not(:disabled) {
  color: var(--text);
  border-color: var(--primary);
  background: rgba(109, 139, 255, 0.12);
}

.eval-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.eval-card {
  flex: 1 1 240px;
  margin-top: 8px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-2);
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.eval-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
}

.eval-row {
  display: grid;
  grid-template-columns: 48px 1fr 42px;
  align-items: center;
  gap: 10px;
}

.eval-label {
  font-size: 12px;
  color: var(--text-2);
}

.eval-bar {
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.eval-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.eval-score {
  font-size: 12px;
  font-weight: 700;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.eval-desc {
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-2);
  opacity: 0.8;
}

.eval-error {
  margin-top: 6px;
  font-size: 12px;
  color: var(--danger);
}

@media (max-width: 960px) {
  .layout {
    flex-direction: column;
  }

  .side {
    width: auto;
    height: auto;
    min-height: 0;
  }
}
</style>
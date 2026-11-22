<template>
  <div class="page">
    <h2>💬 BizFlow 平台助手</h2>

    <section class="chat">
      <div class="chat-head">
        <span class="chat-avatar">💬</span>
        <p class="chat-desc">可查工资、年假、分配任务等，流式作答</p>
        <span
          class="mq-chip"
          :class="mq.connected ? 'mq-chip--ok' : 'mq-chip--off'"
          :title="mqTitle"
        >
          <span class="mq-dot"></span>{{ mqText }}
        </span>
      </div>

      <div class="chat-body">
        <p v-if="!messages.length" class="chat-empty">
          输入问题，助手可帮你查询业务数据 👇
        </p>
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="bubble"
          :class="m.role === 'user' ? 'bubble--user' : m.role === 'error' ? 'bubble--error' : 'bubble--ai'"
        >{{ m.content }}</div>
        <div v-if="toolStatus" class="tool-status">🔧 {{ toolStatus }}</div>
        <div v-if="mqNotice" class="mq-note">📨 {{ mqNotice }}</div>
        <div v-if="loading" class="chat-loading">正在查询…</div>
      </div>

      <footer class="chat-input">
        <input
          v-model="question"
          placeholder="输入问题，如：帮我查一下某人的工资"
          @keyup.enter="onSubmit"
        />
        <button class="btn" type="button" :disabled="loading || !question.trim()" @click="onSubmit">
          发送
        </button>
      </footer>
    </section>

    <!-- 人工审核弹窗：AI 调用第三方工具前必须由用户确认 -->
    <div v-if="pendingApproval" class="approval-mask">
      <div class="approval-card" role="dialog" aria-modal="true" aria-labelledby="approval-title">
        <h3 id="approval-title" class="approval-title">🔐 第三方工具调用审核</h3>
        <p class="approval-hint">{{ pendingApproval.message || 'AI 请求调用第三方工具，是否同意？' }}</p>

        <ul class="approval-list">
          <li v-for="(req, i) in pendingApproval.requests || []" :key="i" class="approval-item">
            <div class="approval-tool">
              {{ req.label || req.tool }}
              <span class="approval-tool-name">{{ req.tool }}</span>
            </div>
            <pre class="approval-args">{{ formatArgs(req.args) }}</pre>
          </li>
        </ul>

        <label class="approval-note">
          备注（可选，拒绝原因会转告助手）
          <input v-model="approvalNote" placeholder="例如：金额不对，先不要分配" :disabled="deciding" />
        </label>

        <div class="approval-actions">
          <button class="btn btn--ghost" type="button" :disabled="deciding" @click="submitDecision(false)">
            拒绝调用
          </button>
          <button class="btn" type="button" :disabled="deciding" @click="submitDecision(true)">
            {{ deciding ? '提交中…' : '同意并执行' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { askAgent, resumeAgent, getMqStatus } from '../api/ai.js'

const question = ref('')
const messages = ref([])
const loading = ref(false)
const toolStatus = ref('')
const mqNotice = ref('')

// 人工审核：approval_required 事件的 payload（null 表示没有待审核操作）
const pendingApproval = ref(null)
const approvalNote = ref('')
const deciding = ref(false)
// 当前这条 AI 消息：首次运行与审核恢复要往同一个气泡里继续写内容
let activeAiMsg = null

const mq = reactive({
  connected: false,
  success: 0,
  processing: 0,
  lastHandler: '',
  lastTime: ''
})

const mqText = computed(() => {
  if (!mq.connected) return 'MQ 未连接'
  if (mq.processing > 0) return 'MQ 正在执行后台任务…'
  return `MQ 已连接 · 已执行 ${mq.success} 个任务`
})

const mqTitle = computed(() =>
  mq.lastTime ? `最近任务：${mq.lastHandler || '-'}（${mq.lastTime}）` : '后台任务队列状态'
)

let mqTimer = null

async function refreshMq() {
  try {
    const s = await getMqStatus()
    mq.connected = !!s.connected
    mq.success = s.stats?.success ?? 0
    mq.processing = s.stats?.processing ?? 0
    mq.lastHandler = s.stats?.last_handler || ''
    mq.lastTime = s.stats?.last_time || ''
  } catch {
    mq.connected = false
  }
}

onMounted(() => {
  refreshMq()
  mqTimer = setInterval(refreshMq, 4000)
})

onBeforeUnmount(() => {
  if (mqTimer) clearInterval(mqTimer)
})

async function onSubmit() {
  if (loading.value || deciding.value || pendingApproval.value) return
  const q = question.value.trim()
  if (!q) return
  messages.value.push({ role: 'user', content: q })
  question.value = ''
  loading.value = true
  toolStatus.value = ''
  mqNotice.value = ''

  const aiMsg = reactive({ role: 'ai', content: '' })
  activeAiMsg = aiMsg
  messages.value.push(aiMsg)

  await askAgent(q, {
    onData: handleStreamEvent,
    onError(err) {
      aiMsg.role = 'error'
      aiMsg.content = err?.message || 'Agent 请求失败'
      // 出错时 askAgent 不会走 onDone（api/ai.js 里直接 return），
      // 不在这里复位，发送按钮会永久禁用
      loading.value = false
    },
    onDone() {
      loading.value = false
      toolStatus.value = ''
      refreshMq()
    }
  })
}

// 所有 SSE 事件统一在这里分发（首次运行和审核恢复共用）
function handleStreamEvent(obj) {
  const aiMsg = activeAiMsg
  if (obj.type === 'content') {
    toolStatus.value = ''
    if (aiMsg) aiMsg.content += obj.content
  } else if (obj.type === 'tool_start') {
    toolStatus.value = `正在调用第三方工具：${obj.label || obj.tool}`
  } else if (obj.type === 'tool_end') {
    toolStatus.value = `第三方工具调用完成：${obj.label || obj.tool}`
  } else if (obj.type === 'approval_required') {
    // 图已暂停在 interrupt 点，弹窗等用户决定；interrupt_id 随审核结果回传
    pendingApproval.value = { ...(obj.payload || {}), interrupt_id: obj.interrupt_id || null }
    approvalNote.value = ''
    toolStatus.value = ''
  } else if (obj.type === 'approval_result') {
    toolStatus.value =
      obj.result === 'approved' ? '人工审核已通过，正在执行工具…' : '人工审核已拒绝，助手正在说明…'
  } else if (obj.type === 'mq') {
    mqNotice.value = obj.content || ''
    refreshMq()
  }
}

// 提交审核结果：后端用 Command(resume=...) 恢复同一 thread 上的图
async function submitDecision(approve) {
  if (!pendingApproval.value || deciding.value) return
  const interruptId = pendingApproval.value.interrupt_id || null
  pendingApproval.value = null
  deciding.value = true
  loading.value = true
  toolStatus.value = '正在提交人工审核结果…'

  await resumeAgent(
    { approve, note: approvalNote.value.trim(), interruptId },
    {
      onData: handleStreamEvent,
      onError(err) {
        const aiMsg = activeAiMsg
        if (aiMsg) {
          aiMsg.role = 'error'
          aiMsg.content = err?.message || '审核提交失败'
        }
        loading.value = false
        deciding.value = false
        toolStatus.value = ''
      },
      onDone() {
        loading.value = false
        deciding.value = false
        approvalNote.value = ''
        toolStatus.value = ''
        refreshMq()
        // 注意不清 pendingApproval：恢复过程中可能产生新的审核请求
      }
    }
  )
}

function formatArgs(args) {
  try {
    return JSON.stringify(args ?? {}, null, 2)
  } catch {
    return String(args)
  }
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  height: calc(100vh - 200px);
  min-height: 400px;
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

.mq-chip {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-2);
  color: var(--text-2);
  font-size: 13px;
  white-space: nowrap;
}

.mq-chip--ok {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.35);
  background: rgba(52, 211, 153, 0.08);
}

.mq-chip--off {
  color: var(--danger);
  border-color: rgba(244, 63, 94, 0.35);
  background: rgba(244, 63, 94, 0.08);
}

.mq-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 8px currentColor;
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
  font-size: 15px;
}

.tool-status {
  align-self: flex-start;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 14px;
  color: var(--primary-2);
  background: rgba(34, 211, 238, 0.08);
  border: 1px dashed rgba(34, 211, 238, 0.35);
}

.mq-note {
  align-self: flex-start;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-2);
  background: rgba(109, 139, 255, 0.08);
  border: 1px solid rgba(109, 139, 255, 0.2);
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

/* ---------- 人工审核弹窗 ---------- */
.approval-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(5, 7, 12, 0.72);
  backdrop-filter: blur(4px);
}

.approval-card {
  width: min(520px, 100%);
  max-height: 82vh;
  overflow-y: auto;
  background: var(--card);
  border: 1px solid rgba(109, 139, 255, 0.35);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md), var(--glow);
  padding: 22px 24px;
}

.approval-title {
  font-size: 18px;
  margin-bottom: 8px;
}

.approval-hint {
  color: var(--text-2);
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 14px;
}

.approval-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.approval-item {
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
}

.approval-tool {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.approval-tool-name {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: var(--primary-2);
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(34, 211, 238, 0.1);
  border: 1px solid rgba(34, 211, 238, 0.3);
}

.approval-args {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-2);
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  padding: 10px 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.approval-note {
  display: block;
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 18px;
}

.approval-note input {
  width: 100%;
  margin-top: 7px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--bg-2);
  color: var(--text);
  font-size: 14px;
  font-family: inherit;
}

.approval-note input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.approval-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
<template>
  <div class="page archive">
    <!-- 顶部主视觉 -->
    <section class="hero">
      <div class="hero-glow" aria-hidden="true"></div>
      <span class="badge">
        <i class="badge-dot"></i>
        董事长专属
      </span>
      <h2 class="hero-title">员工档案导出中心</h2>
      <p class="hero-sub">
        全员任务进展与薪酬明细，一键整理成可以直接交付的 Excel 报表
      </p>
      <ul class="chips">
        <li><span class="chip-key">取数方式</span>消息队列优先 · 不可用时自动本地直算</li>
        <li><span class="chip-key">报表字段</span>员工姓名 · 任务 · 工资</li>
        <li><span class="chip-key">覆盖范围</span>全部在职员工</li>
      </ul>
    </section>

    <!-- 操作区 -->
    <section class="actions">
      <article class="action">
        <div class="action-icon action-icon--blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        </div>
        <h3>在线预览</h3>
        <p>先在这里核对全员的任务与薪酬，确认无误再导出，避免拿错版本。</p>
        <button class="btn btn--ghost btn--block" :disabled="previewing" @click="loadPreview">
          {{ previewing ? '正在汇总数据…' : rows.length ? '重新加载预览' : '加载预览数据' }}
        </button>
      </article>

      <article class="action">
        <div class="action-icon action-icon--green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3.5v11" />
            <path d="M7.5 10.5 12 15l4.5-4.5" />
            <path d="M4.5 17.5v1a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-1" />
          </svg>
        </div>
        <h3>导出 Excel 报表</h3>
        <p>生成标准 xlsx 文件，可直接归档、打印或交付给财务与人事。</p>
        <button class="btn btn--block" :disabled="downloading" @click="download">
          {{ downloading ? '正在生成文件…' : '下载员工信息.xlsx' }}
        </button>
        <button class="link-btn" :disabled="downloading" @click="openInline">
          在浏览器内直接打开
        </button>
      </article>
    </section>

    <!-- 预览结果 -->
    <section class="card result">
      <header class="result-head">
        <div>
          <h3>预览结果</h3>
          <p class="result-sub">{{ resultSub }}</p>
        </div>
        <div class="result-tags">
          <span v-if="sourceLabel" class="source" :class="sourceClass">
            <i class="source-dot"></i>数据来源：{{ sourceLabel }}
          </span>
          <span v-if="rows.length" class="count">{{ rows.length }} 人</span>
        </div>
      </header>

      <!-- 加载骨架 -->
      <div v-if="previewing" class="skeleton">
        <div v-for="n in 3" :key="n" class="skeleton-row">
          <span class="bar bar--sm"></span>
          <span class="bar"></span>
          <span class="bar bar--xs"></span>
        </div>
      </div>

      <!-- 错误 -->
      <p v-else-if="error" class="tip tip--error">⚠ {{ error }}</p>

      <!-- 表格 -->
      <template v-else-if="rows.length">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-index">#</th>
                <th>员工姓名</th>
                <th>承担任务</th>
                <th class="col-num">薪酬合计</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, i) in rows" :key="item.name + i">
                <td class="col-index">{{ i + 1 }}</td>
                <td class="col-name">{{ item.name }}</td>
                <td>
                  <span v-if="item.tasks" class="tasks">{{ item.tasks }}</span>
                  <span v-else class="muted">暂无任务</span>
                </td>
                <td class="col-num">¥ {{ money(item.salary) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <footer class="result-foot">
          <span>合计 {{ rows.length }} 人</span>
          <span class="foot-divider"></span>
          <span>薪酬合计 <strong>¥ {{ money(totalSalary) }}</strong></span>
        </footer>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M4.5 5.5A2 2 0 0 1 6.5 3.5H19v17H6.5a2 2 0 0 1-2-2v-13Z" />
            <path d="M9 8h6M9 12h6M9 16h3" />
          </svg>
        </div>
        <p class="empty-title">还没有加载数据</p>
        <p class="muted">点击「加载预览数据」，先把全员档案汇总出来看一眼</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { previewEmployees, fetchEmployeesExcel, readBlobError } from '../api/excel.js'

const rows = ref([])
const previewing = ref(false)
const downloading = ref(false)
const error = ref('')
const source = ref('')

// 后端 X-Data-Source：mq = 走消息队列，local = MQ 不可用时的本地直算
const sourceLabel = computed(() => {
  if (source.value === 'mq') return '消息队列'
  if (source.value === 'local') return '本地直算'
  return ''
})

const sourceClass = computed(() =>
  source.value === 'mq' ? 'source--mq' : 'source--local'
)

const resultSub = computed(() => {
  if (source.value === 'mq') return '数据由 RabbitMQ 异步汇总，最多等待 60 秒'
  if (source.value === 'local') return '消息队列未启动，已自动改为本地直算，功能不受影响'
  return '优先走消息队列，队列不可用时自动本地直算'
})

const totalSalary = computed(() =>
  rows.value.reduce((sum, r) => sum + (Number(r.salary) || 0), 0)
)

function money(v) {
  return (Number(v) || 0).toLocaleString('zh-CN')
}

async function loadPreview() {
  previewing.value = true
  error.value = ''
  rows.value = []
  try {
    const data = await previewEmployees()
    rows.value = data.rows
    source.value = data.source
  } catch (e) {
    source.value = ''
    error.value = await readBlobError(e, '获取员工档案失败，请稍后重试')
  } finally {
    previewing.value = false
  }
}

async function download() {
  downloading.value = true
  error.value = ''
  try {
    const { blob, source: src } = await fetchEmployeesExcel('download')
    source.value = src
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '员工信息.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  } catch (e) {
    error.value = await readBlobError(e, '导出失败，请稍后重试')
  } finally {
    downloading.value = false
  }
}

async function openInline() {
  downloading.value = true
  error.value = ''
  try {
    const { blob, source: src } = await fetchEmployeesExcel('view')
    source.value = src
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.target = '_blank'
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) {
    error.value = await readBlobError(e, '打开失败，请稍后重试')
  } finally {
    downloading.value = false
  }
}

onMounted(loadPreview)
</script>

<style scoped>
/* ---------- 主视觉 ---------- */
.hero {
  position: relative;
  overflow: hidden;
  padding: 42px 36px 34px;
  border-radius: 22px;
  border: 1px solid var(--border);
  background:
    linear-gradient(135deg, rgba(109, 139, 255, 0.16), rgba(34, 211, 238, 0.06)),
    var(--card);
  box-shadow: var(--shadow-md);
}

.hero-glow {
  position: absolute;
  width: 320px;
  height: 320px;
  right: -90px;
  top: -140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.22), transparent 62%);
  pointer-events: none;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 13px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--primary-2);
  background: rgba(34, 211, 238, 0.1);
  border: 1px solid rgba(34, 211, 238, 0.32);
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-2);
  box-shadow: 0 0 8px var(--primary-2);
}

.hero-title {
  margin: 16px 0 12px;
  font-size: clamp(26px, 3.4vw, 38px);
  font-weight: 800;
  letter-spacing: 0.01em;
  line-height: 1.22;
  background: linear-gradient(120deg, #fff, var(--primary), var(--primary-2));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-sub {
  max-width: 620px;
  font-size: 15px;
  line-height: 1.75;
  color: var(--text-2);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
  list-style: none;
}

.chips li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-radius: 10px;
  font-size: 13px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
}

.chip-key {
  color: var(--text-2);
  font-size: 12px;
}

/* ---------- 操作卡片 ---------- */
.actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
  margin-top: 20px;
}

.action {
  display: flex;
  flex-direction: column;
  padding: 26px 24px 22px;
  border-radius: 18px;
  background: var(--card);
  border: 1px solid var(--border);
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.action:hover {
  transform: translateY(-4px);
  border-color: rgba(109, 139, 255, 0.42);
  box-shadow: var(--shadow-md);
}

.action-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.action-icon svg {
  width: 26px;
  height: 26px;
}

.action-icon--blue {
  color: var(--primary-2);
  background: rgba(109, 139, 255, 0.16);
  box-shadow: 0 0 22px rgba(109, 139, 255, 0.18);
}

.action-icon--green {
  color: var(--success);
  background: rgba(52, 211, 153, 0.14);
  box-shadow: 0 0 22px rgba(52, 211, 153, 0.16);
}

.action h3 {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 8px;
}

.action p {
  flex: 1;
  margin-bottom: 20px;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-2);
}

.action .btn {
  padding: 11px 18px;
}

.link-btn {
  margin-top: 10px;
  padding: 6px;
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: 12.5px;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.link-btn:hover:not(:disabled) {
  color: var(--primary-2);
}

.link-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---------- 预览结果 ---------- */
.result {
  margin-top: 20px;
}

.result-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.result-head h3 {
  font-size: 17px;
  font-weight: 700;
}

.result-sub {
  margin-top: 5px;
  font-size: 12.5px;
  color: var(--text-2);
}

.count {
  flex-shrink: 0;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  color: var(--primary-2);
  background: rgba(109, 139, 255, 0.14);
  border: 1px solid rgba(109, 139, 255, 0.28);
}

.result-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.source {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  white-space: nowrap;
  border: 1px solid transparent;
}

.source-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 7px currentColor;
}

.source--mq {
  color: var(--success);
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.3);
}

.source--local {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.3);
}

.table-wrap {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid var(--border);
}

.table-wrap th {
  white-space: nowrap;
}

.col-index {
  width: 56px;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}

.col-name {
  font-weight: 600;
  white-space: nowrap;
}

.col-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.tasks {
  color: var(--text);
}

.muted {
  color: var(--text-2);
  font-size: 13px;
}

.result-foot {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--border);
  font-size: 13px;
  color: var(--text-2);
}

.result-foot strong {
  color: var(--primary-2);
  font-size: 14px;
}

.foot-divider {
  width: 1px;
  height: 12px;
  background: var(--border);
}

/* ---------- 骨架屏 ---------- */
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-row {
  display: grid;
  grid-template-columns: 90px 1fr 110px;
  gap: 14px;
  align-items: center;
}

.bar {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.05),
    rgba(255, 255, 255, 0.12),
    rgba(255, 255, 255, 0.05)
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

.bar--sm { width: 60%; }
.bar--xs { width: 45%; justify-self: end; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ---------- 空状态 ---------- */
.empty {
  padding: 44px 20px;
  text-align: center;
}

.empty-icon {
  width: 62px;
  height: 62px;
  margin: 0 auto 16px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-2);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
}

.empty-icon svg {
  width: 28px;
  height: 28px;
}

.empty-title {
  margin-bottom: 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}
</style>

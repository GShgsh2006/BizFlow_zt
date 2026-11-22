<template>
  <div class="home">
    <!-- 背景光效层 -->
    <div class="scene" aria-hidden="true">
      <span class="glow glow--a"></span>
      <span class="glow glow--b"></span>
      <span class="streak streak--a"></span>
      <span class="streak streak--b"></span>
      <span class="streak streak--c"></span>
    </div>

    <!-- 主视觉 -->
    <section class="hero">
      <div class="hero-copy">
        <p class="kicker">
          <span class="kicker-tag">WELCOME BACK</span>
          <span class="kicker-user">{{ auth.username || '朋友' }}</span>
          <span class="kicker-role">{{ auth.role || '访客' }}</span>
          <span class="kicker-line"></span>
        </p>

        <h1 class="hero-title">
          <span class="grad">BizFlow</span> 让业务更简单<br />
          让工作更高效
        </h1>

        <p class="hero-sub">统一业务入口 · 流程高效协同 · 智能驱动未来</p>

        <router-link class="cta" to="/task-query">
          开始使用
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4.5 12h14" />
            <path d="M13 6.5 18.5 12 13 17.5" />
          </svg>
        </router-link>
      </div>

      <!-- 3D 徽标舞台 -->
      <div class="stage" aria-hidden="true">
        <span class="stage-glow"></span>
        <span class="orbit orbit--a"></span>
        <span class="orbit orbit--b"></span>
        <span class="platform"><i></i></span>

        <div class="cube">
          <b>B</b>
        </div>

        <span class="shard shard--1"></span>
        <span class="shard shard--2"></span>
        <span class="shard shard--3"></span>
        <span class="shard shard--4"></span>
      </div>
    </section>

    <!-- 平台概览 -->
    <section class="overview">
      <header class="ov-head">
        <span class="ov-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3.2 20 7.6v8.8L12 20.8 4 16.4V7.6L12 3.2Z" />
            <path d="M4 7.6 12 12l8-4.4" />
            <path d="M12 12v8.8" />
          </svg>
        </span>
        <div class="ov-title">
          <h2>平台概览</h2>
          <p>业务运行情况一览</p>
        </div>
        <span class="ov-date">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
               stroke-linecap="round" stroke-linejoin="round">
            <rect x="3.5" y="5.5" width="17" height="15" rx="2.5" />
            <path d="M3.5 10h17" />
            <path d="M8 3.5v4M16 3.5v4" />
          </svg>
          {{ todayText }}
        </span>
      </header>

      <div class="ov-stats">
        <article class="stat">
          <span class="stat-icon stat-icon--blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3 21 7.2 12 11.4 3 7.2 12 3Z" />
              <path d="M3 12 12 16.2 21 12" />
              <path d="M3 16.8 12 21l9-4.2" />
            </svg>
          </span>
          <div class="stat-body">
            <p class="stat-label">接口总数</p>
            <p class="stat-value">{{ apiTotalText }}</p>
          </div>
        </article>

        <article class="stat">
          <span class="stat-icon stat-icon--violet">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3.2 20 7.6v8.8L12 20.8 4 16.4V7.6L12 3.2Z" />
              <path d="M4 7.6 12 12l8-4.4" />
              <path d="M12 12v8.8" />
            </svg>
          </span>
          <div class="stat-body">
            <p class="stat-label">业务模块</p>
            <p class="stat-value">{{ moduleTotalText }}</p>
          </div>
        </article>

        <article class="stat">
          <span class="stat-icon stat-icon--green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3l7 2.6v5.6c0 4.1-3 7.4-7 8.8-4-1.4-7-4.7-7-8.8V5.6L12 3Z" />
              <path d="M8.8 12.2l2.2 2.2 4.4-4.4" />
            </svg>
          </span>
          <div class="stat-body">
            <p class="stat-label">服务状态</p>
            <p class="stat-value stat-value--text"
               :title="serviceOk === null ? '正在检测' : `响应 ${serviceMs} ms`">
              {{ serviceText }}
              <i class="dot"
                 :class="{ 'dot--bad': serviceOk === false, 'dot--wait': serviceOk === null }"></i>
            </p>
          </div>
        </article>
      </div>

      <svg class="ov-wave" viewBox="0 0 1200 140" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="dashWaveLine" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="#22d3ee" stop-opacity="0.15" />
            <stop offset="0.34" stop-color="#60a5fa" stop-opacity="0.9" />
            <stop offset="0.62" stop-color="#a78bfa" stop-opacity="0.6" />
            <stop offset="1" stop-color="#22d3ee" stop-opacity="0.12" />
          </linearGradient>
          <linearGradient id="dashWaveFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#3b82f6" stop-opacity="0.24" />
            <stop offset="1" stop-color="#3b82f6" stop-opacity="0" />
          </linearGradient>
        </defs>
        <path
          d="M0 96C150 40 300 130 470 82c150-42 270 36 430 6 130-24 220 0 300-18v70H0Z"
          fill="url(#dashWaveFill)"
        />
        <path
          d="M0 96C150 40 300 130 470 82c150-42 270 36 430 6 130-24 220 0 300-18"
          fill="none"
          stroke="url(#dashWaveLine)"
          stroke-width="2"
        />
      </svg>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../store/auth.js'
import { fetchApiTotal, probeBackend } from '../api/stats.js'

const router = useRouter()

// ---------- 真实数据 ----------
const apiTotal = ref(null) // 后端 OpenAPI 里真实注册的接口数
const serviceOk = ref(null) // null = 检测中
const serviceMs = ref(0)

const apiTotalText = computed(() =>
  apiTotal.value === null ? '—' : String(apiTotal.value)
)

// 业务模块：真实路由表里「当前身份可进入」的页面数量
const moduleTotal = computed(() =>
  router
    .getRoutes()
    .filter((r) => {
      if (r.meta?.public) return false
      if (r.path === '/' || r.path === '/dashboard') return false
      return !r.meta?.role || r.meta.role === auth.role
    })
    .length
)

const moduleTotalText = computed(() =>
  String(moduleTotal.value).padStart(2, '0')
)

const serviceText = computed(() => {
  if (serviceOk.value === null) return '检测中'
  return serviceOk.value ? '运行稳定' : '连接异常'
})

// ---------- 日期 ----------
const now = new Date()
const pad = (n) => String(n).padStart(2, '0')
const WEEK = ['日', '一', '二', '三', '四', '五', '六']
const todayText = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(
  now.getDate()
)} 星期${WEEK[now.getDay()]}`

onMounted(async () => {
  // 两个请求互不阻塞，任一失败都不影响另一个
  const [api, health] = await Promise.allSettled([
    fetchApiTotal(),
    probeBackend()
  ])

  if (api.status === 'fulfilled') {
    apiTotal.value = api.value
  } else {
    apiTotal.value = 0
  }

  if (health.status === 'fulfilled') {
    serviceOk.value = health.value.ok
    serviceMs.value = health.value.ms
  } else {
    serviceOk.value = false
  }
})
</script>

<style scoped>
/* ================= 容器 ================= */
.home {
  position: relative;
  overflow: hidden;
  border-radius: 26px;
  border: 1px solid rgba(96, 165, 250, 0.16);
  background:
    linear-gradient(150deg, #071227 0%, #0a1b38 38%, #050c1a 100%);
  box-shadow: 0 30px 80px rgba(2, 8, 23, 0.6);
  padding-bottom: 22px;
}

/* ================= 背景光效 ================= */
.scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.glow {
  position: absolute;
  border-radius: 50%;
}

.glow--a {
  width: 620px;
  height: 620px;
  top: -300px;
  left: 12%;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.42), transparent 62%);
}

.glow--b {
  width: 520px;
  height: 520px;
  bottom: -260px;
  right: -100px;
  background: radial-gradient(circle, rgba(14, 165, 233, 0.26), transparent 64%);
}

.streak {
  position: absolute;
  border-radius: 50%;
  filter: blur(14px);
  opacity: 0.4;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(56, 189, 248, 0.75),
    rgba(167, 139, 250, 0.5),
    transparent
  );
}

.streak--a {
  width: 780px;
  height: 3px;
  top: 8%;
  right: -160px;
  transform: rotate(-9deg);
}

.streak--b {
  width: 900px;
  height: 3px;
  bottom: 6%;
  left: -220px;
  transform: rotate(-6deg);
  opacity: 0.28;
}

.streak--c {
  width: 460px;
  height: 2px;
  top: 52%;
  left: -120px;
  transform: rotate(14deg);
  opacity: 0.2;
}

/* ================= 主视觉布局 ================= */
.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.06fr) minmax(0, 0.94fr);
  align-items: center;
  gap: 20px;
  padding: 52px 34px 18px 46px;
}

.hero-copy {
  min-width: 0;
}

/* ---- 小字：姓名 + 身份 ---- */
.kicker {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: #7ea6d8;
}

.kicker-tag {
  letter-spacing: 0.22em;
}

.kicker-user {
  font-size: 12.5px;
  font-weight: 600;
  color: #d6e7ff;
  letter-spacing: 0.04em;
}

.kicker-role {
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: #7dd3fc;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.kicker-line {
  width: 56px;
  height: 1px;
  background: linear-gradient(90deg, rgba(125, 211, 252, 0.75), transparent);
}

/* ---- 大标题 ---- */
.hero-title {
  margin-top: 18px;
  font-size: clamp(28px, 3.5vw, 44px);
  font-weight: 800;
  line-height: 1.28;
  letter-spacing: 0.01em;
  color: #eaf2ff;
}

.hero-title .grad {
  background: linear-gradient(100deg, #4f8cff, #35d6ff 58%, #9af0ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 26px rgba(56, 189, 248, 0.35));
}

.hero-sub {
  margin-top: 16px;
  font-size: 14.5px;
  letter-spacing: 0.05em;
  color: #93b4d6;
}

/* ---- CTA ---- */
.cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 30px;
  padding: 13px 26px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  text-decoration: none;
  background: linear-gradient(100deg, #22d3ee, #3b82f6);
  box-shadow:
    0 12px 30px rgba(37, 99, 235, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.cta svg {
  width: 17px;
  height: 17px;
}

.cta:hover {
  transform: translateY(-2px);
  box-shadow:
    0 18px 42px rgba(37, 99, 235, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.42);
}

/* ================= 3D 舞台 ================= */
.stage {
  position: relative;
  height: 330px;
  display: grid;
  place-items: center;
}

.stage-glow {
  position: absolute;
  width: 430px;
  height: 430px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(37, 99, 235, 0.55),
    rgba(14, 165, 233, 0.16) 46%,
    transparent 68%
  );
  filter: blur(6px);
}

.orbit {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(96, 165, 250, 0.35);
}

.orbit--a {
  width: 372px;
  height: 126px;
  transform: rotate(-13deg);
  box-shadow: 0 0 34px rgba(56, 189, 248, 0.22);
  animation: orbit-pulse 7s ease-in-out infinite;
}

.orbit--b {
  width: 296px;
  height: 94px;
  transform: rotate(10deg);
  border-color: rgba(147, 197, 253, 0.22);
  animation: orbit-pulse 7s ease-in-out infinite reverse;
}

@keyframes orbit-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}

.platform {
  position: absolute;
  bottom: 46px;
  width: 268px;
  height: 78px;
  border-radius: 50%;
  background: radial-gradient(
    ellipse at center,
    rgba(96, 165, 250, 0.42),
    rgba(30, 64, 175, 0.14) 56%,
    transparent 74%
  );
  border: 1px solid rgba(125, 211, 252, 0.26);
  box-shadow:
    0 0 46px rgba(56, 189, 248, 0.32),
    inset 0 0 34px rgba(37, 99, 235, 0.35);
}

.platform i {
  position: absolute;
  inset: 14px 22px;
  border-radius: 50%;
  border: 1px solid rgba(147, 197, 253, 0.3);
  background: radial-gradient(
    ellipse at center,
    rgba(56, 189, 248, 0.3),
    transparent 72%
  );
}

.cube {
  position: relative;
  width: 164px;
  height: 164px;
  margin-bottom: 44px;
  border-radius: 30px;
  display: grid;
  place-items: center;
  background: linear-gradient(
    150deg,
    rgba(147, 197, 253, 0.95),
    rgba(59, 130, 246, 0.86) 38%,
    rgba(29, 78, 216, 0.92) 78%
  );
  border: 1px solid rgba(191, 219, 254, 0.6);
  box-shadow:
    0 30px 70px rgba(2, 6, 23, 0.7),
    0 0 62px rgba(56, 189, 248, 0.5),
    inset 0 2px 0 rgba(255, 255, 255, 0.55),
    inset 0 -34px 60px rgba(13, 52, 120, 0.6);
  animation: cube-float 6.5s ease-in-out infinite;
}

.cube::before {
  content: '';
  position: absolute;
  inset: 8px;
  border-radius: 24px;
  background: linear-gradient(
    140deg,
    rgba(255, 255, 255, 0.4),
    rgba(255, 255, 255, 0) 44%
  );
  pointer-events: none;
}

.cube b {
  position: relative;
  font-size: 92px;
  font-weight: 900;
  line-height: 1;
  background: linear-gradient(160deg, #ffffff, #c9e9ff 42%, #4aa8ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 20px rgba(191, 230, 255, 0.85));
}

@keyframes cube-float {
  0%, 100% {
    transform: perspective(760px) rotateX(9deg) rotateY(-20deg) rotateZ(-7deg)
      translateY(0);
  }
  50% {
    transform: perspective(760px) rotateX(9deg) rotateY(-20deg) rotateZ(-7deg)
      translateY(-13px);
  }
}

/* 浮空碎块 */
.shard {
  position: absolute;
  border-radius: 6px;
  background: linear-gradient(150deg, rgba(147, 197, 253, 0.9), rgba(37, 99, 235, 0.5));
  box-shadow: 0 0 18px rgba(96, 165, 250, 0.6);
  animation: shard-drift 9s ease-in-out infinite;
}

.shard--1 {
  width: 16px;
  height: 16px;
  top: 46px;
  right: 78px;
  transform: rotate(24deg);
  animation-delay: -1s;
}

.shard--2 {
  width: 10px;
  height: 10px;
  top: 118px;
  right: 34px;
  transform: rotate(-16deg);
  opacity: 0.75;
  animation-delay: -3.4s;
}

.shard--3 {
  width: 13px;
  height: 13px;
  bottom: 96px;
  left: 44px;
  transform: rotate(38deg);
  opacity: 0.8;
  animation-delay: -5.2s;
}

.shard--4 {
  width: 8px;
  height: 8px;
  top: 76px;
  left: 62px;
  transform: rotate(-28deg);
  opacity: 0.6;
  animation-delay: -7s;
}

@keyframes shard-drift {
  0%, 100% { translate: 0 0; }
  50% { translate: 0 -16px; }
}

/* ================= 平台概览 ================= */
.overview {
  position: relative;
  overflow: hidden;
  margin: 4px 18px 0;
  padding: 22px 26px 34px;
  border-radius: 20px;
  background: linear-gradient(
    180deg,
    rgba(16, 38, 78, 0.66),
    rgba(9, 20, 42, 0.8)
  );
  border: 1px solid rgba(96, 165, 250, 0.18);
  box-shadow: inset 0 1px 0 rgba(147, 197, 253, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.ov-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ov-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: #7dd3fc;
  background: linear-gradient(150deg, rgba(56, 189, 248, 0.3), rgba(37, 99, 235, 0.16));
  box-shadow:
    inset 0 0 0 1px rgba(125, 211, 252, 0.25),
    0 0 22px rgba(56, 189, 248, 0.2);
}

.ov-icon svg {
  width: 20px;
  height: 20px;
}

.ov-title h2 {
  font-size: 16.5px;
  font-weight: 700;
  color: #e8f2ff;
  letter-spacing: 0.02em;
}

.ov-title p {
  margin-top: 3px;
  font-size: 11.5px;
  color: #7f9dbd;
  letter-spacing: 0.04em;
}

.ov-date {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #8fb0d0;
  letter-spacing: 0.03em;
}

.ov-date svg {
  width: 14px;
  height: 14px;
  opacity: 0.8;
}

/* ---- 三块指标 ---- */
.ov-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 20px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 8px 22px;
  min-width: 0;
}

.stat:first-child {
  padding-left: 2px;
}

.stat + .stat {
  position: relative;
}

.stat + .stat::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12%;
  bottom: 12%;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(125, 211, 252, 0.28),
    transparent
  );
}

.stat-icon {
  flex-shrink: 0;
  width: 46px;
  height: 46px;
  border-radius: 13px;
  display: grid;
  place-items: center;
}

.stat-icon svg {
  width: 22px;
  height: 22px;
}

.stat-icon--blue {
  color: #7dd3fc;
  background: linear-gradient(150deg, rgba(56, 189, 248, 0.3), rgba(37, 99, 235, 0.16));
  box-shadow:
    inset 0 0 0 1px rgba(125, 211, 252, 0.22),
    0 0 22px rgba(56, 189, 248, 0.22);
}

.stat-icon--violet {
  color: #c4b5fd;
  background: linear-gradient(150deg, rgba(139, 92, 246, 0.32), rgba(79, 70, 229, 0.16));
  box-shadow:
    inset 0 0 0 1px rgba(196, 181, 253, 0.22),
    0 0 22px rgba(139, 92, 246, 0.22);
}

.stat-icon--green {
  color: #6ee7b7;
  background: linear-gradient(150deg, rgba(16, 185, 129, 0.32), rgba(5, 150, 105, 0.16));
  box-shadow:
    inset 0 0 0 1px rgba(110, 231, 183, 0.22),
    0 0 22px rgba(16, 185, 129, 0.22);
}

.stat-body {
  min-width: 0;
}

.stat-label {
  font-size: 12.5px;
  color: #8fb0d0;
  letter-spacing: 0.06em;
}

.stat-value {
  margin-top: 5px;
  font-size: clamp(24px, 2.4vw, 32px);
  font-weight: 800;
  line-height: 1.1;
  color: #eaf4ff;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}

.stat-value--text {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: clamp(19px, 1.8vw, 23px);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 10px #34d399;
}

.dot--bad {
  background: #fb7185;
  box-shadow: 0 0 10px #fb7185;
}

.dot--wait {
  background: #7f9dbd;
  box-shadow: 0 0 10px #7f9dbd;
  animation: dot-blink 1.2s ease-in-out infinite;
}

@keyframes dot-blink {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 1; }
}

/* ---- 底部光波 ---- */
.ov-wave {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 76px;
  pointer-events: none;
  opacity: 0.9;
}

/* ================= 响应式 ================= */
@media (max-width: 940px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
    padding: 36px 26px 4px;
  }

  .stage {
    height: 250px;
  }

  .stage-glow {
    width: 320px;
    height: 320px;
  }

  .orbit--a {
    width: 280px;
    height: 96px;
  }

  .orbit--b {
    width: 224px;
    height: 72px;
  }

  .platform {
    bottom: 22px;
    width: 210px;
    height: 62px;
  }

  .cube {
    width: 122px;
    height: 122px;
    margin-bottom: 22px;
    border-radius: 24px;
  }

  .cube b {
    font-size: 68px;
  }

  .ov-stats {
    grid-template-columns: minmax(0, 1fr);
  }

  .stat {
    padding: 14px 2px;
  }

  .stat + .stat {
    border-top: 1px solid rgba(125, 211, 252, 0.12);
  }

  .stat + .stat::before {
    content: none;
  }

  .ov-head {
    flex-wrap: wrap;
  }

  .ov-date {
    margin-left: 0;
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cube,
  .orbit,
  .shard {
    animation: none;
  }
}
</style>

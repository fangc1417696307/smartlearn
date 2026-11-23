<template>
  <div class="screen">
    <header class="screen-head">
      <div class="title-wrap">
        <span class="live-dot" :class="{ off: !redis.connected }"></span>
        <div>
          <h1>实时数据中枢</h1>
          <div class="subtitle">业务指标 · Redis 缓存 · Kafka 消息队列</div>
        </div>
      </div>
      <div class="head-right">
        <span class="status" :class="redis.connected ? 'ok' : 'off'">
          <i></i>Redis {{ redis.connected ? '在线' : '未连接' }}
        </span>
        <span class="status" :class="mq.connected ? 'ok' : 'off'">
          <i></i>MQ {{ mq.connected ? '在线' : '未连接' }}
        </span>
        <span class="clock">{{ clock }}</span>
        <el-button class="demo-btn" size="small" :loading="firing" @click="fireDemo">模拟活动</el-button>
      </div>
    </header>

    <div class="kpi-grid">
      <div v-for="k in kpis" :key="k.label" class="kpi">
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-value">{{ k.value }}<span class="unit">{{ k.unit }}</span></div>
        <div class="kpi-foot">{{ k.foot }}</div>
      </div>
    </div>

    <div class="main-grid">
      <section class="panel redis-panel">
        <header><span class="dot blue"></span>Redis 缓存层<small>CACHE</small></header>
        <div class="redis-top">
          <div ref="gaugeRef" class="gauge"></div>
          <div class="redis-metrics">
            <div><b>{{ redis.memory_human || '—' }}</b><span>内存占用</span></div>
            <div><b>{{ redis.keys ?? 0 }}</b><span>Key 数量</span></div>
            <div><b>{{ redis.ops_per_sec ?? 0 }}</b><span>OPS</span></div>
            <div><b>{{ redis.clients ?? 0 }}</b><span>客户端</span></div>
          </div>
        </div>
        <div class="bar-row">
          <span>应用缓存命中率</span>
          <span>{{ cache.hit_rate ?? 0 }}% <em>({{ cache.hits ?? 0 }}/{{ cache.total ?? 0 }})</em></span>
        </div>
        <div class="progress"><i :style="{ width: (cache.hit_rate || 0) + '%' }"></i></div>
        <div class="redis-foot">
          <span>Redis {{ redis.version || '—' }}</span>
          <span>缓存 TTL {{ redis.cache_ttl ?? 5 }}s</span>
          <span>服务端命中率 {{ redis.server_hit_rate ?? 0 }}%</span>
        </div>
      </section>

      <section class="panel mq-panel">
        <header><span class="dot cyan"></span>消息队列 · Kafka<small>MQ</small></header>
        <div ref="mqRef" class="mq-chart"></div>
        <div class="mq-stats">
          <div><b>{{ mq.produced ?? 0 }}</b><span>累计生产</span></div>
          <div><b>{{ mq.consumed ?? 0 }}</b><span>累计消费</span></div>
          <div><b>{{ mq.length ?? 0 }}</b><span>Topic 消息数</span></div>
          <div><b>{{ mq.lag ?? 0 }}</b><span>消费者 Lag</span></div>
        </div>
        <div class="mq-foot">
          Topic {{ mq.topic || 'smartlearn.events' }} · {{ mq.partitions ?? 0 }} 分区 · {{ mq.consumers ?? 0 }} 消费者
        </div>
      </section>

      <section class="panel events-panel">
        <header><span class="dot lime"></span>实时事件流<small>LIVE</small></header>
        <div class="events">
          <div v-for="e in events" :key="e.id" class="event">
            <span class="ev-tag" :class="'t-' + (e.type || 'event')">{{ typeLabel(e.type) }}</span>
            <div class="ev-body">
              <b>{{ e.nickname || e.account || '系统' }}</b>
              <span>{{ e.detail || e.type }}</span>
            </div>
            <span class="ev-time">{{ fmtTime(e.ts) }}</span>
          </div>
          <div v-if="!events.length" class="empty">
            暂无事件，点击右上角「模拟活动」体验消息队列
          </div>
        </div>
      </section>
    </div>

    <div class="bottom-grid">
      <section class="panel">
        <header><span class="dot violet"></span>角色分布<small>ROLE</small></header>
        <div ref="pieRef" class="chart"></div>
      </section>
      <section class="panel">
        <header><span class="dot blue"></span>近 7 天新增用户<small>REGISTER</small></header>
        <div ref="barRef" class="chart"></div>
      </section>
      <section class="panel">
        <header><span class="dot cyan"></span>在线人数趋势<small>ONLINE</small></header>
        <div ref="onlineRef" class="chart"></div>
      </section>
    </div>

    <div class="flow">
      <span class="flow-title">数据链路</span>
      <div class="flow-step"><b>业务事件</b><span>登录 · 注册 · 资源生成 · 答疑</span></div>
      <span class="arrow">→</span>
      <div class="flow-step"><b>Kafka</b><span>PRODUCE → smartlearn.events</span></div>
      <span class="arrow">→</span>
      <div class="flow-step"><b>消费者组 bigscreen</b><span>POLL + COMMIT OFFSET</span></div>
      <span class="arrow">→</span>
      <div class="flow-step"><b>实时大屏</b><span>2s 轮询 + Redis 缓存</span></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import api from '../api'

const clock = ref('')
const firing = ref(false)
const redis = ref({ connected: false, cache: {} })
const mq = ref({ connected: false, topic: 'smartlearn.events', partitions: 0, consumers: 0, series: [] })
const overview = ref({ total_users: 0, pending_users: 0, today_new: 0, role_distribution: [], last_7_days: [] })
const online = ref({ count: 0, users: [] })
const events = ref([])

const cache = computed(() => redis.value.cache || {})

const kpis = computed(() => {
  const series = mq.value.series || []
  const recent = series.slice(-5)
  const totalProduced = recent.reduce((sum, s) => sum + (s.produced || 0), 0)
  const msgPerSec = recent.length ? Math.round(totalProduced / recent.length) : 0
  return [
    { label: '总用户数', value: overview.value.total_users ?? 0, unit: '人', foot: `角色 ${(overview.value.role_distribution || []).length} 类` },
    { label: '在线用户', value: online.value.count ?? 0, unit: '人', foot: 'WebSocket 实时连接' },
    { label: '今日新增', value: overview.value.today_new ?? 0, unit: '人', foot: `待审核 ${overview.value.pending_users ?? 0}` },
    { label: '消息吞吐 / 秒', value: msgPerSec, unit: 'msg/s', foot: `累计 ${mq.value.produced ?? 0} 条` },
    { label: '缓存命中率', value: cache.value.hit_rate ?? 0, unit: '%', foot: `${cache.value.hits ?? 0} 次命中` },
    { label: '消息积压', value: mq.value.lag ?? 0, unit: '条', foot: `Topic 共 ${mq.value.length ?? 0} 条` },
  ]
})

const TYPE_LABELS = {
  login: '登录',
  register: '注册',
  user_create: '建号',
  user_update: '改号',
  user_delete: '删号',
  teacher_approve: '审核通过',
  teacher_reject: '审核拒绝',
  resource_generate: '资源生成',
  qa_ask: '智能答疑',
  assessment: '学习评估',
  path_update: '路径更新',
}
const typeLabel = (t) => TYPE_LABELS[t] || '事件'
const fmtTime = (ts) => {
  const n = typeof ts === 'string' ? Number(ts) : ts
  return n ? new Date(n).toLocaleTimeString('zh-CN', { hour12: false }) : '—'
}

const gaugeRef = ref(null)
const mqRef = ref(null)
const pieRef = ref(null)
const barRef = ref(null)
const onlineRef = ref(null)
let charts = {}
let timer = null
let clockTimer = null
let loading = false

const AXIS = 'rgba(25, 25, 25, .12)'
const SPLIT = 'rgba(25, 25, 25, .06)'
const MUTED = '#a3a399'
const TOOLTIP = {
  backgroundColor: '#fff',
  borderColor: '#e5e5e5',
  textStyle: { color: '#191919' },
  extraCssText: 'box-shadow: 0 8px 24px rgba(25, 25, 25, .12); border-radius: 12px;',
}

function initCharts() {
  charts.gauge = echarts.init(gaugeRef.value)
  charts.mq = echarts.init(mqRef.value)
  charts.pie = echarts.init(pieRef.value)
  charts.bar = echarts.init(barRef.value)
  charts.online = echarts.init(onlineRef.value)

  charts.gauge.setOption({
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      radius: '96%',
      center: ['50%', '56%'],
      progress: {
        show: true,
        width: 11,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#2908ff' },
            { offset: 1, color: '#00b5c2' },
          ]),
        },
      },
      axisLine: { lineStyle: { width: 11, color: [[1, '#eeecde']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      anchor: { show: false },
      title: { offsetCenter: [0, '58%'], color: '#737373', fontSize: 11 },
      detail: {
        offsetCenter: [0, '4%'],
        fontSize: 28,
        fontWeight: 800,
        color: '#191919',
        formatter: '{value}%',
      },
      data: [{ value: 0, name: '应用缓存命中率' }],
    }],
  })

  charts.mq.setOption({
    grid: { left: 38, right: 14, top: 30, bottom: 24 },
    tooltip: { trigger: 'axis', ...TOOLTIP },
    legend: { right: 0, top: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: '#737373', fontSize: 11 } },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: { lineStyle: { color: AXIS } },
      axisTick: { show: false },
      axisLabel: { color: MUTED, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: SPLIT } },
      axisLabel: { color: MUTED, fontSize: 10 },
    },
    series: [
      { name: '生产', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 2, color: '#2908ff' }, areaStyle: { color: 'rgba(41, 8, 255, .12)' } },
      { name: '消费', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 2, color: '#00b5c2' }, areaStyle: { color: 'rgba(0, 181, 194, .12)' } },
    ],
  })

  const commonLegend = { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: '#737373', fontSize: 11 } }
  charts.pie.setOption({
    tooltip: { trigger: 'item', ...TOOLTIP },
    legend: commonLegend,
    color: ['#2908ff', '#00b5c2', '#bcf887', '#7c5cff', '#f472b6', '#f59e0b'],
    series: [{
      type: 'pie',
      radius: ['42%', '66%'],
      center: ['50%', '44%'],
      data: [],
      label: { color: '#737373', fontSize: 11, formatter: '{b} {c}' },
      labelLine: { lineStyle: { color: 'rgba(25, 25, 25, .18)' } },
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
    }],
  })

  charts.bar.setOption({
    grid: { left: 34, right: 12, top: 18, bottom: 26 },
    tooltip: { trigger: 'axis', ...TOOLTIP },
    xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: AXIS } }, axisTick: { show: false }, axisLabel: { color: MUTED, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: SPLIT } }, axisLabel: { color: MUTED, fontSize: 10 } },
    series: [{
      type: 'bar',
      data: [],
      barWidth: '46%',
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#2908ff' },
          { offset: 1, color: 'rgba(41, 8, 255, .16)' },
        ]),
      },
    }],
  })

  charts.online.setOption({
    grid: { left: 34, right: 12, top: 18, bottom: 26 },
    tooltip: { trigger: 'axis', ...TOOLTIP },
    xAxis: { type: 'category', boundaryGap: false, data: [], axisLine: { lineStyle: { color: AXIS } }, axisTick: { show: false }, axisLabel: { color: MUTED, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: SPLIT } }, axisLabel: { color: MUTED, fontSize: 10 } },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: [],
      lineStyle: { width: 2, color: '#7c5cff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(124, 92, 255, .24)' },
          { offset: 1, color: 'rgba(124, 92, 255, 0)' },
        ]),
      },
    }],
  })
}

function updateCharts() {
  const series = mq.value.series || []
  const labels = series.map((s) => new Date(s.t).toLocaleTimeString('zh-CN', { hour12: false }))

  charts.gauge.setOption({
    series: [{ data: [{ value: cache.value.hit_rate ?? 0, name: '应用缓存命中率' }] }],
  })

  charts.mq.setOption({
    xAxis: { data: labels },
    series: [
      { data: series.map((s) => s.produced || 0) },
      { data: series.map((s) => s.consumed || 0) },
    ],
  })

  charts.pie.setOption({
    series: [{
      data: (overview.value.role_distribution || []).map((r) => ({ name: r.name, value: r.count })),
    }],
  })

  charts.bar.setOption({
    xAxis: { data: (overview.value.last_7_days || []).map((d) => d.date) },
    series: [{ data: (overview.value.last_7_days || []).map((d) => d.count) }],
  })

  charts.online.setOption({
    xAxis: { data: labels },
    series: [{ data: series.map((s) => s.online || 0) }],
  })
}

function updateClock() {
  clock.value = new Date().toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
}

async function load() {
  if (loading) return
  loading = true
  try {
    const data = await api.get('/stats/bigscreen', { silent: true })
    redis.value = data.redis || { connected: false, cache: {} }
    mq.value = data.mq || { connected: false, series: [] }
    overview.value = data.overview || overview.value
    online.value = data.online || { count: 0, users: [] }
    events.value = data.events || []
    updateCharts()
  } catch {
    /* 轮询失败不弹窗，页面保留上一帧数据；顶部在线状态会反映连接情况 */
  } finally {
    loading = false
  }
}

async function fireDemo() {
  if (firing.value) return
  firing.value = true
  try {
    const res = await api.post('/stats/demo-events?count=8')
    ElMessage.success(`已投递 ${res.produced} 条消息到队列`)
    setTimeout(load, 800)
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    firing.value = false
  }
}

function onResize() {
  Object.values(charts).forEach((c) => c.resize())
}

onMounted(async () => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  await nextTick()
  initCharts()
  await load()
  timer = setInterval(load, 2000)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(clockTimer)
  window.removeEventListener('resize', onResize)
  Object.values(charts).forEach((c) => c.dispose())
  charts = {}
})
</script>

<style scoped>
.screen {
  position: relative;
  padding: 20px 22px 24px;
  border-radius: 26px;
  color: #191919;
  background:
    radial-gradient(820px 380px at 6% -12%, rgba(188, 248, 135, 0.42), transparent 60%),
    radial-gradient(700px 340px at 98% -8%, rgba(41, 8, 255, 0.07), transparent 60%),
    linear-gradient(180deg, #fffdf8 0%, #f7f6ef 100%);
  border: 1px solid #e5e5e5;
  box-shadow: 0 16px 40px rgba(25, 25, 25, 0.07);
  overflow: hidden;
}
.screen::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(41, 8, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(41, 8, 255, 0.035) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: linear-gradient(to bottom, #000, transparent 82%);
  mask-image: linear-gradient(to bottom, #000, transparent 82%);
  pointer-events: none;
}
.screen-head { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.title-wrap { display: flex; align-items: center; gap: 12px; }
.live-dot { width: 10px; height: 10px; border-radius: 50%; background: #00b5c2; box-shadow: 0 0 0 4px rgba(0, 181, 194, 0.14); animation: pulse 1.8s infinite; }
.live-dot.off { background: #e5484d; box-shadow: 0 0 0 4px rgba(229, 72, 77, 0.12); }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.82); } }
h1 { margin: 0; font-family: 'Bitter', serif; font-size: 24px; font-weight: 800; letter-spacing: 0.3px; color: #191919; }
.subtitle { font-size: 12px; color: #737373; margin-top: 3px; letter-spacing: 0.3px; }
.head-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
.status { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: #737373; background: #fff; border: 1px solid #e5e5e5; border-radius: 999px; padding: 4px 10px; }
.status i { width: 7px; height: 7px; border-radius: 50%; background: #e5484d; }
.status.ok i { background: #12b76a; box-shadow: 0 0 0 3px rgba(18, 183, 106, 0.13); }
.status.ok { color: #1f7a4c; border-color: #cdebd9; background: #f3fbf6; }
.clock { font-family: 'Bitter', serif; font-size: 13px; color: #737373; letter-spacing: 0.6px; }
.demo-btn { border-radius: 999px; background: #bcf887; border-color: #bcf887; color: #1f06d6; font-weight: 700; }
.demo-btn:hover { background: #a8ef62; border-color: #a8ef62; color: #1f06d6; }

.kpi-grid { position: relative; display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 14px; }
.kpi { position: relative; overflow: hidden; padding: 13px 16px; border-radius: 16px; background: #fff; border: 1px solid #e8e6dc; box-shadow: 0 4px 14px rgba(25, 25, 25, 0.04); }
.kpi::after { content: ''; position: absolute; right: -24px; top: -24px; width: 76px; height: 76px; border-radius: 50%; background: radial-gradient(circle, rgba(188, 248, 135, 0.5), transparent 70%); }
.kpi:nth-child(3n + 2)::after { background: radial-gradient(circle, rgba(41, 8, 255, 0.09), transparent 70%); }
.kpi:nth-child(3n)::after { background: radial-gradient(circle, rgba(0, 181, 194, 0.14), transparent 70%); }
.kpi-label { font-size: 12px; color: #737373; }
.kpi-value { font-family: 'Bitter', serif; font-size: 29px; font-weight: 800; line-height: 1.15; color: #191919; }
.kpi-value .unit { font-size: 11px; color: #a3a399; margin-left: 4px; font-family: Inter, sans-serif; font-weight: 600; }
.kpi-foot { font-size: 11px; color: #a3a399; margin-top: 2px; }

.main-grid { position: relative; display: grid; grid-template-columns: 1.05fr 1.4fr 1.1fr; gap: 14px; margin-bottom: 14px; }
.bottom-grid { position: relative; display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.panel { position: relative; padding: 14px 16px; border-radius: 18px; background: #fff; border: 1px solid #e8e6dc; box-shadow: 0 6px 18px rgba(25, 25, 25, 0.04); }
.panel > header { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 800; color: #191919; margin-bottom: 10px; letter-spacing: 0.3px; }
.panel header small { margin-left: auto; font-size: 10px; color: #b3b3aa; letter-spacing: 1.6px; font-weight: 700; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.blue { background: #2908ff; box-shadow: 0 0 0 3px rgba(41, 8, 255, 0.1); }
.dot.cyan { background: #00b5c2; box-shadow: 0 0 0 3px rgba(0, 181, 194, 0.12); }
.dot.lime { background: #9bdd4f; box-shadow: 0 0 0 3px rgba(188, 248, 135, 0.3); }
.dot.violet { background: #7c5cff; box-shadow: 0 0 0 3px rgba(124, 92, 255, 0.12); }

.redis-top { display: grid; grid-template-columns: 1.05fr 1fr; gap: 4px; align-items: center; }
.gauge { height: 134px; }
.redis-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 10px; }
.redis-metrics div { background: #f7f6ef; border: 1px solid #eceade; border-radius: 12px; padding: 8px 10px; }
.redis-metrics b { display: block; font-family: 'Bitter', serif; font-size: 17px; color: #191919; }
.redis-metrics span { font-size: 10px; color: #a3a399; }
.bar-row { display: flex; justify-content: space-between; align-items: baseline; margin-top: 8px; font-size: 11px; color: #737373; }
.bar-row em { font-style: normal; color: #a3a399; }
.progress { height: 7px; border-radius: 999px; background: #eeecde; margin: 6px 0 9px; overflow: hidden; }
.progress i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #2908ff, #00b5c2); transition: width 0.5s ease; }
.redis-foot { display: flex; justify-content: space-between; gap: 8px; font-size: 10px; color: #a3a399; flex-wrap: wrap; }

.mq-chart { height: 205px; }
.mq-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 6px; }
.mq-stats div { text-align: center; background: #f7f6ef; border: 1px solid #eceade; border-radius: 12px; padding: 7px 4px; }
.mq-stats b { display: block; font-family: 'Bitter', serif; font-size: 17px; color: #191919; }
.mq-stats span { font-size: 10px; color: #a3a399; }
.mq-foot { margin-top: 7px; font-size: 10px; color: #a3a399; text-align: right; }

.events { height: 262px; overflow-y: auto; padding-right: 4px; }
.events::-webkit-scrollbar { width: 4px; }
.events::-webkit-scrollbar-thumb { background: #d9d9d0; border-radius: 4px; }
.event { display: flex; align-items: center; gap: 8px; padding: 7px 0; border-bottom: 1px dashed #eceade; animation: slideIn 0.35s ease; }
@keyframes slideIn { from { opacity: 0; transform: translateX(8px); } to { opacity: 1; transform: none; } }
.event:last-child { border-bottom: none; }
.ev-tag { flex-shrink: 0; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 999px; background: #e8e4ff; color: #2908ff; border: 1px solid #d0c9ff; }
.ev-tag.t-login { color: #2908ff; background: #ece8ff; border-color: #d5ceff; }
.ev-tag.t-register { color: #4f7a1f; background: #f1fadf; border-color: #d9efb7; }
.ev-tag.t-resource_generate { color: #007b85; background: #e4f7f8; border-color: #bfe9eb; }
.ev-tag.t-qa_ask { color: #6d4aff; background: #efeaff; border-color: #dcd2ff; }
.ev-tag.t-assessment { color: #c0266c; background: #fdeaf2; border-color: #f6cbdc; }
.ev-tag.t-user_create, .ev-tag.t-user_update, .ev-tag.t-user_delete,
.ev-tag.t-teacher_approve, .ev-tag.t-teacher_reject, .ev-tag.t-path_update { color: #a86a00; background: #fdf3e0; border-color: #f2ddb0; }
.ev-body { flex: 1; min-width: 0; font-size: 12px; color: #737373; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ev-body b { color: #191919; margin-right: 5px; font-weight: 700; }
.ev-time { flex-shrink: 0; font-size: 10px; color: #b3b3aa; font-family: 'Bitter', serif; }
.empty { padding: 42px 10px; text-align: center; font-size: 12px; color: #a3a399; line-height: 1.8; }

.chart { height: 220px; }

.flow {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: 16px;
  background: #f7f6ef;
  border: 1px solid #e8e6dc;
  flex-wrap: wrap;
}
.flow-title { font-size: 12px; font-weight: 800; color: #737373; letter-spacing: 1px; padding-right: 10px; border-right: 1px solid #e0ded2; }
.flow-step { flex: 1; min-width: 150px; padding: 6px 12px; border-radius: 10px; background: #fff; border: 1px solid #e8e6dc; }
.flow-step b { display: block; font-size: 12px; color: #191919; }
.flow-step span { font-size: 10px; color: #a3a399; }
.arrow { color: #2908ff; font-size: 18px; font-weight: 800; }

@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .main-grid, .bottom-grid { grid-template-columns: 1fr; }
  .events { height: 240px; }
}
@media (max-width: 720px) {
  .screen { padding: 16px; border-radius: 20px; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .screen-head { flex-direction: column; align-items: flex-start; }
  .head-right { justify-content: flex-start; }
}
</style>

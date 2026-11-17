<template>
  <div>
    <div class="hero">
      <div>
        <div class="hero-kicker">你的专属 AI 学习团队已就绪</div>
        <h2>你好，<span class="grad">{{ userStore.user?.nickname || '同学' }}</span> 👋</h2>
        <div class="hero-sub">多智能体已根据你的画像规划好路线，今天开始你的个性化学习。</div>
        <div class="hero-goal">🎯 学习目标：{{ profile?.goal?.text || '待完善' }}</div>
      </div>
      <AgentOrbit class="hero-orbit" :size="196" />
    </div>

    <div class="grid-2">
      <el-card shadow="never" class="panel">
        <template #header>
          <div class="panel-head"><span>📌 今日学习任务</span><a @click="$router.push('/path')">查看全部</a></div>
        </template>
        <div v-for="(t, i) in todayTasks" :key="i" class="task-item">
          <span class="task-check">✓</span>
          <div>
            <div class="task-title">{{ t.title }}</div>
            <div class="task-meta">{{ t.desc }}</div>
          </div>
          <span class="task-tag">{{ i === 0 ? '当前' : '后续' }}</span>
        </div>
        <div v-if="!todayTasks.length" class="empty">🎉 所有学习步骤都已完成！</div>
      </el-card>

      <el-card shadow="never" class="panel">
        <template #header>
          <div class="panel-head"><span>🧬 我的画像速览</span><a @click="$router.push('/profile')">详情</a></div>
        </template>
        <div v-for="d in snapshotDims" :key="d.key" class="dim-row">
          <span class="dim-label">{{ d.icon }} {{ d.name }}</span>
          <div class="dim-bar"><div class="dim-fill" :style="{ width: (profile?.[d.key]?.score || 50) + '%' }"></div></div>
          <span class="dim-val">{{ profile?.[d.key]?.score || 50 }}</span>
        </div>
      </el-card>
    </div>

    <el-card shadow="never" class="panel">
      <template #header>
        <div class="panel-head"><span>✨ 为你精准推送</span><a @click="$router.push('/resources')">进入资源中心</a></div>
      </template>
      <div class="resource-grid">
        <div v-for="r in pushResources" :key="r.id" class="resource-card" @click="$router.push('/resources/' + r.id)">
          <div class="r-icon">{{ r.icon }}</div>
          <div class="r-type">{{ r.typeLabel }}</div>
          <div class="r-title">{{ r.title }}</div>
          <div class="r-desc">{{ r.desc }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useUserStore } from '../store/user'
import { RESOURCES } from '../data/resources'
import AgentOrbit from '../components/AgentOrbit.vue'

const userStore = useUserStore()

const profile = computed(() => JSON.parse(localStorage.getItem('sl_profile_' + userStore.user?.account) || 'null'))
const path = computed(() => JSON.parse(localStorage.getItem('sl_path_' + userStore.user?.account) || '{"steps":[],"done":[]}'))

const snapshotDims = [
  { key: 'goal', name: '学习目标', icon: '🎯' },
  { key: 'foundation', name: '知识基础', icon: '🧱' },
  { key: 'history', name: '学习历史', icon: '📖' },
  { key: 'pace', name: '学习节奏', icon: '⏱️' },
]

const todayTasks = computed(() => path.value.steps.filter((s) => !path.value.done.includes(s.id)).slice(0, 3))
const pushResources = RESOURCES.slice(0, 4)
</script>

<style scoped>
.hero { border-radius: 30px; padding: 34px 38px; margin-bottom: 24px; background: #fff; border: 1px solid #e5e5e5; box-shadow: 0 10px 30px rgba(25,25,25,.07); position: relative; overflow: hidden; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.hero-orbit { flex-shrink: 0; }
.hero-kicker { display: inline-block; font-size: 12px; font-weight: 800; letter-spacing: 1px; color: #1f06d6; background: #bcf887; padding: 6px 14px; border-radius: 999px; margin-bottom: 14px; }
.hero h2 { font-size: 30px; font-weight: 800; margin-bottom: 10px; font-family: 'Bitter', serif; }
.hero .grad { color: #2908ff; }
.hero-sub { font-size: 14px; color: #737373; line-height: 1.7; }
.hero-goal { display: inline-block; margin-top: 18px; background: #eeecde; padding: 10px 18px; border-radius: 999px; font-size: 13px; font-weight: 700; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin-bottom: 22px; }
.panel { border-radius: 20px; }
.panel-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.panel-head a { color: #2908ff; font-size: 13px; cursor: pointer; }
.task-item { display: flex; align-items: center; gap: 12px; padding: 13px 14px; border: 1px solid #e5e5e5; border-radius: 14px; margin-bottom: 10px; }
.task-check { width: 24px; height: 24px; border-radius: 50%; border: 2px solid #d4d4d4; flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: transparent; }
.task-title { font-size: 14px; font-weight: 700; }
.task-meta { font-size: 12px; color: #737373; margin-top: 2px; }
.task-tag { margin-left: auto; font-size: 11px; padding: 5px 12px; border-radius: 999px; background: #bcf887; color: #1f06d6; font-weight: 800; }
.dim-row { display: flex; align-items: center; gap: 10px; font-size: 13px; margin-bottom: 11px; }
.dim-label { width: 90px; color: #737373; flex-shrink: 0; }
.dim-bar { flex: 1; height: 9px; background: #eeecde; border-radius: 999px; overflow: hidden; }
.dim-fill { height: 100%; background: #2908ff; border-radius: 999px; }
.dim-val { width: 40px; text-align: right; font-weight: 800; }
.empty { color: #737373; text-align: center; padding: 20px; }
.resource-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.resource-card { border: 1px solid #e5e5e5; border-radius: 16px; padding: 18px; cursor: pointer; transition: .15s; }
.resource-card:hover { border-color: #2908ff; transform: translateY(-2px); }
.r-icon { font-size: 26px; margin-bottom: 10px; }
.r-type { font-size: 11px; color: #2908ff; font-weight: 800; margin-bottom: 5px; }
.r-title { font-size: 14px; font-weight: 700; margin-bottom: 6px; }
.r-desc { font-size: 12px; color: #737373; line-height: 1.5; }
</style>

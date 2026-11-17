<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="head"><span>🧬 我的学习画像</span><span class="muted">最近更新：{{ profile?.updatedAt || '刚刚' }}</span></div>
    </template>
    <div class="dims">
      <div v-for="d in DIMS" :key="d.key" class="dim-card">
        <div class="icon">{{ d.icon }}</div>
        <div class="name">{{ d.name }}</div>
        <div class="desc">{{ profile?.[d.key]?.text || '待补充' }}</div>
        <div class="bar"><div class="fill" :style="{ width: (profile?.[d.key]?.score || 50) + '%' }"></div></div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
const DIMS = [
  { key: 'goal', name: '学习目标', icon: '🎯', desc: '驱动学习路径与资源优先级' },
  { key: 'foundation', name: '知识基础', icon: '🧱', desc: '决定资源难度与讲解深度' },
  { key: 'history', name: '学习历史', icon: '📖', desc: '影响内容衔接与查漏补缺' },
  { key: 'pace', name: '学习节奏', icon: '⏱️', desc: '决定路径长度与任务颗粒度' },
  { key: 'style', name: '认知风格', icon: '🧠', desc: '决定推送内容形态与权重' },
  { key: 'weakness', name: '易错点偏好', icon: '⚠️', desc: '影响练习与讲解侧重点' },
]
const profile = computed(() => JSON.parse(localStorage.getItem('sl_profile_' + userStore.user?.account) || 'null'))
</script>

<style scoped>
.panel { border-radius: 20px; }
.head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.muted { color: #737373; font-size: 12px; }
.dims { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.dim-card { border: 1px solid #e5e5e5; border-radius: 16px; padding: 18px; }
.icon { font-size: 24px; }
.name { font-size: 15px; font-weight: 800; margin: 6px 0; font-family: 'Bitter', serif; }
.desc { font-size: 13px; color: #737373; line-height: 1.6; }
.bar { height: 7px; background: #eeecde; border-radius: 999px; margin-top: 12px; overflow: hidden; }
.fill { height: 100%; background: #2908ff; border-radius: 999px; }
</style>

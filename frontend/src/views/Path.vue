<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="head">
        <div>
          <h3>🧭 我的学习路径</h3>
          <p class="muted">基于你的画像一次性生成，按顺序完成即可</p>
        </div>
        <div class="progress">
          <span class="pct">{{ pct }}%</span>
          <el-progress :percentage="pct" :stroke-width="8" color="#2908ff" :show-text="false" class="bar" />
        </div>
      </div>
    </template>
    <div class="steps">
      <div v-for="(s, i) in steps" :key="s.id" class="step" :class="{ done: done.includes(s.id), current: !done.includes(s.id) && i === done.length }">
        <div class="step-title">{{ i + 1 }}. {{ s.title }}</div>
        <div class="step-desc">{{ s.desc }}</div>
        <div class="step-res">
          <el-tag v-for="rid in s.res" :key="rid" class="chip" @click="$router.push('/resources/' + rid)">
            {{ resName(rid) }}
          </el-tag>
        </div>
        <el-button v-if="done.includes(s.id)" size="small" disabled class="done-btn">✅ 已掌握</el-button>
        <el-button v-else size="small" type="primary" class="done-btn" @click="markDone(s.id)">标记为已完成 / 已掌握</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '../store/user'
import { PATH_TEMPLATE, RESOURCES } from '../data/resources'

const userStore = useUserStore()
const steps = ref(PATH_TEMPLATE)
const pathKey = computed(() => 'sl_path_' + userStore.user?.account)
const done = ref(JSON.parse(localStorage.getItem('sl_path_' + userStore.user?.account) || '{"done":[]}').done || [])

const pct = computed(() => Math.round((done.value.length / steps.value.length) * 100))

function resName(id) {
  const r = RESOURCES.find((x) => x.id === id)
  return r ? r.icon + ' ' + r.title : id
}

function markDone(id) {
  if (!done.value.includes(id)) done.value.push(id)
  localStorage.setItem(pathKey.value, JSON.stringify({ steps: steps.value, done: done.value }))
}
</script>

<style scoped>
.panel { border-radius: 20px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.head h3 { font-family: 'Bitter', serif; }
.muted { color: #737373; font-size: 13px; margin-top: 4px; }
.progress { display: flex; align-items: center; gap: 10px; }
.pct { font-weight: 800; }
.bar { width: 140px; }
.steps { position: relative; padding-left: 28px; }
.steps::before { content: ''; position: absolute; left: 10px; top: 8px; bottom: 8px; width: 2px; background: #e5e5e5; }
.step { position: relative; padding: 15px 0 15px 22px; }
.step::before { content: ''; position: absolute; left: -23px; top: 22px; width: 17px; height: 17px; border-radius: 50%; background: #fff; border: 3px solid #d4d4d4; z-index: 1; }
.step.done::before { background: #22c55e; border-color: #22c55e; }
.step.current::before { background: #2908ff; border-color: #2908ff; box-shadow: 0 0 0 4px rgba(41, 8, 255, 0.14); }
.step-title { font-size: 15px; font-weight: 800; }
.step-desc { font-size: 13px; color: #737373; margin: 4px 0 10px; }
.step-res { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { cursor: pointer; border-radius: 999px; }
.done-btn { margin-top: 12px; border-radius: 999px; }
</style>

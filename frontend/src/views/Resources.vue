<template>
  <el-card shadow="never" class="panel">
    <div class="tabs">
      <el-button v-for="t in RES_TYPES" :key="t.key" :type="activeType === t.key ? 'primary' : ''" class="tab" @click="activeType = t.key">
        {{ t.icon }} {{ t.label }}
      </el-button>
    </div>
    <div class="grid">
      <div v-for="r in list" :key="r.id" class="card" @click="$router.push('/resources/' + r.id)">
        <div class="icon">{{ r.icon }}</div>
        <div class="type">{{ typeLabel(r.type) }}</div>
        <div class="title">{{ r.title }}</div>
        <div class="desc">{{ r.desc }}</div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RES_TYPES, RESOURCES } from '../data/resources'

const activeType = ref('all')
const list = computed(() => (activeType.value === 'all' ? RESOURCES : RESOURCES.filter((r) => r.type === activeType.value)))
function typeLabel(type) { return RES_TYPES.find((t) => t.key === type)?.label || type }
</script>

<style scoped>
.panel { border-radius: 20px; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 22px; }
.tab { border-radius: 999px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.card { border: 1px solid #e5e5e5; border-radius: 18px; padding: 20px; cursor: pointer; transition: 0.15s; position: relative; overflow: hidden; }
.card:hover { border-color: #2908ff; transform: translateY(-3px); box-shadow: 0 10px 30px rgba(25, 25, 25, 0.07); }
.icon { font-size: 28px; margin-bottom: 12px; }
.type { font-size: 11px; color: #2908ff; font-weight: 800; margin-bottom: 6px; }
.title { font-size: 15px; font-weight: 800; margin-bottom: 6px; font-family: 'Bitter', serif; }
.desc { font-size: 12px; color: #737373; line-height: 1.5; }
</style>

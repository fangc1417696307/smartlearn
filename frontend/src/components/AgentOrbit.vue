<template>
  <div class="agent-orbit" v-html="svg"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ size: { type: Number, default: 260 } })

const AGENTS = [
  { icon: '🔍', name: '学情分析', color: '#2908ff' },
  { icon: '📖', name: '课程讲解', color: '#00b5c2' },
  { icon: '✏️', name: '出题判分', color: '#2908ff' },
  { icon: '🧭', name: '路径规划', color: '#00b5c2' },
  { icon: '📤', name: '资源推送', color: '#16a34a' },
  { icon: '📊', name: '学习评估', color: '#2908ff' },
]

const svg = computed(() => {
  const size = props.size
  const cx = size / 2, cy = size / 2
  const coreR = Math.round(size * 0.1)
  const orbitR = Math.round(size / 2 - 46)
  const nodeR = Math.round(size * 0.075)
  const n = AGENTS.length
  const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n
  const pos = (i, r) => [cx + r * Math.cos(angle(i)), cy + r * Math.sin(angle(i))]

  let s = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`
  s += `<circle class="orbit-core-pulse" cx="${cx}" cy="${cy}" r="${coreR}" fill="none" stroke="#2908ff" stroke-width="2"/>`
  AGENTS.forEach((a, i) => {
    const [x, y] = pos(i, orbitR)
    s += `<line class="orbit-link" style="animation-delay:${(i * 0.22).toFixed(2)}s" x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${a.color}" stroke-width="2" stroke-linecap="round"/>`
  })
  s += `<circle cx="${cx}" cy="${cy}" r="${coreR}" fill="#2908ff"/>`
  s += `<text x="${cx}" y="${cy + coreR * 0.36}" text-anchor="middle" font-size="${coreR}" fill="#fff" font-weight="800" font-family="Bitter, serif">S</text>`
  AGENTS.forEach((a, i) => {
    const [x, y] = pos(i, orbitR)
    s += `<g class="orbit-node"><circle cx="${x}" cy="${y}" r="${nodeR}" fill="#fff" stroke="${a.color}" stroke-width="2"/><text x="${x}" y="${y + 5}" text-anchor="middle" font-size="${Math.round(nodeR * 0.66)}">${a.icon}</text><text x="${x}" y="${y + nodeR + 15}" text-anchor="middle" font-size="11" fill="#737373" font-weight="700">${a.name}</text></g>`
  })
  return s + '</svg>'
})
</script>

<style scoped>
.agent-orbit { display: flex; justify-content: center; }
</style>

<template>
  <div>
    <div class="grid-2">
      <el-card shadow="never" class="panel">
        <template #header><span class="head">📊 六维掌握度</span></template>
        <div class="radar" v-html="radarSvg"></div>
      </el-card>
      <el-card shadow="never" class="panel">
        <template #header><span class="head">📝 评估结论</span></template>
        <div class="conclusion">
          <b>总体结论：</b>你对「栈与队列」「二叉树」掌握较好，但「图」相关知识点较为薄弱，建议重点补强。<br />
          <b>易错点提醒：</b>根据你的画像，注意「细节遗漏」类错误，做练习时多检查边界条件。
        </div>
        <div class="stats">
          <div class="stat"><div class="num">12</div><div class="label">已完成资源</div></div>
          <div class="stat"><div class="num">68%</div><div class="label">练习正确率</div></div>
          <div class="stat"><div class="num">5</div><div class="label">薄弱知识点</div></div>
        </div>
      </el-card>
    </div>
    <el-card shadow="never" class="panel">
      <template #header><span class="head">🎯 调整后的推送策略</span></template>
      <p class="muted">评估结果仅调整资源推送，学习路径保持不变。</p>
    </el-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const data = [
  { label: '二叉树', value: 74 }, { label: '栈与队列', value: 88 },
  { label: '图', value: 42 }, { label: '排序', value: 65 },
  { label: '查找', value: 58 }, { label: '复杂度', value: 70 },
]

const radarSvg = computed(() => {
  const size = 300, cx = size / 2, cy = size / 2, r = 115
  const n = data.length
  const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n
  const pt = (i, radius) => [cx + radius * Math.cos(angle(i)), cy + radius * Math.sin(angle(i))]
  let svg = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`
  for (let lv = 1; lv <= 4; lv++) {
    const rr = (r / 4) * lv
    const poly = data.map((_, i) => pt(i, rr).map((v) => v.toFixed(1)).join(',')).join(' ')
    svg += `<polygon points="${poly}" fill="none" stroke="#e5e5e5" stroke-width="1"/>`
  }
  data.forEach((_, i) => { const [x, y] = pt(i, r); svg += `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#e5e5e5"/>` })
  const dataPoly = data.map((d, i) => pt(i, (r * d.value) / 100).map((v) => v.toFixed(1)).join(',')).join(' ')
  svg += `<polygon points="${dataPoly}" fill="rgba(41,8,255,.15)" stroke="#2908ff" stroke-width="2"/>`
  data.forEach((d, i) => {
    const [x, y] = pt(i, (r * d.value) / 100)
    svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="#2908ff"/>`
  })
  data.forEach((d, i) => {
    const [x, y] = pt(i, r + 22)
    svg += `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="12" text-anchor="middle" fill="#737373">${d.label} ${d.value}</text>`
  })
  return svg + '</svg>'
})
</script>

<style scoped>
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin-bottom: 22px; }
.panel { border-radius: 20px; }
.head { font-weight: 700; }
.radar { display: flex; justify-content: center; }
.conclusion { background: #f8f9fc; border: 1px solid #e5e5e5; border-radius: 14px; padding: 16px; font-size: 14px; line-height: 1.75; margin-bottom: 16px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat { text-align: center; padding: 16px; border: 1px solid #e5e5e5; border-radius: 14px; }
.num { font-size: 24px; font-weight: 800; color: #2908ff; font-family: 'Bitter', serif; }
.label { font-size: 12px; color: #737373; margin-top: 4px; }
.muted { color: #737373; font-size: 13px; }
</style>

<template>
  <el-card shadow="never" class="panel qa-wrap">
    <template #header>
      <div class="head"><span>💬 答疑</span><span class="pill">答疑老师 · 纯文字解答</span></div>
    </template>
    <div class="chat" ref="chatBox">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div v-if="m.agent" class="tag">答疑老师</div>
        <div class="bubble">{{ m.text }}</div>
      </div>
    </div>
    <div class="input-row">
      <el-input v-model="input" placeholder="输入你的问题，例如：什么是平衡二叉树的旋转？" @keyup.enter="send" />
      <el-button type="primary" @click="send">提问</el-button>
    </div>
  </el-card>
</template>

<script setup>
import { reactive, ref, nextTick } from 'vue'
import { QA_KNOWLEDGE } from '../data/resources'

const messages = reactive([{ role: 'bot', agent: true, text: '你好，我是答疑老师 👋 学习中遇到任何问题都可以问我，我会用文字给你讲清楚。' }])
const input = ref('')
const chatBox = ref(null)

function send() {
  const t = input.value.trim()
  if (!t) return
  messages.push({ role: 'user', text: t })
  input.value = ''
  const found = QA_KNOWLEDGE.find(([k]) => t.includes(k))
  const ans = found ? found[1] : '这是个好问题！建议你从「定义 → 性质 → 典型操作 → 复杂度」这条主线去理解。如果还卡壳，可以到「资源中心」回看对应的讲解文档与代码案例。'
  setTimeout(() => {
    messages.push({ role: 'bot', agent: true, text: ans })
    nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
  }, 500)
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}
</script>

<style scoped>
.qa-wrap { border-radius: 20px; display: flex; flex-direction: column; height: calc(100vh - 140px); }
.head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.pill { font-size: 12px; font-weight: 700; color: #1f06d6; background: #bcf887; padding: 6px 14px; border-radius: 999px; }
.chat { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; padding: 8px 4px; }
.msg { max-width: 76%; display: flex; flex-direction: column; gap: 4px; }
.msg.bot { align-self: flex-start; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.tag { font-size: 11px; color: #2908ff; font-weight: 700; }
.bubble { padding: 12px 16px; border-radius: 15px; font-size: 14px; line-height: 1.65; }
.msg.bot .bubble { background: #fff; border: 1px solid #e5e5e5; border-top-left-radius: 4px; }
.msg.user .bubble { background: #2908ff; color: #fff; border-top-right-radius: 4px; }
.input-row { display: flex; gap: 10px; margin-top: 12px; border-top: 1px solid #e5e5e5; padding-top: 12px; }
.input-row .el-button { border-radius: 999px; }
</style>

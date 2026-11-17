<template>
  <div class="onboarding">
    <header class="onb-header">
      <div class="brand">
        <div class="brand-logo">S</div>
        <div class="brand-name">SmartLearn</div>
      </div>
      <div class="header-right">
        <span class="agent-pill">学情分析师 · 正在为你构建画像</span>
        <el-button class="skip-btn" @click="finish(true)">跳过，直接进入</el-button>
      </div>
    </header>
    <div class="onb-body">
      <div class="chat-box" ref="chatBox">
        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <div v-if="m.agent" class="agent-tag">{{ m.agent }}</div>
          <div class="bubble">{{ m.text }}</div>
        </div>
      </div>
      <div class="input-bar">
        <div v-if="quickReplies.length" class="quick-replies">
          <el-button v-for="q in quickReplies" :key="q[0]" class="quick-btn" @click="answer(q)">{{ q[0] }}</el-button>
        </div>
        <div class="input-row">
          <el-input v-model="input" placeholder="输入你的回答…" @keyup.enter="submit" />
          <el-button type="primary" @click="submit">发送</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const chatBox = ref(null)

const DIMS = [
  { key: 'goal', name: '学习目标', icon: '🎯', desc: '驱动学习路径与资源优先级' },
  { key: 'foundation', name: '知识基础', icon: '🧱', desc: '决定资源难度与讲解深度' },
  { key: 'history', name: '学习历史', icon: '📖', desc: '影响内容衔接与查漏补缺' },
  { key: 'pace', name: '学习节奏', icon: '⏱️', desc: '决定路径长度与任务颗粒度' },
  { key: 'style', name: '认知风格', icon: '🧠', desc: '决定推送内容形态与权重' },
  { key: 'weakness', name: '易错点偏好', icon: '⚠️', desc: '影响练习与讲解侧重点' },
]

const SCRIPT = [
  { dim: 'goal', ask: '你好，我是学情分析师 🤖 为了给你生成专属学习画像，我们随便聊几句，不用填表。\n\n先告诉我：你这次学习最想达成什么目标？', quick: [['期末冲刺 90+', 80], ['考研备考', 70], ['兴趣入门', 45], ['就业求职技能', 85]] },
  { dim: 'foundation', ask: '收到！那你目前的计算机 / 编程基础大概是什么水平？', quick: [['零基础', 20], ['有一点基础', 40], ['比较扎实', 70], ['很熟练', 90]] },
  { dim: 'history', ask: '之前学过哪些相关课程呢？', quick: [['C 语言', 50], ['数据结构', 55], ['操作系统', 60], ['还没系统学过', 20]] },
  { dim: 'pace', ask: '你每周大概能投入多少时间学习？', quick: [['少于 5 小时', 25], ['5-10 小时', 45], ['10-20 小时', 70], ['20 小时以上', 90]] },
  { dim: 'style', ask: '你平时更喜欢哪种学习方式？', quick: [['看视频', 55], ['读文档', 60], ['动手写代码', 70], ['刷题', 65]] },
  { dim: 'weakness', ask: '最后，你学习时容易在哪些地方出错？', quick: [['概念混淆', 55], ['细节遗漏', 60], ['逻辑推理', 70], ['代码语法', 65]] },
]

const messages = reactive([])
const collected = reactive({})
const stepIndex = ref(0)
const quickReplies = ref([])
const input = ref('')

function pushMsg(role, text, agent) {
  messages.push({ role, text, agent })
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}

function botSay(text) {
  pushMsg('bot', text, '学情分析师')
  quickReplies.value = stepIndex.value < SCRIPT.length ? SCRIPT[stepIndex.value].quick : []
}

function answer(q) {
  pushMsg('user', q[0])
  collected[SCRIPT[stepIndex.value].dim] = q[0]
  collected[SCRIPT[stepIndex.value].dim + '_score'] = q[1]
  stepIndex.value++
  if (stepIndex.value < SCRIPT.length) {
    setTimeout(() => botSay(SCRIPT[stepIndex.value].ask), 400)
  } else {
    quickReplies.value = []
    setTimeout(() => { pushMsg('bot', '画像特征已抽取完成，正在为你生成专属学习画像…', '学情分析师'); setTimeout(() => finish(false), 800) }, 400)
  }
}

function submit() {
  const v = input.value.trim()
  if (!v || stepIndex.value >= SCRIPT.length) return
  input.value = ''
  pushMsg('user', v)
  collected[SCRIPT[stepIndex.value].dim] = v
  collected[SCRIPT[stepIndex.value].dim + '_score'] = 50
  stepIndex.value++
  if (stepIndex.value < SCRIPT.length) setTimeout(() => botSay(SCRIPT[stepIndex.value].ask), 400)
  else { quickReplies.value = []; setTimeout(() => finish(false), 600) }
}

function finish(skip) {
  const profile = {}
  DIMS.forEach((d) => {
    profile[d.key] = skip
      ? { text: '待完善', score: 50 }
      : { text: collected[d.key] || '待补充', score: collected[d.key + '_score'] ?? 50 }
  })
  profile.updatedAt = new Date().toLocaleString('zh-CN')
  localStorage.setItem('sl_profile_' + userStore.user.account, JSON.stringify(profile))
  // 学习路径（后续模块后端化）
  localStorage.setItem('sl_path_' + userStore.user.account, JSON.stringify({ steps: [], done: [] }))
  router.push('/dashboard')
}

botSay(SCRIPT[0].ask)
</script>

<style scoped>
.onboarding { display: flex; flex-direction: column; height: 100vh; background: #f7f6ef; }
.onb-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 28px; background: #fff; border-bottom: 1px solid #e5e5e5; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand-logo { width: 40px; height: 40px; border-radius: 12px; background: #2908ff; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 21px; }
.brand-name { font-size: 20px; font-weight: 800; font-family: 'Bitter', serif; }
.header-right { display: flex; align-items: center; gap: 12px; }
.agent-pill { font-size: 12px; font-weight: 700; color: #1f06d6; background: #bcf887; padding: 6px 14px; border-radius: 999px; }
.skip-btn { border-radius: 999px; }
.onb-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; max-width: 860px; width: 100%; margin: 0 auto; padding: 20px; }
.chat-box { flex: 1; overflow-y: auto; padding: 8px 4px 16px; display: flex; flex-direction: column; gap: 14px; }
.msg { max-width: 76%; display: flex; flex-direction: column; gap: 4px; }
.msg.bot { align-self: flex-start; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.agent-tag { font-size: 11px; color: #2908ff; font-weight: 700; }
.bubble { padding: 12px 16px; border-radius: 15px; font-size: 14px; line-height: 1.65; white-space: pre-line; }
.msg.bot .bubble { background: #fff; border: 1px solid #e5e5e5; border-top-left-radius: 4px; }
.msg.user .bubble { background: #2908ff; color: #fff; border-top-right-radius: 4px; }
.input-bar { padding-top: 8px; border-top: 1px solid #e5e5e5; }
.quick-replies { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.quick-btn { border-radius: 999px; }
.input-row { display: flex; gap: 10px; }
.input-row .el-button { border-radius: 999px; }
</style>

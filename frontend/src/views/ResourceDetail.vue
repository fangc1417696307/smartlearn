<template>
  <div>
    <el-button class="back" @click="$router.push('/resources')">← 返回资源中心</el-button>
    <el-card v-if="resource" shadow="never" class="panel">
      <el-tag class="type-badge" effect="plain">{{ detail.type }}</el-tag>
      <h2 class="title">{{ resource.title }}</h2>
      <p class="desc">{{ resource.desc }}</p>

      <div v-if="detail.html" class="article" v-html="detail.html"></div>

      <div v-if="detail.mindmap" class="mindmap">
        <div class="mm-root">{{ detail.mindmap.root }}</div>
        <div class="mm-tree">
          <div v-for="b in detail.mindmap.branches" :key="b.head" class="mm-branch">
            <div class="mm-node">{{ b.head }}</div>
            <div v-for="l in b.leaves" :key="l" class="mm-leaf">{{ l }}</div>
          </div>
        </div>
      </div>

      <div v-if="detail.quiz">
        <div v-for="(q, qi) in detail.quiz" :key="qi" class="quiz-q">
          <div class="q-type">{{ q.kind === 'subjective' ? '主观题 · LLM 判分' : (q.kind === 'judge' ? '判断题 · 自动判分' : '单选题 · 自动判分') }}</div>
          <div class="q-title">{{ qi + 1 }}. {{ q.q }}</div>
          <template v-if="q.kind !== 'subjective'">
            <div v-for="(o, oi) in q.options" :key="oi" class="q-opt" :class="optClass(qi, oi)" @click="choose(qi, oi)">
              <el-radio :model-value="answers[qi]" :value="oi" @click.stop>{{ o }}</el-radio>
            </div>
          </template>
          <template v-else>
            <el-input v-model="subjective[qi]" type="textarea" :rows="3" placeholder="写下你的回答…" />
            <el-button size="small" class="sub-btn" @click="submitSubjective(qi)">提交给 LLM 判分</el-button>
            <div v-if="subjectiveResults[qi]" class="sub-result">{{ subjectiveResults[qi] }}</div>
          </template>
        </div>
        <el-button v-if="hasObjective" type="primary" class="check-btn" @click="checkQuiz">提交客观题</el-button>
        <div v-if="scoreText" class="score">{{ scoreText }}</div>
      </div>

      <div v-if="detail.reading">
        <div v-for="x in detail.reading" :key="x.t" class="read-item">
          <div class="read-title">{{ x.t }}</div>
          <div class="read-src">{{ x.s }}</div>
          <div class="read-desc">{{ x.d }}</div>
        </div>
      </div>

      <div v-if="detail.code">
        <pre class="code-block"><code>{{ detail.code.source }}</code></pre>
        <div class="callout">📌 {{ detail.code.note }}</div>
      </div>

      <div v-if="detail.videos">
        <div v-for="v in detail.videos" :key="v.t" class="video-item">
          <div class="v-icon">🎬</div>
          <div class="v-info">
            <div class="v-title">{{ v.t }}</div>
            <div class="v-up">UP 主：{{ v.up }} · {{ v.dur }}</div>
          </div>
          <a :href="v.url" target="_blank" rel="noopener"><el-button type="primary" size="small" class="v-btn">前往观看</el-button></a>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { RESOURCES, RESOURCE_DETAILS } from '../data/resources'

const route = useRoute()
const resource = computed(() => RESOURCES.find((r) => r.id === route.params.id))
const detail = computed(() => RESOURCE_DETAILS[route.params.id] || {})

const answers = reactive({})
const subjective = reactive({})
const subjectiveResults = reactive({})
const scoreText = ref('')

const hasObjective = computed(() => detail.value.quiz?.some((q) => q.kind !== 'subjective'))

function choose(qi, oi) { answers[qi] = oi }
function optClass(qi, oi) {
  if (answers[qi] === undefined) return ''
  if (detail.value.quiz[qi].answer === oi) return 'correct'
  if (answers[qi] === oi) return 'wrong'
  return ''
}

function checkQuiz() {
  let correct = 0, total = 0
  detail.value.quiz.forEach((q, qi) => {
    if (q.kind === 'subjective') return
    total++
    if (answers[qi] === q.answer) correct++
  })
  const score = total ? Math.round((correct / total) * 100) : 0
  scoreText.value = `客观题得分：${correct}/${total}（${score} 分）`
}

function submitSubjective(qi) {
  if (!subjective[qi]) return
  subjectiveResults[qi] = '评估分析师 · LLM 判分中…'
  setTimeout(() => {
    subjectiveResults[qi] = detail.value.quiz[qi].ref || '已完成作答'
  }, 1000)
}
</script>

<style scoped>
.back { margin-bottom: 16px; border-radius: 999px; }
.panel { border-radius: 20px; }
.type-badge { margin-bottom: 14px; border-radius: 999px; color: #1f06d6; border-color: #bcf887; background: #bcf887; }
.title { font-size: 24px; font-weight: 800; margin-bottom: 8px; font-family: 'Bitter', serif; }
.desc { color: #737373; font-size: 13px; margin-bottom: 20px; }
.article h4 { margin: 18px 0 8px; font-size: 15px; }
.article p, .article li { font-size: 14px; line-height: 1.8; color: #404040; }
.article ul { padding-left: 20px; }
.article .callout, .callout { background: #bcf887; border-left: 4px solid #1f06d6; padding: 12px 14px; border-radius: 10px; font-size: 13px; margin: 14px 0; color: #1e2b0f; }
.mindmap { display: flex; flex-direction: column; align-items: center; padding: 18px 0; }
.mm-root { background: #2908ff; color: #fff; padding: 13px 26px; border-radius: 999px; font-weight: 800; }
.mm-tree { display: flex; gap: 30px; margin-top: 26px; flex-wrap: wrap; justify-content: center; }
.mm-branch { display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 120px; }
.mm-node { border: 1.5px solid #2908ff; color: #2908ff; padding: 9px 15px; border-radius: 999px; font-size: 13px; font-weight: 700; }
.mm-leaf { font-size: 12px; color: #737373; background: #eeecde; padding: 5px 12px; border-radius: 999px; }
.quiz-q { border: 1px solid #e5e5e5; border-radius: 16px; padding: 18px; margin-bottom: 14px; }
.q-type { font-size: 11px; color: #2908ff; font-weight: 800; margin-bottom: 6px; }
.q-title { font-size: 14px; font-weight: 700; margin-bottom: 12px; line-height: 1.6; }
.q-opt { padding: 9px 12px; border: 1.5px solid #e5e5e5; border-radius: 999px; margin-bottom: 8px; cursor: pointer; }
.q-opt.correct { background: #dcfce7; border-color: #22c55e; }
.q-opt.wrong { background: #fee2e2; border-color: #ef4444; }
.sub-btn { margin-top: 10px; border-radius: 999px; }
.sub-result { margin-top: 10px; background: #dcfce7; border-radius: 10px; padding: 12px; font-size: 13px; line-height: 1.7; }
.check-btn { border-radius: 999px; margin-top: 6px; }
.score { font-weight: 800; margin-top: 14px; }
.read-item { border: 1px solid #e5e5e5; border-radius: 14px; padding: 14px; margin-bottom: 12px; }
.read-title { font-weight: 700; font-size: 14px; }
.read-src { color: #737373; font-size: 12px; margin: 4px 0 6px; }
.read-desc { font-size: 13px; line-height: 1.7; color: #404040; }
.code-block { background: #191919; color: #e7e7e7; border-radius: 16px; padding: 20px; overflow-x: auto; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 13px; line-height: 1.7; }
.video-item { display: flex; align-items: center; gap: 14px; border: 1px solid #e5e5e5; border-radius: 14px; padding: 14px; margin-bottom: 12px; }
.v-icon { font-size: 26px; }
.v-info { flex: 1; }
.v-title { font-weight: 700; font-size: 14px; }
.v-up { color: #737373; font-size: 12px; margin-top: 3px; }
.v-btn { border-radius: 999px; }
</style>

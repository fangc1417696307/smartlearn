<template>
  <div class="login-page">
    <div class="login-hero">
      <div class="brand">
        <div class="brand-logo">S</div>
        <div>
          <div class="brand-name">SmartLearn</div>
          <div class="brand-tag">个性化学习多智能体系统</div>
        </div>
      </div>
      <div class="kicker">Multi-Agent Learning</div>
      <h1 class="headline">让学习资料，<br /><span class="grad">长成你的形状</span></h1>
      <p class="sub">SmartLearn 用多智能体协作，把你的专业、目标与知识短板，变成专属的学习资源与路径。</p>
      <ul class="features">
        <li><span class="dot"></span>对话式构建你的学习画像</li>
        <li><span class="dot"></span>多智能体协同生成专属资源</li>
        <li><span class="dot"></span>个性化学习路径与精准推送</li>
      </ul>
      <AgentOrbit class="hero-orbit" :size="232" />
    </div>

    <div class="login-card">
      <el-tabs v-model="activeTab" class="login-tabs" stretch>
        <el-tab-pane label="密码登录" name="login">
          <el-form @submit.prevent>
            <el-form-item>
              <el-input v-model="login.account" placeholder="学号 / 邮箱" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="login.password" type="password" placeholder="密码" size="large" show-password />
            </el-form-item>
            <el-form-item>
              <div class="captcha-box">
                <div class="captcha-question" @click="refreshCaptcha('login')">{{ loginCaptcha.question || '点击获取验证码' }}</div>
                <el-button @click="refreshCaptcha('login')" class="refresh-btn">↻ 刷新</el-button>
              </div>
            </el-form-item>
            <el-form-item>
              <el-input v-model="login.captcha" placeholder="请输入上方算式结果" size="large" />
            </el-form-item>
            <el-button type="primary" size="large" class="submit-btn" @click="onLogin" :loading="loading">登 录</el-button>
            <div class="hint">还没有账号？<a @click="activeTab = 'register'">立即注册</a></div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="验证码登录" name="code">
          <el-form @submit.prevent>
            <el-form-item>
              <el-input v-model="codeLogin.email" placeholder="请输入已绑定的邮箱" size="large" />
            </el-form-item>
            <el-form-item>
              <div class="code-row">
                <el-input v-model="codeLogin.code" placeholder="6 位验证码" size="large" maxlength="6" />
                <el-button size="large" @click="sendCode" :disabled="countdown > 0">{{ countdown > 0 ? countdown + 's 后重发' : '发送验证码' }}</el-button>
              </div>
            </el-form-item>
            <el-button type="primary" size="large" class="submit-btn" @click="onCodeLogin" :loading="loading">验证码登录</el-button>
            <div class="hint">需先绑定邮箱。<a @click="activeTab = 'login'">返回密码登录</a></div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form @submit.prevent>
            <el-form-item>
              <el-radio-group v-model="reg.role" size="large" class="role-group">
                <el-radio-button label="student">我是学生</el-radio-button>
                <el-radio-button label="teacher">我是老师</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-select v-model="reg.major" placeholder="专业" size="large" style="width: 100%">
                <el-option v-for="m in majors" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
            <el-form-item><el-input v-model="reg.account" placeholder="学号" size="large" /></el-form-item>
            <el-form-item><el-input v-model="reg.nickname" placeholder="昵称" size="large" /></el-form-item>
            <el-form-item><el-input v-model="reg.password" type="password" placeholder="密码（至少 6 位）" size="large" show-password /></el-form-item>
            <el-form-item><el-input v-model="reg.password2" type="password" placeholder="确认密码（再次输入）" size="large" show-password /></el-form-item>
            <el-form-item>
              <div class="code-row">
                <el-input v-model="reg.email" placeholder="邮箱（选填，绑定后可验证码登录）" size="large" />
                <el-button size="large" @click="sendRegCode" :disabled="regCountdown > 0">{{ regCountdown > 0 ? regCountdown + 's 后重发' : '获取验证码' }}</el-button>
              </div>
            </el-form-item>
            <el-form-item v-if="reg.email"><el-input v-model="reg.emailCode" placeholder="请输入邮箱验证码" size="large" maxlength="6" /></el-form-item>
            <el-form-item>
              <div class="captcha-box">
                <div class="captcha-question" @click="refreshCaptcha('reg')">{{ regCaptcha.question || '点击获取验证码' }}</div>
                <el-button @click="refreshCaptcha('reg')" class="refresh-btn">↻ 刷新</el-button>
              </div>
            </el-form-item>
            <el-form-item><el-input v-model="reg.captcha" placeholder="请输入上方算式结果" size="large" /></el-form-item>
            <el-button type="primary" size="large" class="submit-btn" @click="onRegister" :loading="loading">注册并开始</el-button>
            <div class="hint">已有账号？<a @click="activeTab = 'login'">去登录</a></div>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="pwdDialog" title="请修改初始密码" width="400px" :close-on-click-modal="false" :show-close="false">
      <p class="dialog-tip">为保障账号安全，首次登录需设置新密码。</p>
      <el-input v-model="pwdNew" type="password" placeholder="新密码（至少 6 位）" show-password />
      <el-input v-model="pwdNew2" type="password" placeholder="确认新密码" show-password style="margin-top: 10px" />
      <p v-if="pwdErr" class="pwd-err">{{ pwdErr }}</p>
      <template #footer>
        <el-button type="primary" class="submit-btn" @click="onChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useUserStore } from '../store/user'
import { resolveHome } from '../router/rules'
import AgentOrbit from '../components/AgentOrbit.vue'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const majors = ['计算机科学与技术', '软件工程', '网络工程', '人工智能', '数据科学与大数据技术', '数学与应用数学', '英语', '经济与管理']

const login = reactive({ account: '', password: '', captcha: '' })
const codeLogin = reactive({ email: '', code: '' })
const reg = reactive({ major: '', account: '', nickname: '', password: '', password2: '', email: '', emailCode: '', captcha: '', role: 'student' })

const loginCaptcha = reactive({ id: '', question: '' })
const regCaptcha = reactive({ id: '', question: '' })
const countdown = ref(0)
const regCountdown = ref(0)

const pwdDialog = ref(false)
const pwdNew = ref('')
const pwdNew2 = ref('')
const pwdErr = ref('')
let pwdLoginPassword = ''

async function refreshCaptcha(prefix) {
  try {
    const data = await api.get('/auth/captcha')
    if (prefix === 'login') { loginCaptcha.id = data.captcha_id; loginCaptcha.question = data.question; }
    else { regCaptcha.id = data.captcha_id; regCaptcha.question = data.question; }
  } catch (e) { /* 已全局提示 */ }
}

function enterApp(data, loginPassword) {
  userStore.setAuth(data.access_token, data.user, data.permissions)
  if (data.user.must_change_password) {
    pwdLoginPassword = loginPassword || ''
    pwdNew.value = ''
    pwdErr.value = ''
    pwdDialog.value = true
  } else {
    afterLogin()
  }
}

function afterLogin() {
  // 超级管理员进数据看板
  if (userStore.isAdmin) { router.push('/stats'); return }
  const roles = (userStore.user?.roles || []).map((r) => r.code)
  // 只有学生走「画像构建 → 学习空间」流程
  if (roles.includes('student')) {
    const profile = JSON.parse(localStorage.getItem('sl_profile_' + userStore.user.account) || 'null')
    router.push(profile ? '/dashboard' : '/onboarding')
    return
  }
  // 老师及其他角色按权限进入对应工作台
  const home = resolveHome(userStore.permissions, roles)
  router.push(home ? { name: home } : '/account')
}

async function onLogin() {
  if (!login.account || !login.password) return ElMessage.warning('请填写账号和密码')
  if (!login.captcha) return ElMessage.warning('请填写验证码')
  loading.value = true
  try {
    const data = await api.post('/auth/login', {
      account: login.account, password: login.password,
      captcha_id: loginCaptcha.id, captcha_answer: login.captcha,
    })
    enterApp(data, login.password)
  } catch (e) {
    refreshCaptcha('login')
  } finally { loading.value = false }
}

async function onRegister() {
  if (!reg.account || !reg.password) return ElMessage.warning('请填写学号和密码')
  if (reg.password.length < 6) return ElMessage.warning('密码至少 6 位')
  if (reg.password !== reg.password2) return ElMessage.warning('两次输入的密码不一致')
  if (reg.email && !reg.emailCode) return ElMessage.warning('请填写邮箱验证码')
  if (!reg.captcha) return ElMessage.warning('请填写验证码')
  loading.value = true
  try {
    const data = await api.post('/auth/register', {
      account: reg.account, password: reg.password, nickname: reg.nickname || '同学', major: reg.major, role: reg.role,
      email: reg.email || null, email_code: reg.emailCode || null,
      captcha_id: regCaptcha.id, captcha_answer: reg.captcha,
    })
    if (data.pending) {
      ElMessage.success('注册成功，请等待管理员审核后登录')
      activeTab.value = 'login'
      return
    }
    enterApp(data)
  } catch (e) {
    refreshCaptcha('reg')
  } finally { loading.value = false }
}

async function sendCode() {
  if (!codeLogin.email) return ElMessage.warning('请输入邮箱')
  try {
    await api.post('/auth/send-code', { email: codeLogin.email })
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) { /* 已全局提示 */ }
}

async function sendRegCode() {
  if (!reg.email) return ElMessage.warning('请先输入邮箱')
  try {
    await api.post('/auth/send-code', { email: reg.email })
    ElMessage.success('验证码已发送')
    regCountdown.value = 60
    const timer = setInterval(() => {
      regCountdown.value--
      if (regCountdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) { /* 已全局提示 */ }
}

async function onCodeLogin() {
  if (!codeLogin.email || !codeLogin.code) return ElMessage.warning('请输入邮箱和验证码')
  loading.value = true
  try {
    const data = await api.post('/auth/code-login', { email: codeLogin.email, code: codeLogin.code })
    enterApp(data)
  } catch (e) { /* 已全局提示 */ } finally { loading.value = false }
}

async function onChangePwd() {
  if (pwdNew.value.length < 6) { pwdErr.value = '新密码至少 6 位'; return }
  if (pwdNew.value !== pwdNew2.value) { pwdErr.value = '两次输入的密码不一致'; return }
  try {
    await api.post('/auth/change-password', { old_password: pwdLoginPassword, new_password: pwdNew.value })
    const u = { ...userStore.user, must_change_password: false }
    localStorage.setItem('sl_user', JSON.stringify(u))
    userStore.user = u
    pwdDialog.value = false
    ElMessage.success('密码修改成功')
    afterLogin()
  } catch (e) { pwdErr.value = '修改失败，请重试' }
}

onMounted(() => {
  refreshCaptcha('login')
  refreshCaptcha('reg')
})
</script>

<style scoped>
.login-page { display: grid; grid-template-columns: 1fr 1fr; min-height: 100vh; max-width: 1320px; margin: 0 auto; background: #f7f6ef; position: relative; overflow: hidden; }
.login-page::before { content: ''; position: fixed; width: 520px; height: 520px; border-radius: 50%; background: rgba(188, 248, 135, 0.35); top: -180px; right: -120px; pointer-events: none; z-index: 0; }
.login-page::after { content: ''; position: fixed; width: 420px; height: 420px; border-radius: 50%; background: rgba(41, 8, 255, 0.06); bottom: -160px; left: -120px; pointer-events: none; z-index: 0; }
.login-hero { padding: 56px 32px 56px 72px; display: flex; flex-direction: column; justify-content: center; position: relative; z-index: 1; }
.hero-orbit { margin-top: 30px; }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 40px; }
.brand-logo { width: 44px; height: 44px; border-radius: 14px; background: #2908ff; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 23px; }
.brand-name { font-size: 22px; font-weight: 800; font-family: 'Bitter', serif; }
.brand-tag { font-size: 12px; color: #737373; }
.kicker { display: inline-flex; align-self: flex-start; font-size: 13px; font-weight: 800; letter-spacing: 1px; color: #1f06d6; background: #bcf887; padding: 7px 15px; border-radius: 999px; margin-bottom: 20px; }
.headline { font-size: 43px; line-height: 1.18; font-weight: 800; margin-bottom: 16px; letter-spacing: -0.5px; font-family: 'Bitter', serif; }
.headline .grad { color: #2908ff; }
.sub { font-size: 15px; color: #737373; line-height: 1.7; max-width: 440px; margin-bottom: 32px; }
.features { list-style: none; display: flex; flex-direction: column; gap: 14px; font-size: 15px; }
.features li { display: flex; align-items: center; gap: 12px; }
.features .dot { width: 9px; height: 9px; border-radius: 50%; background: #2908ff; flex-shrink: 0; }

.login-card { display: flex; flex-direction: column; justify-content: center; padding: 56px 72px 56px 32px; max-width: 500px; width: 100%; margin: 0 auto; position: relative; z-index: 1; }
.login-card :deep(.el-tabs) { background: #fff; border: 1px solid #e5e5e5; border-radius: 24px; padding: 28px 30px; box-shadow: 0 10px 30px rgba(25, 25, 25, 0.07); }
.login-card :deep(.el-tabs__nav-wrap::after) { display: none; }
.login-card :deep(.el-tabs__item) { font-weight: 700; font-size: 15px; }
.captcha-box { display: flex; align-items: center; gap: 10px; width: 100%; }
.captcha-question { flex: 1; background: #eeecde; padding: 10px 16px; border-radius: 12px; font-size: 17px; font-weight: 800; font-family: 'Bitter', serif; letter-spacing: 1px; color: #2908ff; cursor: pointer; user-select: none; text-align: center; }
.refresh-btn { border-radius: 12px; }
.code-row { display: flex; gap: 8px; width: 100%; }
.submit-btn { width: 100%; border-radius: 999px; }
.hint { text-align: center; font-size: 13px; color: #737373; margin-top: 14px; }
.hint a { color: #2908ff; font-weight: 700; cursor: pointer; }
.dialog-tip { color: #737373; font-size: 13px; margin-bottom: 12px; }
.pwd-err { color: #ef4444; font-size: 12px; margin-top: 8px; }
@media (max-width: 900px) { .login-page { grid-template-columns: 1fr; } .login-hero { display: none; } }
</style>

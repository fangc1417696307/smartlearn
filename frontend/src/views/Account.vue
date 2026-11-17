<template>
  <div>
    <el-card shadow="never" class="panel">
      <template #header><span class="head">👤 账号信息</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="学号">{{ user?.account }}</el-descriptions-item>
        <el-descriptions-item label="昵称">{{ user?.nickname }}</el-descriptions-item>
        <el-descriptions-item label="专业">{{ user?.major || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">
          <span :class="{ unbound: !user?.email }">{{ user?.email || '未绑定' }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="panel">
      <template #header>
        <div class="card-head">
          <span class="head">📧 绑定邮箱</span>
          <el-tag v-if="user?.email" type="success" round size="small">已绑定</el-tag>
          <el-tag v-else type="info" round size="small">未绑定</el-tag>
        </div>
      </template>

      <!-- 已绑定：展示当前邮箱，提供更换 / 解绑 -->
      <div v-if="user?.email && !editing" class="bound-box">
        <div class="bound-info">
          <div class="bound-label">当前邮箱</div>
          <div class="bound-email">{{ user.email }}</div>
        </div>
        <div class="bound-actions">
          <el-button size="large" @click="startRebind">更换邮箱</el-button>
          <el-button size="large" type="danger" plain @click="unbind">解绑</el-button>
        </div>
      </div>
      <p v-if="user?.email && !editing" class="tip">
        该邮箱可用于「邮箱验证码登录」；解绑后将无法使用该方式登录。
      </p>

      <!-- 未绑定，或正在更换 -->
      <template v-else>
        <p class="tip">
          {{ user?.email ? `绑定新邮箱后，原邮箱 ${user.email} 将自动解绑。` : '绑定邮箱后可用「邮箱验证码登录」，忘记密码时也更方便找回。' }}
        </p>
        <div class="row">
          <el-input v-model="bindEmail" placeholder="请输入要绑定的邮箱" size="large" />
          <el-button size="large" @click="sendCode" :disabled="countdown > 0">
            {{ countdown > 0 ? countdown + 's 后重发' : '发送验证码' }}
          </el-button>
        </div>
        <div class="row">
          <el-input v-model="bindCode" placeholder="请输入邮箱验证码" size="large" maxlength="6" />
          <el-button type="primary" size="large" @click="bind">{{ user?.email ? '确认更换' : '绑定邮箱' }}</el-button>
        </div>
        <el-button v-if="editing" text class="cancel-btn" @click="cancelRebind">取消更换</el-button>
      </template>
    </el-card>

    <el-card shadow="never" class="panel">
      <template #header><span class="head">🔒 修改密码</span></template>
      <el-input v-model="oldPwd" type="password" placeholder="原密码" size="large" show-password class="stack" />
      <el-input v-model="newPwd" type="password" placeholder="新密码（至少 6 位）" size="large" show-password class="stack" />
      <el-input v-model="newPwd2" type="password" placeholder="确认新密码" size="large" show-password class="stack" />
      <el-button type="primary" size="large" class="pwd-btn" @click="changePwd">修改密码</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
// 用 computed 跟随 store 更新（MainLayout 会在进入页面时刷新用户信息）
const user = computed(() => userStore.user)

const editing = ref(false)
const bindEmail = ref('')
const bindCode = ref('')
const countdown = ref(0)
const oldPwd = ref('')
const newPwd = ref('')
const newPwd2 = ref('')

function startRebind() {
  editing.value = true
  bindEmail.value = ''
  bindCode.value = ''
}

function cancelRebind() {
  editing.value = false
  bindEmail.value = ''
  bindCode.value = ''
}

/** 绑定/解绑后同步最新用户信息 */
async function refreshMe() {
  const refreshed = await api.get('/auth/me')
  userStore.setAuth(userStore.token, refreshed)
}

async function sendCode() {
  if (!bindEmail.value) return ElMessage.warning('请输入邮箱')
  try {
    await api.post('/auth/send-code', { email: bindEmail.value })
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const t = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(t)
    }, 1000)
  } catch (e) { /* 已全局提示 */ }
}

async function bind() {
  if (!bindEmail.value) return ElMessage.warning('请输入邮箱')
  if (!bindCode.value) return ElMessage.warning('请输入验证码')
  const isRebind = !!user.value?.email
  try {
    await api.post('/auth/bind-email', { email: bindEmail.value, code: bindCode.value })
    await refreshMe()
    ElMessage.success(isRebind ? '邮箱更换成功' : '邮箱绑定成功')
    editing.value = false
    resetBindForm()
  } catch (e) { /* 已全局提示 */ }
}

async function unbind() {
  try {
    await ElMessageBox.confirm(
      `解绑后「${user.value?.email}」将不能再用于验证码登录，确认解绑？`,
      '解绑邮箱',
      { type: 'warning', confirmButtonText: '确认解绑', cancelButtonText: '取消' },
    )
    await api.post('/auth/unbind-email')
    await refreshMe()
    ElMessage.success('邮箱已解绑')
    resetBindForm()
  } catch (e) { /* 取消或失败 */ }
}

function resetBindForm() {
  bindEmail.value = ''
  bindCode.value = ''
}

async function changePwd() {
  if (newPwd.value.length < 6) return ElMessage.warning('新密码至少 6 位')
  if (newPwd.value !== newPwd2.value) return ElMessage.warning('两次输入的密码不一致')
  try {
    await api.post('/auth/change-password', { old_password: oldPwd.value, new_password: newPwd.value })
    ElMessage.success('密码修改成功')
    oldPwd.value = newPwd.value = newPwd2.value = ''
  } catch (e) { /* 已全局提示 */ }
}
</script>

<style scoped>
.panel { border-radius: 20px; }
.card-head { display: flex; align-items: center; gap: 10px; }
.head { font-weight: 700; }
.tip { color: #737373; font-size: 13px; margin-bottom: 14px; }
.row { display: flex; gap: 10px; margin-bottom: 12px; }
.row .el-button { border-radius: 999px; white-space: nowrap; }
.stack { margin-bottom: 12px; }
.pwd-btn { border-radius: 999px; }
.unbound { color: #f59e0b; }

.bound-box {
  display: flex; align-items: center; justify-content: space-between;
  gap: 20px; padding: 18px 22px; margin-bottom: 12px;
  background: #f7f6ef; border-radius: 16px;
}
.bound-label { font-size: 12px; color: #737373; margin-bottom: 4px; }
.bound-email { font-size: 17px; font-weight: 700; color: #191919; }
.bound-actions { display: flex; gap: 10px; flex-shrink: 0; }
.bound-actions .el-button { border-radius: 999px; }
.cancel-btn { border-radius: 999px; color: #737373; }
</style>

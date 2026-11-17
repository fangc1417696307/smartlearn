<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="head"><span>👥 用户管理</span><el-button type="primary" @click="openAdd">+ 新增用户</el-button></div>
    </template>

    <el-table :data="users" border stripe>
      <el-table-column prop="account" label="账号" width="120" />
      <el-table-column prop="nickname" label="昵称" width="120" />
      <el-table-column label="邮箱"><template #default="{ row }">{{ row.email || '-' }}</template></el-table-column>
      <el-table-column label="专业" width="140"><template #default="{ row }">{{ row.major || '-' }}</template></el-table-column>
      <el-table-column label="角色"><template #default="{ row }"><el-tag v-for="r in row.roles" :key="r.id" class="role-tag">{{ r.name }}</el-tag></template></el-table-column>
      <el-table-column label="额外权限">
        <template #default="{ row }">
          <el-tag v-for="p in row.direct_permissions" :key="p.id" type="warning" class="role-tag">{{ p.name }}</el-tag>
          <span v-if="!row.direct_permissions || !row.direct_permissions.length" class="none">-</span>
        </template>
      </el-table-column>
      <el-table-column label="审核状态" width="100">
        <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button size="small" type="success" @click="approve(row)">通过</el-button>
            <el-button size="small" type="danger" @click="reject(row)">拒绝</el-button>
          </template>
          <template v-else>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="del(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="form.id ? '编辑用户' : '新增用户'" width="480px">
      <el-form label-width="70px">
        <el-form-item label="学号"><el-input v-model="form.account" :disabled="!!form.id" /></el-form-item>
        <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" placeholder="选填，绑定后可验证码登录" /></el-form-item>
        <el-form-item label="专业"><el-input v-model="form.major" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" :placeholder="form.id ? '留空则不修改' : '必填'" show-password /></el-form-item>
        <el-form-item label="角色">
          <el-checkbox-group v-model="form.role_ids">
            <el-checkbox v-for="r in roles" :key="r.id" :label="r.id">{{ r.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="额外权限">
          <el-select v-model="form.permission_ids" multiple collapse-tags placeholder="可选：给该用户单独补权限" style="width: 100%">
            <el-option v-for="p in permissions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <div class="perm-tip">通常通过角色授权；此处仅用于额外补充（最终权限 = 角色权限 ∪ 额外权限）</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
const users = ref([])
const roles = ref([])
const permissions = ref([])
const dialog = ref(false)
const form = reactive({ id: null, account: '', nickname: '', email: '', major: '', password: '', role_ids: [], permission_ids: [] })

async function load() {
  users.value = await api.get('/users/')
  roles.value = await api.get('/roles/')
  permissions.value = await api.get('/users/permissions')
}

function openAdd() {
  Object.assign(form, { id: null, account: '', nickname: '', email: '', major: '', password: '', role_ids: [], permission_ids: [] })
  dialog.value = true
}

function openEdit(row) {
  Object.assign(form, { id: row.id, account: row.account, nickname: row.nickname, email: row.email || '', major: row.major || '', password: '', role_ids: (row.roles || []).map((r) => r.id), permission_ids: (row.direct_permissions || []).map((p) => p.id) })
  dialog.value = true
}

async function save() {
  try {
    if (form.id) {
      const body = { nickname: form.nickname || '同学', email: form.email || null, major: form.major, role_ids: form.role_ids, permission_ids: form.permission_ids }
      if (form.password) body.password = form.password
      await api.put('/users/' + form.id, body)
    } else {
      if (!form.account || !form.password) return ElMessage.warning('新增用户需填写学号和密码')
      await api.post('/users/', { account: form.account, password: form.password, nickname: form.nickname || '同学', email: form.email || null, major: form.major, role_ids: form.role_ids, permission_ids: form.permission_ids })
    }
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) { /* 已全局提示 */ }
}

async function del(row) {
  if (row.id === userStore.user?.id) return ElMessage.warning('不能删除当前登录账号')
  try {
    await ElMessageBox.confirm(`确认删除用户「${row.nickname}」？`, '提示', { type: 'warning' })
    await api.delete('/users/' + row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) { /* 取消或失败 */ }
}

function statusText(s) {
  return { active: '正常', pending: '待审核', rejected: '已拒绝' }[s] || s
}
function statusType(s) {
  return { active: 'success', pending: 'warning', rejected: 'danger' }[s] || 'info'
}

async function approve(row) {
  await api.post(`/users/${row.id}/approve`)
  ElMessage.success('已通过审核')
  load()
}

async function reject(row) {
  await api.post(`/users/${row.id}/reject`)
  ElMessage.success('已拒绝')
  load()
}

onMounted(load)
</script>

<style scoped>
.panel { border-radius: 20px; }
.head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.role-tag { margin-right: 4px; border-radius: 999px; }
.none { color: #989898; }
.perm-tip { font-size: 12px; color: #989898; margin-top: 6px; line-height: 1.5; }
</style>

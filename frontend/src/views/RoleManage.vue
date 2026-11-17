<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="head"><span>🛡️ 角色管理</span><el-button type="primary" @click="openAdd">+ 新建角色</el-button></div>
    </template>

    <div class="role-list">
      <div v-for="r in roles" :key="r.id" class="role-card">
        <div class="info">
          <div class="name">{{ r.name }} <span v-if="r.is_system" class="sys">系统内置</span></div>
          <div class="code">编码：{{ r.code }}</div>
          <div class="desc">{{ r.description }}</div>
          <div class="perms"><el-tag v-for="p in r.permissions" :key="p.id" class="perm-tag">{{ p.name }}</el-tag></div>
        </div>
        <div class="actions">
          <el-button size="small" @click="openEdit(r)">编辑</el-button>
          <el-button v-if="!r.is_system" size="small" type="danger" @click="del(r)">删除</el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="dialog" :title="form.id ? '编辑角色' : '新建角色'" width="520px">
      <el-form label-width="70px">
        <el-form-item label="名称"><el-input v-model="form.name" placeholder="如：助教" /></el-form-item>
        <el-form-item label="编码"><el-input v-model="form.code" placeholder="英文，如：assistant" :disabled="!!form.id" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="form.permission_ids" class="perm-list">
            <el-checkbox v-for="p in permissions" :key="p.id" :label="p.id" border>{{ p.name }}</el-checkbox>
          </el-checkbox-group>
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

const roles = ref([])
const permissions = ref([])
const dialog = ref(false)
const form = reactive({ id: null, name: '', code: '', description: '', permission_ids: [] })

async function load() {
  roles.value = await api.get('/roles/')
}

async function loadPerms() {
  permissions.value = await api.get('/roles/permissions')
}

function openAdd() {
  Object.assign(form, { id: null, name: '', code: '', description: '', permission_ids: [] })
  dialog.value = true
}

function openEdit(r) {
  Object.assign(form, { id: r.id, name: r.name, code: r.code, description: r.description, permission_ids: (r.permissions || []).map((p) => p.id) })
  dialog.value = true
}

async function save() {
  if (!form.name || !form.code) return ElMessage.warning('请填写名称和编码')
  try {
    const body = { name: form.name, description: form.description, permission_ids: form.permission_ids }
    if (form.id) await api.put('/roles/' + form.id, body)
    else await api.post('/roles/', { ...body, code: form.code })
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) { /* 已全局提示 */ }
}

async function del(r) {
  try {
    await ElMessageBox.confirm(`确认删除角色「${r.name}」？`, '提示', { type: 'warning' })
    await api.delete('/roles/' + r.id)
    ElMessage.success('已删除')
    load()
  } catch (e) { /* 取消或失败 */ }
}

onMounted(() => { load(); loadPerms() })
</script>

<style scoped>
.panel { border-radius: 20px; }
.head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.role-list { display: flex; flex-direction: column; gap: 12px; }
.role-card { border: 1px solid #e5e5e5; border-radius: 16px; padding: 18px; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.info { flex: 1; }
.name { font-size: 15px; font-weight: 800; }
.sys { font-size: 11px; padding: 3px 10px; border-radius: 999px; background: #eeecde; color: #737373; font-weight: 700; margin-left: 6px; }
.code { font-size: 12px; color: #989898; margin: 2px 0 6px; }
.desc { font-size: 13px; color: #737373; margin-bottom: 8px; }
.perms { display: flex; flex-wrap: wrap; gap: 6px; }
.perm-tag { border-radius: 999px; }
.actions { display: flex; flex-direction: column; gap: 6px; }
.perm-list { display: flex; flex-wrap: wrap; gap: 8px; }
.perm-list .el-checkbox { border-radius: 10px; }
</style>

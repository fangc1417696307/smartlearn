<template>
  <el-card shadow="never" class="panel">
    <template #header>
      <div class="head"><span>👨‍🏫 学生管理</span><span class="muted">共 {{ students.length }} 名学生</span></div>
    </template>
    <el-table :data="students" border stripe>
      <el-table-column prop="account" label="学号" width="130" />
      <el-table-column prop="nickname" label="昵称" width="130" />
      <el-table-column label="邮箱"><template #default="{ row }">{{ row.email || '-' }}</template></el-table-column>
      <el-table-column label="专业" width="180"><template #default="{ row }">{{ row.major || '-' }}</template></el-table-column>
      <el-table-column label="状态" width="100"><template #default><el-tag type="success">正常</el-tag></template></el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button size="small" round @click="chatWith(row)">发消息</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p class="tip">💡 学生画像与学习数据由学生端维护，后续可接入后端统一展示。</p>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const students = ref([])
const router = useRouter()

onMounted(async () => {
  students.value = await api.get('/students/')
})

async function chatWith(row) {
  // 复用已有私聊会话，没有则新建，然后跳到聊天页
  const conv = await api.post('/chat/conversations', { type: 'private', peerId: row.id })
  router.push({ name: 'chat', query: { conv: conv.id } })
}
</script>

<style scoped>
.panel { border-radius: 20px; }
.head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.muted { color: #737373; font-size: 13px; font-weight: 400; }
.tip { color: #737373; font-size: 13px; margin-top: 16px; }
</style>

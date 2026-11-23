<template>
  <div class="main-layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">S</div>
        <div class="brand-name">SmartLearn</div>
      </div>
      <nav class="nav">
        <router-link v-for="item in menu" :key="item.path" :to="item.path" class="nav-item" active-class="active">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="user-chip">
          <div class="avatar">{{ (userStore.user?.nickname || '同').slice(0, 1) }}</div>
          <div>
            <div class="user-name">{{ userStore.user?.nickname || '同学' }}</div>
            <div class="user-major">{{ userStore.user?.major || '—' }}</div>
          </div>
        </div>
        <el-button class="logout-btn" @click="onLogout">退出登录</el-button>
      </div>
    </aside>

    <main class="content">
      <header class="topbar">
        <div class="topbar-title">{{ title }}</div>
        <div class="topbar-date">{{ today }}</div>
      </header>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { canAccessRoute, resolveHome } from '../router/rules'
import { usePresence } from '../composables/usePresence'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 实时在线状态：进入主界面即建立 presence 长连接，退出/关闭页面即下线
usePresence()

// 进入主界面时从后端拉取最新用户信息与权限：
// 管理员改了某人的角色/额外权限后，对方刷新页面即可生效，无需重新登录
onMounted(async () => {
  await userStore.refresh()
  // 权限被收回时，当前页面可能已无权访问，自动回到有权限的落地页
  if (!canAccessRoute(route.name, userStore.permissions)) {
    const roles = (userStore.user?.roles || []).map((r) => r.code)
    const home = resolveHome(userStore.permissions, roles)
    router.replace(home ? { name: home } : '/account')
  }
})

const menu = computed(() => {
  // 超级管理员只显示管理菜单
  if (userStore.isAdmin) {
    return [
      { path: '/stats', label: '数据大屏', icon: 'DataAnalysis' },
      { path: '/users', label: '用户管理', icon: 'UserFilled' },
      { path: '/roles', label: '角色管理', icon: 'Lock' },
      { path: '/account', label: '个人中心', icon: 'Setting' },
    ]
  }
  // 其他角色：完全按有效权限（角色权限 ∪ 直接权限）动态生成菜单
  const perms = userStore.permissions
  const items = []
  // 管理类功能
  if (perms.includes('stats.view')) items.push({ path: '/stats', label: '数据大屏', icon: 'DataAnalysis' })
  if (perms.includes('user.manage')) items.push({ path: '/users', label: '用户管理', icon: 'UserFilled' })
  if (perms.includes('role.manage')) items.push({ path: '/roles', label: '角色管理', icon: 'Lock' })
  if (perms.includes('student.view')) items.push({ path: '/students', label: '学生管理', icon: 'UserFilled' })
  // 学习类功能
  if (perms.includes('profile.manage')) items.push({ path: '/dashboard', label: '首页', icon: 'HomeFilled' })
  if (perms.includes('path.manage')) items.push({ path: '/path', label: '学习路径', icon: 'Guide' })
  if (perms.includes('resource.view')) items.push({ path: '/resources', label: '资源中心', icon: 'Collection' })
  if (perms.includes('qa.ask')) items.push({ path: '/qa', label: '答疑', icon: 'ChatDotRound' })
  if (perms.includes('chat.use')) items.push({ path: '/chat', label: '消息', icon: 'ChatLineRound' })
  if (perms.includes('assessment.view')) items.push({ path: '/assessment', label: '学习评估', icon: 'DataLine' })
  if (perms.includes('profile.manage')) items.push({ path: '/profile', label: '我的画像', icon: 'User' })
  items.push({ path: '/account', label: '个人中心', icon: 'Setting' })
  return items
})

const titles = { dashboard: '首页', path: '学习路径', resources: '资源中心', 'resource-detail': '资源详情', qa: '答疑', chat: '消息', assessment: '学习评估', profile: '我的画像', users: '用户管理', roles: '角色管理', students: '学生管理', account: '个人中心', stats: '数据大屏' }
const title = computed(() => titles[route.name] || '首页')
const today = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })

function onLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.main-layout { display: grid; grid-template-columns: 250px 1fr; min-height: 100vh; }
.sidebar { background: #fff; border-right: 1px solid #e5e5e5; padding: 22px 16px; position: sticky; top: 0; height: 100vh; display: flex; flex-direction: column; }
.brand { display: flex; align-items: center; gap: 12px; padding: 0 8px 22px; }
.brand-logo { width: 40px; height: 40px; border-radius: 12px; background: #2908ff; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 21px; }
.brand-name { font-size: 20px; font-weight: 800; font-family: 'Bitter', serif; }
.nav { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 40px; color: #737373; font-size: 14px; font-weight: 700; text-decoration: none; transition: 0.15s; }
.nav-item:hover { background: #eeecde; color: #191919; }
.nav-item.active { background: #bcf887; color: #1f06d6; }
.sidebar-footer { border-top: 1px solid #e5e5e5; padding-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.user-chip { display: flex; align-items: center; gap: 10px; padding: 0 4px; }
.avatar { width: 40px; height: 40px; border-radius: 50%; background: #2908ff; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.user-name { font-size: 14px; font-weight: 700; }
.user-major { font-size: 12px; color: #737373; }
.logout-btn { border-radius: 999px; }
.content { padding: 28px 34px; width: 100%; max-width: 1400px; margin: 0 auto; box-sizing: border-box; }
.topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.topbar-title { font-size: 26px; font-weight: 800; font-family: 'Bitter', serif; }
.topbar-date { color: #737373; font-size: 13px; }
</style>

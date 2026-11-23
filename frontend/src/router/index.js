import { createRouter, createWebHistory } from 'vue-router'
import { currentPermissions, readStoredUser } from '../utils/perms'
import { canAccessRoute, resolveHome } from './rules'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  { path: '/onboarding', name: 'onboarding', component: () => import('../views/Onboarding.vue') },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'path', name: 'path', component: () => import('../views/Path.vue') },
      { path: 'resources', name: 'resources', component: () => import('../views/Resources.vue') },
      { path: 'resources/:id', name: 'resource-detail', component: () => import('../views/ResourceDetail.vue') },
      { path: 'qa', name: 'qa', component: () => import('../views/Qa.vue') },
      { path: 'chat', name: 'chat', component: () => import('../views/Chat.vue'), meta: { perm: 'chat.use' } },
      { path: 'assessment', name: 'assessment', component: () => import('../views/Assessment.vue') },
      { path: 'profile', name: 'profile', component: () => import('../views/Profile.vue') },
      { path: 'stats', name: 'stats', component: () => import('../views/Stats.vue'), meta: { perm: 'stats.view' } },
      { path: 'users', name: 'users', component: () => import('../views/UserManage.vue'), meta: { perm: 'user.manage' } },
      { path: 'roles', name: 'roles', component: () => import('../views/RoleManage.vue'), meta: { perm: 'role.manage' } },
      { path: 'students', name: 'students', component: () => import('../views/StudentList.vue'), meta: { perm: 'student.view' } },
      { path: 'account', name: 'account', component: () => import('../views/Account.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('sl_token')
  const user = readStoredUser()
  if (!token) return to.name === 'login' ? true : { name: 'login' }

  const roles = (user?.roles || []).map((r) => r.code)
  // 有效权限 = 角色权限 ∪ 用户直接权限
  const perms = currentPermissions()
  const isAdmin = roles.includes('admin')
  const isStudent = roles.includes('student')

  // 超级管理员只进管理后台
  if (isAdmin) {
    if (to.name === 'login') return { name: 'stats' }
    return ['users', 'roles', 'account', 'stats'].includes(to.name) ? true : { name: 'stats' }
  }

  const home = resolveHome(perms, roles)

  // 无任何功能权限 → 清除登录态
  if (!home) {
    localStorage.removeItem('sl_token')
    localStorage.removeItem('sl_user')
    localStorage.removeItem('sl_perms')
    return { name: 'login' }
  }

  if (to.name === 'login') return { name: home }

  // 画像构建是学生专属流程，其他角色即使被误配了学习权限也不进入
  if (to.name === 'onboarding' && !isStudent) return { name: home }

  if (!canAccessRoute(to.name, perms)) return { name: home }
  return true
})

export default router

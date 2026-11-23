/**
 * 路由权限规则（router 与 MainLayout 共用，避免循环依赖）
 */

// 各路由所需权限
export const ROUTE_PERM = {
  users: 'user.manage',
  roles: 'role.manage',
  students: 'student.view',
  stats: 'stats.view',
  profile: 'profile.manage',
  path: 'path.manage',
  resources: 'resource.view',
  'resource-detail': 'resource.view',
  qa: 'qa.ask',
  chat: 'chat.use',
  assessment: 'assessment.view',
  onboarding: 'profile.manage',
}

// 学习区路由：只要有任一学习权限即可访问（首页不单独要求某一权限）
export const LEARN_ROUTES = ['dashboard', 'path', 'resources', 'resource-detail', 'qa', 'assessment', 'profile', 'onboarding']

// 学习类权限集合
export const LEARN_PERMS = ['profile.manage', 'resource.view', 'path.manage', 'qa.ask', 'assessment.view']

/** 计算用户默认落地页（路由 name），无任何权限时返回 null */
export function resolveHome(perms = [], roles = []) {
  if (roles.includes('admin')) return 'stats'
  if (LEARN_PERMS.some((p) => perms.includes(p))) return 'dashboard'
  if (perms.includes('stats.view')) return 'stats'
  if (perms.includes('user.manage')) return 'users'
  if (perms.includes('student.view')) return 'students'
  if (perms.includes('role.manage')) return 'roles'
  return null
}

/** 判断某路由是否可访问 */
export function canAccessRoute(name, perms = []) {
  const need = ROUTE_PERM[name]
  if (need && !perms.includes(need)) return false
  if (LEARN_ROUTES.includes(name) && !LEARN_PERMS.some((p) => perms.includes(p))) return false
  return true
}

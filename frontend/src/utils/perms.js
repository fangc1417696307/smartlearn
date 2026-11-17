/**
 * 权限计算工具
 *
 * 用户的有效权限 = 所属角色带来的权限 ∪ 用户被单独授予的权限
 * 前端所有菜单、路由、跳转都必须以此为准，不能只看角色 code。
 */

/** 从用户对象计算有效权限（角色权限 + 直接权限） */
export function extractPermissions(user) {
  if (!user) return []
  const set = new Set()
  for (const role of user.roles || []) {
    for (const p of role.permissions || []) set.add(p.code)
  }
  for (const p of user.direct_permissions || []) set.add(p.code)
  return Array.from(set)
}

/** 读取本地缓存的用户对象 */
export function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('sl_user') || 'null')
  } catch {
    return null
  }
}

/** 读取本地缓存的权限（登录时后端下发的并集结果） */
export function readStoredPermissions() {
  try {
    const raw = localStorage.getItem('sl_perms')
    if (raw) {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr) && arr.length) return arr
    }
  } catch {
    /* 缓存损坏则回退计算 */
  }
  return null
}

/** 当前用户的有效权限：优先用缓存，缺失则从用户对象现算 */
export function currentPermissions() {
  return readStoredPermissions() || extractPermissions(readStoredUser())
}

/** 是否拥有指定权限 */
export function hasPermission(code, perms) {
  return (perms || currentPermissions()).includes(code)
}

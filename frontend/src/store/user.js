import { defineStore } from 'pinia'
import api from '../api'
import { extractPermissions, readStoredUser, readStoredPermissions } from '../utils/perms'

const storedUser = readStoredUser()

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('sl_token') || '',
    user: storedUser,
    // 有效权限 = 角色权限 ∪ 用户直接权限（登录时由后端下发，本地缓存以防刷新丢失）
    permissions: readStoredPermissions() || extractPermissions(storedUser),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    hasPerm: (s) => (code) => s.permissions.includes(code),
    isAdmin: (s) => (s.user?.roles || []).some((r) => r.code === 'admin'),
  },
  actions: {
    /** 登录成功写入登录态；permissions 为后端返回的并集，缺省时前端自行合并 */
    setAuth(token, user, permissions) {
      this.token = token
      this.user = user
      this.permissions = Array.isArray(permissions) && permissions.length
        ? permissions
        : extractPermissions(user)
      localStorage.setItem('sl_token', token)
      localStorage.setItem('sl_user', JSON.stringify(user))
      localStorage.setItem('sl_perms', JSON.stringify(this.permissions))
    },

    /** 重新拉取当前用户（权限被管理员改动后，刷新页面即可生效，无需重新登录） */
    async refresh() {
      if (!this.token) return
      try {
        const user = await api.get('/auth/me')
        this.user = user
        this.permissions = extractPermissions(user)
        localStorage.setItem('sl_user', JSON.stringify(user))
        localStorage.setItem('sl_perms', JSON.stringify(this.permissions))
      } catch {
        /* 令牌失效由 axios 拦截器提示，这里不打断页面 */
      }
    },

    logout() {
      this.token = ''
      this.user = null
      this.permissions = []
      localStorage.removeItem('sl_token')
      localStorage.removeItem('sl_user')
      localStorage.removeItem('sl_perms')
    },
  },
})

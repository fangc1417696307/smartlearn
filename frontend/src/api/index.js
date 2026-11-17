import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: '/api', timeout: 15000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sl_token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    // 大屏轮询等高频请求可传 silent: true，失败时不弹提示
    if (!err.config?.silent) {
      const msg = err.response?.data?.detail || '请求失败，请稍后重试'
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  },
)

export default api

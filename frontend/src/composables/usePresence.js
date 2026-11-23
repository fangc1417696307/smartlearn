/**
 * 全局实时在线状态（数据大屏「在线用户」的数据源）。
 *
 * 登录后主布局建立 /ws/presence 长连接：
 * - 连接建立 → 服务端立即记为在线；
 * - 每 30s ping 续期；10s 没收到 pong 判定半开连接并重连；
 * - 页面关闭 / 退出登录 → onBeforeUnmount 断开，服务端立即下线；
 * - 断网重连使用指数退避，与聊天连接同一套策略（PPT P07）。
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { getDeviceId } from '../utils/device'

const PING_INTERVAL = 30000
const PONG_TIMEOUT = 10000
const MAX_BACKOFF = 30000

export function usePresence() {
  const device = getDeviceId()

  let ws = null
  let retry = 0
  let pingTimer = null
  let pongTimer = null
  let reconnectTimer = null
  let manualClose = false

  function buildUrl() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const token = localStorage.getItem('sl_token') || ''
    return `${proto}://${location.host}/ws/presence?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}`
  }

  function clearTimers() {
    clearInterval(pingTimer)
    clearTimeout(pongTimer)
    clearTimeout(reconnectTimer)
    pingTimer = pongTimer = reconnectTimer = null
  }

  function startHeartbeat() {
    clearInterval(pingTimer)
    clearTimeout(pongTimer)
    const ping = () => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return
      try {
        ws.send(JSON.stringify({ type: 'ping' }))
      } catch {
        return
      }
      clearTimeout(pongTimer)
      pongTimer = setTimeout(() => {
        try {
          ws.close(4000, 'pong timeout')
        } catch {
          /* ignore */
        }
      }, PONG_TIMEOUT)
    }
    ping()
    pingTimer = setInterval(ping, PING_INTERVAL)
  }

  function scheduleReconnect() {
    const delay = Math.min(1000 * 2 ** retry, MAX_BACKOFF) + Math.floor(Math.random() * 1000)
    retry += 1
    reconnectTimer = setTimeout(connect, delay)
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return
    manualClose = false
    clearTimers()
    try {
      ws = new WebSocket(buildUrl())
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      retry = 0
      startHeartbeat()
    }
    ws.onmessage = (e) => {
      try {
        if (JSON.parse(e.data).type === 'pong') clearTimeout(pongTimer)
      } catch {
        /* ignore */
      }
    }
    ws.onclose = (e) => {
      clearTimers()
      if (e.code === 4401) {
        // token 失效：不再重试，等用户重新登录
        ws = null
        return
      }
      if (manualClose) return
      ws = null
      scheduleReconnect()
    }
    ws.onerror = () => {
      try {
        ws?.close()
      } catch {
        /* ignore */
      }
    }
  }

  function reconnectNow() {
    if (ws && ws.readyState === WebSocket.OPEN) return
    clearTimers()
    retry = 0
    connect()
  }

  function disconnect() {
    manualClose = true
    clearTimers()
    try {
      ws?.close(1000, 'bye')
    } catch {
      /* ignore */
    }
    ws = null
  }

  const onVisibility = () => {
    if (document.visibilityState === 'visible') reconnectNow()
  }
  const onOnline = () => reconnectNow()

  window.addEventListener('online', onOnline)
  document.addEventListener('visibilitychange', onVisibility)
  onMounted(connect)
  onBeforeUnmount(() => {
    window.removeEventListener('online', onOnline)
    document.removeEventListener('visibilitychange', onVisibility)
    disconnect()
  })
}

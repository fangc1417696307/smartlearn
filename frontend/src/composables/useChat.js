/**
 * 聊天 WebSocket 连接管理（对应 PPT P06 / P07 / P10 / P12）。
 *
 * - 心跳：每 30s 发 ping，10s 内没收到 pong 判定半开连接，主动断开重连
 * - 重连：指数退避 1s → 2s → 4s … 封顶 30s，并加随机抖动，避免重连风暴
 * - 重连成功后由页面负责调 sync 补拉断线期间的消息
 */
import { onBeforeUnmount, ref } from 'vue'
import { getDeviceId } from '../utils/device'

const PING_INTERVAL = 30000
const PONG_TIMEOUT = 10000
const MAX_BACKOFF = 30000

export function newClientId(uid) {
  const rand = globalThis.crypto?.randomUUID
    ? globalThis.crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36)
  return `${uid}:${rand}`
}

export function useChat({ uid, onEvent } = {}) {
  // idle | connecting | open | reconnecting | closed | unauthorized
  const status = ref('idle')
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
    return `${proto}://${location.host}/ws/chat?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}`
  }

  function clearTimers() {
    clearInterval(pingTimer)
    clearTimeout(pongTimer)
    clearTimeout(reconnectTimer)
    pingTimer = pongTimer = reconnectTimer = null
  }

  function stopHeartbeat() {
    clearInterval(pingTimer)
    clearTimeout(pongTimer)
    pingTimer = pongTimer = null
  }

  function startHeartbeat() {
    stopHeartbeat()
    const ping = () => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return
      try {
        ws.send(JSON.stringify({ type: 'ping' }))
      } catch {
        return
      }
      clearTimeout(pongTimer)
      pongTimer = setTimeout(() => {
        // 超过 10s 没收到 pong：TCP 可能已半开，主动断开走重连
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
    const base = Math.min(1000 * 2 ** retry, MAX_BACKOFF)
    const delay = base + Math.floor(Math.random() * 1000)
    retry += 1
    status.value = 'reconnecting'
    reconnectTimer = setTimeout(connect, delay)
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return
    manualClose = false
    clearTimers()
    status.value = retry === 0 ? 'connecting' : 'reconnecting'
    try {
      ws = new WebSocket(buildUrl())
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      retry = 0
      status.value = 'open'
      startHeartbeat()
    }

    ws.onmessage = (e) => {
      let data
      try {
        data = JSON.parse(e.data)
      } catch {
        return
      }
      if (data.type === 'pong') {
        clearTimeout(pongTimer)
        pongTimer = null
        return
      }
      onEvent?.(data)
    }

    ws.onclose = (e) => {
      stopHeartbeat()
      if (e.code === 4401) {
        status.value = 'unauthorized'
        onEvent?.({ type: 'unauthorized' })
        return
      }
      if (manualClose) {
        status.value = 'idle'
        return
      }
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

  /** 立即重连（切回页面、网络恢复时用），清掉退避等待 */
  function reconnectNow() {
    if (status.value === 'open' || status.value === 'unauthorized') return
    if (ws && ws.readyState === WebSocket.OPEN) return
    clearTimers()
    retry = 0
    connect()
  }

  function send(payload) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return false
    try {
      ws.send(JSON.stringify(payload))
      return true
    } catch {
      return false
    }
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
    status.value = 'idle'
  }

  function onVisibility() {
    if (document.visibilityState === 'visible') reconnectNow()
  }
  function onOnline() {
    reconnectNow()
  }

  window.addEventListener('online', onOnline)
  document.addEventListener('visibilitychange', onVisibility)

  onBeforeUnmount(() => {
    window.removeEventListener('online', onOnline)
    document.removeEventListener('visibilitychange', onVisibility)
    disconnect()
  })

  return { status, connect, reconnectNow, send, disconnect }
}

<template>
  <el-card shadow="never" class="chat-panel">
    <template #header>
      <div class="head">
        <span>💬 消息</span>
        <span class="conn" :class="status">
          <i class="dot"></i>
          {{ statusText }}
        </span>
      </div>
    </template>

    <div class="chat-body">
      <!-- 左：会话列表 -->
      <aside class="conv-list">
        <div class="conv-tools">
          <el-input v-model="keyword" placeholder="搜索会话" size="small" clearable />
          <el-button type="primary" circle size="small" title="发起聊天" @click="openCreate">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        <div class="conv-scroll">
          <div
            v-for="c in filteredConversations"
            :key="c.id"
            class="conv-item"
            :class="{ active: c.id === activeId }"
            @click="selectConversation(c.id)"
          >
            <div class="avatar" :class="{ group: c.type === 'group' }">
              {{ avatarText(c) }}
              <i v-if="c.type === 'private' && c.online" class="online-dot"></i>
            </div>
            <div class="conv-main">
              <div class="conv-title">
                <span class="name">{{ c.name }}</span>
                <span class="time">{{ fmtListTime(c.updatedAt) }}</span>
              </div>
              <div class="conv-preview">
                <span class="preview-text">{{ previewText(c) }}</span>
                <span v-if="c.unread" class="unread">{{ c.unread > 99 ? '99+' : c.unread }}</span>
              </div>
            </div>
          </div>
          <div v-if="!filteredConversations.length" class="conv-empty">暂无会话</div>
        </div>
      </aside>

      <!-- 右：消息区 -->
      <section class="chat-main">
        <template v-if="activeConversation">
          <div class="chat-header">
            <div>
              <div class="chat-title">{{ activeConversation.name }}</div>
              <div class="chat-sub">
                <template v-if="activeConversation.type === 'group'">
                  {{ activeConversation.memberCount }} 位成员
                </template>
                <template v-else>
                  {{ activeConversation.online ? '在线' : '离线' }}
                </template>
              </div>
            </div>
            <span class="history-seq">seq {{ maxSeqMap[activeId] || 0 }}</span>
          </div>

          <div ref="boxRef" class="messages">
            <div v-if="hasMoreMap[activeId]" class="load-more">
              <el-button link :loading="loadingOlder" @click="loadOlder">加载更早的消息</el-button>
            </div>
            <div
              v-for="m in activeMessages"
              :key="m.key"
              class="msg"
              :class="m.sender?.id === myId ? 'mine' : 'other'"
            >
              <div class="msg-meta">
                <span v-if="activeConversation.type === 'group' && m.sender?.id !== myId">{{ m.sender?.nickname }}</span>
                <span class="msg-time">{{ fmtTime(m.createdAt) }}</span>
              </div>
              <!-- 纯文本插值渲染，天然防 XSS（PPT P16） -->
              <div class="bubble">{{ m.body }}</div>
              <div v-if="m.sender?.id === myId" class="msg-status">
                <el-icon v-if="m.status === 'sending'" class="sending"><Loading /></el-icon>
                <el-icon v-else-if="m.status === 'failed'" class="failed" title="发送失败，点击重发" @click="retryMessage(m)">
                  <WarningFilled />
                </el-icon>
                <el-icon v-else class="ok"><Check /></el-icon>
              </div>
            </div>
            <div v-if="!activeMessages.length" class="empty">还没有消息，打个招呼吧 👋</div>
          </div>

          <div class="composer">
            <el-input
              v-model="input"
              type="textarea"
              :rows="2"
              resize="none"
              maxlength="4000"
              show-word-limit
              placeholder="输入消息，Enter 发送，Shift + Enter 换行"
              @keydown.enter.exact.prevent="sendMessage"
            />
            <el-button type="primary" :disabled="!input.trim()" @click="sendMessage">发送</el-button>
          </div>
        </template>
        <div v-else class="no-active">选择左侧会话开始聊天</div>
      </section>
    </div>

    <!-- 发起会话 -->
    <el-dialog v-model="createVisible" title="发起聊天" width="440px">
      <el-radio-group v-model="createMode" class="mode-switch">
        <el-radio-button value="private">私聊</el-radio-button>
        <el-radio-button value="group">群聊</el-radio-button>
      </el-radio-group>
      <el-input
        v-if="createMode === 'group'"
        v-model="groupName"
        class="group-name"
        maxlength="60"
        placeholder="群聊名称，例如：数据结构 · 期中复习群"
      />
      <el-select
        v-if="createMode === 'private'"
        v-model="selectedPeer"
        filterable
        class="user-select"
        placeholder="选择聊天对象"
      >
        <el-option
          v-for="u in chatUsers"
          :key="u.id"
          :label="`${u.nickname}（${u.account}）`"
          :value="u.id"
        />
      </el-select>
      <el-select
        v-else
        v-model="selectedMembers"
        multiple
        collapse-tags
        collapse-tags-tooltip
        filterable
        class="user-select"
        placeholder="选择群成员（可多选）"
      >
        <el-option
          v-for="u in chatUsers"
          :key="u.id"
          :label="`${u.nickname}（${u.account}）`"
          :value="u.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useUserStore } from '../store/user'
import { newClientId, useChat } from '../composables/useChat'

const route = useRoute()
const userStore = useUserStore()
const myId = computed(() => userStore.user?.id)

const conversations = ref([])
const activeId = ref(null)
const messagesMap = reactive({})
const maxSeqMap = reactive({})
const hasMoreMap = reactive({})
const pending = new Map() // clientId -> 消息对象（等待 ack）

const input = ref('')
const keyword = ref('')
const boxRef = ref(null)
const loadingOlder = ref(false)

const createVisible = ref(false)
const createMode = ref('private')
const groupName = ref('')
const selectedPeer = ref(null)
const selectedMembers = ref([])
const chatUsers = ref([])
const creating = ref(false)

const readTimers = {}
const RETRY_MAX = 3

const activeConversation = computed(() =>
  conversations.value.find((c) => c.id === activeId.value) || null,
)
const activeMessages = computed(() => messagesMap[activeId.value] || [])
const filteredConversations = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return conversations.value
  return conversations.value.filter((c) => c.name.includes(kw))
})
const statusText = computed(() => ({
  idle: '未连接',
  connecting: '连接中…',
  open: '已连接',
  reconnecting: '正在重连…',
  closed: '已断开',
  unauthorized: '登录已失效',
}[status.value] || '未连接'))

const { status, connect, send } = useChat({ onEvent: handleEvent })

// ---------------------------------------------------------------------------
// 数据归一化 / 插入（按 seq 有序，对应 PPT P11 客户端排序）
// ---------------------------------------------------------------------------

function meBrief() {
  return {
    id: myId.value,
    account: userStore.user?.account || '',
    nickname: userStore.user?.nickname || '我',
  }
}

function normalize(m, msgStatus = 'ok') {
  return {
    key: m.id ? `m${m.id}` : `c${m.clientId}`,
    id: m.id ?? null,
    convId: m.convId,
    seq: m.seq ?? null,
    sender: m.sender,
    body: m.body,
    clientId: m.clientId,
    createdAt: m.createdAt || new Date().toISOString(),
    status: msgStatus,
    retries: 0,
    timer: null,
  }
}

function insertMessage(convId, data) {
  if (!messagesMap[convId]) messagesMap[convId] = []
  const arr = messagesMap[convId]

  // 乐观消息与服务端回包按 clientId 合并（P10）
  const byClient = data.clientId ? arr.find((x) => x.clientId === data.clientId) : null
  if (byClient) {
    Object.assign(byClient, normalize(data), { key: byClient.key })
    return byClient
  }
  if (data.id) {
    const byId = arr.find((x) => x.id === data.id)
    if (byId) {
      Object.assign(byId, normalize(data), { key: byId.key })
      return byId
    }
  }

  const item = reactive(normalize(data))
  const idx = arr.findIndex((x) => x.seq != null && data.seq != null && x.seq > data.seq)
  if (idx === -1) arr.push(item)
  else arr.splice(idx, 0, item)
  return item
}

function noteMaxSeq(convId, seq) {
  if (!seq) return
  if (seq > (maxSeqMap[convId] || 0)) maxSeqMap[convId] = seq
}

function findConv(id) {
  return conversations.value.find((c) => c.id === id)
}

function sortConversations() {
  conversations.value.sort((a, b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')))
}

let convRefreshTimer = null
function scheduleConversationRefresh() {
  // 收到陌生会话的消息（对方刚发起聊天）：防抖刷新一次会话列表
  if (convRefreshTimer) return
  convRefreshTimer = setTimeout(() => {
    convRefreshTimer = null
    loadConversations().catch(() => {})
  }, 300)
}

function updatePreview(convId, message, mine) {
  const conv = findConv(convId)
  if (!conv) {
    scheduleConversationRefresh()
    return
  }
  conv.lastMessage = message
  conv.lastSeq = Math.max(conv.lastSeq || 0, message.seq || 0)
  conv.updatedAt = message.createdAt
  if (!mine && convId !== activeId.value) conv.unread = (conv.unread || 0) + 1
  sortConversations()
}

// ---------------------------------------------------------------------------
// 收发
// ---------------------------------------------------------------------------

function handleEvent(data) {
  switch (data.type) {
    case 'ack':
      onAck(data)
      break
    case 'chat':
      onChat(data.message)
      break
    case 'presence':
      for (const c of conversations.value) {
        if (c.type === 'private' && c.peer?.id === data.userId) c.online = data.online
      }
      break
    case 'read':
      if (findConv(data.convId)) findConv(data.convId).unread = 0
      break
    case 'error':
      onError(data)
      break
    case 'unauthorized':
      ElMessage.error('登录状态已失效，请重新登录')
      break
    default:
      break
  }
}

function onAck(data) {
  const msg = pending.get(data.clientId)
  if (!msg) return
  pending.delete(data.clientId)
  clearTimeout(msg.timer)

  const before = maxSeqMap[data.convId] || 0
  const item = insertMessage(data.convId, {
    id: data.msgId,
    convId: data.convId,
    seq: data.seq,
    sender: msg.sender,
    body: msg.body,
    clientId: data.clientId,
    createdAt: data.createdAt,
  })
  item.status = 'ok'
  noteMaxSeq(data.convId, data.seq)

  // 空洞检测：说明中间有消息没收到，拉增量补齐（P11）
  if (data.seq > before + 1) syncConv(data.convId)
  if (data.convId === activeId.value) scrollBottom()
}

function onChat(message) {
  const convId = message.convId
  const mine = message.sender?.id === myId.value
  const loaded = !!messagesMap[convId] || convId === activeId.value
  const before = maxSeqMap[convId] || 0

  if (loaded) insertMessage(convId, message)
  noteMaxSeq(convId, message.seq)
  if (loaded && message.seq > before + 1) syncConv(convId)

  updatePreview(convId, message, mine)

  if (convId === activeId.value) {
    markReadDebounced(convId)
    if (document.visibilityState === 'visible') scrollBottom()
  }
}

function onError(data) {
  if (data.clientId) {
    const msg = pending.get(data.clientId)
    if (msg) {
      clearTimeout(msg.timer)
      msg.status = 'failed'
      pending.delete(data.clientId)
    }
  }
  if (data.code === 'RATE_LIMIT') ElMessage.warning(data.message || '发送太频繁')
  else if (data.code !== 'UNAUTHORIZED') ElMessage.error(data.message || '发送失败')
}

function sendMessage() {
  const body = input.value.trim()
  const convId = activeId.value
  if (!body || !convId) return

  const clientId = newClientId(myId.value)
  const msg = reactive(normalize({
    convId, clientId, sender: meBrief(), body,
    createdAt: new Date().toISOString(),
  }, 'sending'))
  if (!messagesMap[convId]) messagesMap[convId] = []
  messagesMap[convId].push(msg)
  pending.set(clientId, msg)
  input.value = ''
  scrollBottom()
  updatePreview(convId, msg, true)

  if (send({ type: 'chat', convId, clientId, body })) {
    scheduleRetry(msg, 3000)
  } else {
    // 连接未就绪：先停留在「发送中」，重连后由 watch 统一重发（P07）
    scheduleRetry(msg, 1500)
  }
}

function scheduleRetry(msg, delay = 3000) {
  clearTimeout(msg.timer)
  msg.timer = setTimeout(() => resend(msg), delay)
}

function resend(msg) {
  if (msg.status !== 'sending') return
  if ((msg.retries || 0) >= RETRY_MAX) {
    msg.status = 'failed'
    pending.delete(msg.clientId)
    return
  }
  msg.retries = (msg.retries || 0) + 1
  if (send({ type: 'chat', convId: msg.convId, clientId: msg.clientId, body: msg.body })) {
    scheduleRetry(msg, 3000)
  }
  // 发送失败（未连接）就不再排定时器，等重连成功后统一重发
}

function retryMessage(msg) {
  msg.status = 'sending'
  msg.retries = 0
  pending.set(msg.clientId, msg)
  resend(msg)
}

// ---------------------------------------------------------------------------
// 同步 / 已读
// ---------------------------------------------------------------------------

async function syncConv(convId) {
  if (!convId) return
  if (!messagesMap[convId] && convId !== activeId.value) return
  const cur = maxSeqMap[convId] || 0
  try {
    const res = await api.get(`/chat/conversations/${convId}/messages`, {
      params: { afterSeq: cur, limit: 500 },
      silent: true,
    })
    res.messages.forEach((m) => insertMessage(convId, m))
    noteMaxSeq(convId, res.lastSeq)
  } catch {
    // 下次重连或收到下一条消息时会再次触发
  }
}

async function markRead(convId) {
  const seq = maxSeqMap[convId] || 0
  const conv = findConv(convId)
  if (conv) conv.unread = 0
  if (!seq) return
  try {
    await api.post(`/chat/conversations/${convId}/read`, { seq }, { silent: true })
  } catch {
    /* 已读上报失败不影响聊天 */
  }
}

function markReadDebounced(convId) {
  clearTimeout(readTimers[convId])
  readTimers[convId] = setTimeout(() => {
    const seq = maxSeqMap[convId] || 0
    if (seq) send({ type: 'read', convId, seq })
  }, 300)
}

// ---------------------------------------------------------------------------
// 会话列表 / 历史
// ---------------------------------------------------------------------------

async function loadConversations() {
  const list = await api.get('/chat/conversations')
  conversations.value = list
  if (!activeId.value && list.length) {
    const wanted = Number(route.query.conv)
    await selectConversation(list.find((c) => c.id === wanted) ? wanted : list[0].id)
  } else if (activeId.value && !findConv(activeId.value)) {
    activeId.value = null
    if (list.length) await selectConversation(list[0].id)
  }
}

async function selectConversation(id) {
  if (!id) return
  activeId.value = id
  window.history.replaceState({}, '', `?conv=${id}`)
  const conv = findConv(id)
  if (conv) conv.unread = 0

  if (!messagesMap[id]) {
    const liveMax = maxSeqMap[id] || 0
    const res = await api.get(`/chat/conversations/${id}/messages`, {
      params: { limit: 50 },
    })
    messagesMap[id] = res.messages.map((m) => reactive(normalize(m)))
    maxSeqMap[id] = res.lastSeq
    hasMoreMap[id] = res.hasMore
    // 拉历史期间如果实时收到了新消息，会在这之前写进 maxSeqMap；补拉一次防丢
    if (liveMax > res.lastSeq) syncConv(id)
  } else {
    syncConv(id)
  }
  markRead(id)
  scrollBottom()
}

async function loadOlder() {
  const id = activeId.value
  if (!id || loadingOlder.value) return
  const first = (messagesMap[id] || []).find((m) => m.seq != null)
  if (!first) return

  loadingOlder.value = true
  const el = boxRef.value
  const prevHeight = el?.scrollHeight || 0
  try {
    const res = await api.get(`/chat/conversations/${id}/messages`, {
      params: { beforeSeq: first.seq, limit: 50 },
    })
    const older = res.messages.map((m) => reactive(normalize(m)))
    messagesMap[id] = [...older, ...(messagesMap[id] || [])]
    hasMoreMap[id] = res.hasMore
    await nextTick()
    if (el) el.scrollTop = el.scrollHeight - prevHeight
  } finally {
    loadingOlder.value = false
  }
}

function scrollBottom() {
  nextTick(() => {
    const el = boxRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// ---------------------------------------------------------------------------
// 发起会话
// ---------------------------------------------------------------------------

async function openCreate() {
  try {
    chatUsers.value = await api.get('/chat/users')
  } catch {
    return
  }
  createMode.value = 'private'
  groupName.value = ''
  selectedPeer.value = null
  selectedMembers.value = []
  createVisible.value = true
}

async function submitCreate() {
  if (createMode.value === 'private' && !selectedPeer.value) {
    return ElMessage.warning('请选择聊天对象')
  }
  if (createMode.value === 'group' && !selectedMembers.value.length) {
    return ElMessage.warning('请选择群成员')
  }
  if (createMode.value === 'group' && !groupName.value.trim()) {
    return ElMessage.warning('请填写群聊名称')
  }
  creating.value = true
  try {
    const payload = createMode.value === 'private'
      ? { type: 'private', peerId: selectedPeer.value }
      : { type: 'group', name: groupName.value.trim(), memberIds: selectedMembers.value }
    const conv = await api.post('/chat/conversations', payload)
    createVisible.value = false
    const list = await api.get('/chat/conversations')
    conversations.value = list
    await selectConversation(conv.id)
  } finally {
    creating.value = false
  }
}

// ---------------------------------------------------------------------------
// 展示辅助
// ---------------------------------------------------------------------------

function avatarText(c) {
  return c.type === 'group' ? '群' : (c.peer?.nickname || c.name || '?').slice(0, 1)
}

function previewText(c) {
  const last = c.lastMessage
  if (!last) return '暂无消息'
  const prefix = c.type === 'group' && last.sender?.id !== myId.value ? `${last.sender?.nickname}：` : ''
  return prefix + last.body
}

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function fmtListTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

// 重连成功：补拉增量 + 重发断线期间的「发送中」消息（P07 + P12）
let hasOpenedOnce = false
watch(status, (s, prev) => {
  if (s !== 'open' || prev === 'open') return
  if (!hasOpenedOnce) {
    hasOpenedOnce = true // 首次连接由 onMounted 负责初始化
    return
  }
  loadConversations().catch(() => {})
  if (activeId.value) {
    syncConv(activeId.value)
    markRead(activeId.value)
  }
  for (const msg of pending.values()) {
    if (msg.status === 'sending') {
      clearTimeout(msg.timer)
      resend(msg)
    }
  }
})

onMounted(async () => {
  connect()
  try {
    await loadConversations()
  } catch {
    /* 错误提示由 axios 拦截器处理 */
  }
})
</script>

<style scoped>
.chat-panel { border-radius: 20px; }
.chat-panel :deep(.el-card__body) { padding: 0; }
.head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.conn { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; color: #737373; }
.conn .dot { width: 8px; height: 8px; border-radius: 50%; background: #c0c0c0; }
.conn.open .dot { background: #3ac569; }
.conn.connecting .dot, .conn.reconnecting .dot { background: #f0a020; animation: pulse 1s infinite; }
.conn.unauthorized .dot, .conn.closed .dot { background: #e34d4d; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.chat-body { display: grid; grid-template-columns: 290px 1fr; height: calc(100vh - 205px); min-height: 480px; }
.conv-list { border-right: 1px solid #e5e5e5; display: flex; flex-direction: column; min-height: 0; }
.conv-tools { display: flex; gap: 8px; padding: 12px; border-bottom: 1px solid #f0f0f0; }
.conv-scroll { flex: 1; overflow-y: auto; padding: 6px; }
.conv-empty { color: #999; text-align: center; padding: 30px 0; font-size: 13px; }
.conv-item { display: flex; gap: 10px; padding: 10px; border-radius: 14px; cursor: pointer; align-items: center; transition: 0.15s; }
.conv-item:hover { background: #f5f4ec; }
.conv-item.active { background: #bcf887; }
.avatar { position: relative; width: 42px; height: 42px; border-radius: 50%; flex: none; background: #2908ff; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; }
.avatar.group { background: #00b5c2; }
.online-dot { position: absolute; right: -1px; bottom: -1px; width: 12px; height: 12px; border-radius: 50%; background: #3ac569; border: 2px solid #fff; }
.conv-main { flex: 1; min-width: 0; }
.conv-title { display: flex; justify-content: space-between; gap: 8px; font-size: 14px; font-weight: 700; }
.conv-title .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-title .time { color: #999; font-size: 11px; font-weight: 400; flex: none; }
.conv-preview { display: flex; justify-content: space-between; gap: 8px; margin-top: 4px; color: #8a8a8a; font-size: 12px; }
.preview-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.unread { flex: none; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 999px; background: #e34d4d; color: #fff; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }

.chat-main { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.chat-title { font-size: 16px; font-weight: 800; }
.chat-sub { font-size: 12px; color: #8a8a8a; margin-top: 3px; }
.history-seq { font-size: 11px; color: #aaa; font-family: monospace; }
.messages { flex: 1; overflow-y: auto; padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; }
.load-more { text-align: center; padding-bottom: 4px; }
.msg { display: flex; flex-direction: column; max-width: 66%; gap: 4px; }
.msg.other { align-self: flex-start; }
.msg.mine { align-self: flex-end; align-items: flex-end; }
.msg-meta { display: flex; gap: 8px; font-size: 11px; color: #999; padding: 0 4px; }
.msg-status { font-size: 12px; color: #999; padding: 0 4px; }
.msg-status .sending { color: #f0a020; }
.msg-status .ok { color: #3ac569; }
.msg-status .failed { color: #e34d4d; cursor: pointer; }
.bubble { padding: 11px 15px; border-radius: 15px; font-size: 14px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.msg.other .bubble { background: #fff; border: 1px solid #e5e5e5; border-top-left-radius: 4px; }
.msg.mine .bubble { background: #2908ff; color: #fff; border-top-right-radius: 4px; }
.empty { color: #aaa; font-size: 13px; text-align: center; margin-top: 40px; }
.no-active { flex: 1; display: flex; align-items: center; justify-content: center; color: #aaa; }

.composer { border-top: 1px solid #e5e5e5; padding: 12px 16px; display: flex; gap: 10px; align-items: flex-end; }
.composer .el-button { border-radius: 999px; height: 40px; padding: 0 22px; }

.mode-switch { margin-bottom: 14px; }
.group-name { margin-bottom: 12px; }
.user-select { width: 100%; }
</style>

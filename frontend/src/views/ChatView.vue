<template>
  <div class="chat chat-layout">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card class="session-panel" :body-style="{ padding: '0', display: 'flex', flexDirection: 'column', height: '100%' }">
          <template #header>
            <div class="row">
              <div class="panel-heading">
                <span class="panel-title">会话</span>
                <span class="panel-count">{{ sessionTotal }}</span>
              </div>
              <el-button size="small" type="primary" round @click.stop="newSession">
                <el-icon class="btn-icon"><Plus /></el-icon>
                新建
              </el-button>
            </div>
          </template>

          <div class="kb-block">
            <div class="kb-block__label">
              <el-icon><Collection /></el-icon>
              <span>知识库范围</span>
            </div>
            <el-select
              v-model="selectedKbIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :max-collapse-tags="1"
              placeholder="选择要检索的知识库"
              class="kb-select"
            >
              <el-option v-for="kb in activeKbs" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
            <p class="kb-block__hint">
              {{ selectedKbIds.length ? `已选 ${selectedKbIds.length} 个库` : '请至少选择一个知识库' }}
            </p>
          </div>

          <div class="session-list-head">
            <span>历史对话</span>
          </div>

          <div class="session-list">
            <div v-if="draftMode" class="chat-session-item active draft">
              <span class="session-icon draft-icon" aria-hidden="true" />
              <div class="session-meta">
                <span class="title">新对话（未发送）</span>
                <span class="sub">发送第一条消息后保存</span>
              </div>
            </div>

            <div
              v-for="s in sessions"
              :key="s.id"
              class="chat-session-item"
              :class="{ active: !draftMode && currentSessionId === s.id }"
              @click="loadSession(String(s.id))"
            >
              <span class="session-icon" aria-hidden="true" />
              <div class="session-meta">
                <span class="title" :title="s.title">{{ s.title || '未命名对话' }}</span>
                <span class="sub">{{ formatSessionTime(s) }}</span>
              </div>
              <el-dropdown trigger="click" @click.stop>
                <button type="button" class="session-more" @click.stop>
                  <el-icon><MoreFilled /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="renameSession(s)">改标题</el-dropdown-item>
                    <el-dropdown-item divided @click="deleteSession(s.id)">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div v-if="!draftMode && !sessions.length" class="session-empty">
              <p>还没有历史对话</p>
              <span>点右上角「新建」开始提问</span>
            </div>
          </div>

          <div v-if="sessionTotal > sessionPageSize" class="session-pager">
            <el-pagination
              small
              layout="prev, pager, next"
              :total="sessionTotal"
              :page-size="sessionPageSize"
              v-model:current-page="sessionPage"
              @current-change="loadSessions"
            />
          </div>
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-card class="panel chat-panel">
          <div class="chat-messages" ref="boxRef">
            <div v-if="!messages.length" class="chat-empty">
              <div class="chat-empty__avatar" aria-hidden="true">
                <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" class="mascot">
                  <defs>
                    <linearGradient id="mascotBody" x1="20" y1="20" x2="100" y2="110" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#7dd3fc" />
                      <stop offset="1" stop-color="#0284c7" />
                    </linearGradient>
                    <linearGradient id="mascotCheek" x1="0" y1="0" x2="1" y2="1">
                      <stop stop-color="#fda4af" />
                      <stop offset="1" stop-color="#fb7185" />
                    </linearGradient>
                  </defs>
                  <!-- soft glow -->
                  <ellipse cx="60" cy="108" rx="34" ry="6" fill="rgba(2,132,199,0.18)" />
                  <!-- body -->
                  <circle cx="60" cy="62" r="38" fill="url(#mascotBody)" />
                  <!-- ears -->
                  <path d="M28 48c-6-18 8-30 18-18" fill="#38bdf8" />
                  <path d="M92 48c6-18-8-30-18-18" fill="#38bdf8" />
                  <path d="M31 47c-3-10 4-16 10-9" fill="#e0f2fe" />
                  <path d="M89 47c3-10-4-16-10-9" fill="#e0f2fe" />
                  <!-- face plate -->
                  <ellipse cx="60" cy="66" rx="28" ry="24" fill="#f0f9ff" />
                  <!-- eyes -->
                  <circle cx="48" cy="62" r="5.5" fill="#0f2744" />
                  <circle cx="72" cy="62" r="5.5" fill="#0f2744" />
                  <circle cx="49.8" cy="60.2" r="1.8" fill="#fff" />
                  <circle cx="73.8" cy="60.2" r="1.8" fill="#fff" />
                  <!-- cheeks -->
                  <circle cx="40" cy="72" r="4.5" fill="url(#mascotCheek)" opacity="0.75" />
                  <circle cx="80" cy="72" r="4.5" fill="url(#mascotCheek)" opacity="0.75" />
                  <!-- smile -->
                  <path d="M50 76c4 5 16 5 20 0" fill="none" stroke="#0369a1" stroke-width="2.4" stroke-linecap="round" />
                  <!-- book / knowledge badge -->
                  <rect x="78" y="86" width="22" height="16" rx="3" fill="#fff" stroke="#0284c7" stroke-width="1.5" />
                  <path d="M89 86v16" stroke="#0284c7" stroke-width="1.2" />
                  <path d="M82 91h6M82 95h6" stroke="#7dd3fc" stroke-width="1.4" stroke-linecap="round" />
                </svg>
              </div>
              <h3 class="chat-empty__title">基于企业文档的智能问答</h3>
              <p class="chat-empty__desc">选好左侧知识库后提问。同一会话可追问；新建对话也会记住你最近聊过的内容，例如接着问「那它的薪资怎么样」。回答会附带文档引用。</p>
              <div class="chat-empty__tips">
                <span>跨会话记忆</span>
                <span>多库检索</span>
                <span>流式回答</span>
                <span>来源可追溯</span>
              </div>
            </div>
            <div v-for="m in messages" :key="m.id" :class="['chat-msg', m.role]">
              <div class="chat-bubble">{{ displayContent(m) }}</div>
              <details v-if="m.sources?.length" class="sources">
                <summary>查看引用（{{ m.sources.length }}）</summary>
                <div v-for="(s, i) in m.sources" :key="i">《{{ s.document_name }}》 {{ (s.snippet || '').slice(0, 200) }}…</div>
              </details>
              <div v-if="m.role === 'assistant' && m.id && !String(m.id).startsWith('temp')" class="feedback">
                <el-button size="small" :type="m.feedback === 1 ? 'primary' : 'default'" @click="feedback(m, 1)">有用</el-button>
                <el-button size="small" :type="m.feedback === -1 ? 'danger' : 'default'" @click="feedback(m, -1)">无用</el-button>
              </div>
            </div>
          </div>
          <div class="composer">
            <el-input
              v-model="question"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="输入问题，Ctrl + Enter 发送…"
              @keydown.ctrl.enter="send"
            />
            <div class="send-row">
              <span class="composer-tip">支持多轮追问；回答基于所选知识库与本会话上文</span>
              <div class="send-actions">
                <el-button v-if="streaming" @click="abortStream">停止</el-button>
                <el-button type="primary" :loading="streaming" @click="send">发送</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, MoreFilled, Plus } from '@element-plus/icons-vue'
import http, { formatApiError } from '../api/http'

const route = useRoute()

function formatSessionTime(s) {
  const raw = s.updated_at || s.created_at
  if (!raw) return '近期'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return '近期'
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

const kbs = ref([])
const sessions = ref([])
const sessionPage = ref(1)
const sessionPageSize = 20
const sessionTotal = ref(0)
const messages = ref([])
const selectedKbIds = ref([])
const currentSessionId = ref(null)
const question = ref('')
const streaming = ref(false)
const draftMode = ref(false)
const boxRef = ref(null)
let abortCtrl = null

const activeKbs = computed(() => kbs.value.filter((k) => k.is_active))

/** 去掉历史消息里已废弃的千问/限流提示（库里的旧数据） */
function displayContent(m) {
  let s = m.content || ''
  if (m.role !== 'assistant') return s
  const mark = '【根据知识库整理】'
  const i = s.indexOf(mark)
  if (i > 0) return s.slice(i).trim()
  if (/通义千问|DASHSCOPE|百炼|限流|API-KEY/i.test(s)) {
    s = s.replace(/⚠️[\s\S]*?(?=【|$)/u, '').trim()
  }
  return s
}

async function loadKbs() {
  const { data } = await http.get('/knowledge-bases', { params: { page: 1, page_size: 100 } })
  kbs.value = data.items
  // 不默认勾选，由用户自己点开选择
  selectedKbIds.value = []
}

async function loadSessions() {
  const { data } = await http.get('/chat/sessions', {
    params: { page: sessionPage.value, page_size: sessionPageSize },
  })
  sessions.value = data.items
  sessionTotal.value = data.total
}

async function loadSession(id) {
  if (streaming.value) abortStream()
  draftMode.value = false
  currentSessionId.value = Number(id)
  const { data } = await http.get(`/chat/sessions/${id}/messages`)
  messages.value = data
  scrollBottom()
}

async function newSession() {
  if (streaming.value) abortStream()
  if (!selectedKbIds.value.length) {
    ElMessage.warning('请先选择至少一个知识库')
    return
  }
  draftMode.value = true
  currentSessionId.value = null
  messages.value = []
  question.value = ''
  ElMessage.success('已开始新对话（仍会记住最近聊天，可直接追问）')
  await nextTick()
  scrollBottom()
}

async function renameSession(s) {
  const { value } = await ElMessageBox.prompt('会话标题', '修改标题', { inputValue: s.title })
  if (value) {
    await http.put(`/chat/sessions/${s.id}?title=${encodeURIComponent(value)}`)
    loadSessions()
  }
}

async function deleteSession(id) {
  await ElMessageBox.confirm('确定删除该会话及全部消息？')
  await http.delete(`/chat/sessions/${id}`)
  if (currentSessionId.value === id) newSession()
  loadSessions()
}

async function feedback(m, v) {
  await http.post(`/chat/messages/${m.id}/feedback`, { feedback: v })
  m.feedback = v
  ElMessage.success('感谢反馈')
}

function abortStream() {
  abortCtrl?.abort()
}

async function send() {
  if (!question.value.trim() || !selectedKbIds.value.length) {
    ElMessage.warning('请选择至少一个启用的知识库并输入问题')
    return
  }
  streaming.value = true
  abortCtrl = new AbortController()
  const q = question.value
  question.value = ''
  messages.value.push({ id: `temp-u-${Date.now()}`, role: 'user', content: q })
  const assistant = { id: `temp-a-${Date.now()}`, role: 'assistant', content: '', sources: [], feedback: null }
  messages.value.push(assistant)
  scrollBottom()

  let gotDelta = false
  try {
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      signal: abortCtrl.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
        'X-Auth-Type': localStorage.getItem('auth_type') || 'tenant',
      },
      body: JSON.stringify({
        session_id: currentSessionId.value,
        kb_ids: selectedKbIds.value,
        question: q,
      }),
    })
    if (!resp.ok) {
      let detail = '请求失败'
      try {
        const errJson = await resp.json()
        detail = formatApiError({ response: { data: errJson } }, detail)
      } catch {
        detail = (await resp.text()) || detail
      }
      assistant.content = `[未能回答] ${detail}`
      ElMessage.error(detail)
      return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    const STATUS_HINT = '正在检索知识库并生成回答'
    const applyAnswer = (text) => {
      if (!text) return
      assistant.content = text
      gotDelta = true
    }
    const fallbackFromSources = (sources) => {
      if (!sources?.length) return ''
      const lines = sources.slice(0, 5).map((s, i) => {
        const sn = (s.snippet || '').trim().replace(/\s+/g, ' ')
        return `${i + 1}. 《${s.document_name || '文档'}》\n   ${sn.slice(0, 280)}${sn.length > 280 ? '…' : ''}`
      })
      return `（根据知识库检索整理）\n\n${lines.join('\n\n')}`
    }
    const handleEvent = (payload) => {
      if (payload.type === 'session') {
        currentSessionId.value = payload.session_id
        draftMode.value = false
      }
      if (payload.type === 'status' && !gotDelta) {
        assistant.content = payload.content || '正在生成…'
      }
      if (payload.type === 'answer') {
        applyAnswer(payload.content || '')
      }
      if (payload.type === 'delta') {
        const piece = payload.content || ''
        if (piece) {
          if (!gotDelta) assistant.content = ''
          gotDelta = true
          assistant.content += piece
        }
      }
      if (payload.type === 'sources') {
        assistant.sources = payload.sources || []
        if (!gotDelta || assistant.content.includes(STATUS_HINT)) {
          const fb = fallbackFromSources(assistant.sources)
          if (fb) applyAnswer(fb)
        }
      }
      if (payload.type === 'done' && payload.message_id) assistant.id = payload.message_id
      if (payload.type === 'error') {
        ElMessage.error(payload.message || '问答出错')
        if (!gotDelta) assistant.content = `[错误] ${payload.message || '问答处理失败'}`
      }
    }
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const blocks = buf.split('\n\n')
      buf = blocks.pop() || ''
      for (const block of blocks) {
        for (const line of block.split('\n')) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue
          const jsonStr = trimmed.slice(5).trim().replace(/^:/, '')
          if (!jsonStr) continue
          try {
            handleEvent(JSON.parse(jsonStr))
          } catch {
            /* 半包 JSON */
          }
        }
      }
      scrollBottom()
    }
    if (!gotDelta && !assistant.content) {
      assistant.content =
        '未收到回答内容。请确认后端已启动、文档已解析成功；本地可在 backend/.env 设置 EMBEDDING_MOCK=true 加快检索。'
    }
    await loadSessions()
  } catch (e) {
    if (e.name !== 'AbortError') {
      const msg = e.message || '流式请求失败'
      assistant.content = assistant.content || `[请求失败] ${msg}`
      ElMessage.error(msg)
    }
  } finally {
    streaming.value = false
    abortCtrl = null
  }
}

function scrollBottom() {
  nextTick(() => {
    if (boxRef.value) boxRef.value.scrollTop = boxRef.value.scrollHeight
  })
}

async function openSessionFromRoute() {
  const sid = Number(route.query.session)
  if (!sid) return
  await loadSessions()
  const exists = sessions.value.some((s) => s.id === sid)
  if (!exists) {
    // 可能不在当前页，仍尝试拉取消息
  }
  await loadSession(sid)
}

onMounted(async () => {
  await loadKbs()
  await loadSessions()
  await openSessionFromRoute()
})

watch(
  () => route.query.session,
  async (sid) => {
    if (sid) await openSessionFromRoute()
  },
)
</script>

<style scoped>
.panel-heading {
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel-title {
  font-weight: 700;
  letter-spacing: -0.02em;
}
.panel-count {
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--color-accent-soft);
  color: var(--color-accent-deep);
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.btn-icon {
  margin-right: 2px;
}
.session-panel {
  min-height: 70vh;
  overflow: hidden;
}
.session-panel :deep(.el-card__header) {
  padding: 14px 16px;
}
.kb-block {
  margin: 14px 14px 8px;
  padding: 12px;
  border-radius: 14px;
  background: linear-gradient(160deg, #f0f9ff 0%, #f8fafc 100%);
  border: 1px solid rgba(14, 165, 233, 0.14);
}
.kb-block__label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent-deep);
}
.kb-select {
  width: 100%;
}
.kb-block__hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--color-text-soft);
}
.session-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-soft);
}
.session-list {
  flex: 1;
  overflow: auto;
  padding: 4px 10px 12px;
  min-height: 180px;
}
.session-empty {
  margin: 28px 8px;
  text-align: center;
  color: var(--color-text-soft);
}
.session-empty p {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
}
.session-empty span {
  font-size: 12px;
}
.session-panel .chat-session-item {
  gap: 10px;
  padding: 10px 10px;
  margin-bottom: 6px;
  border: 1px solid transparent;
  border-radius: 12px;
}
.session-panel .chat-session-item:hover {
  background: #f8fafc;
  border-color: var(--color-border);
}
.session-panel .chat-session-item.active {
  background: var(--color-accent-soft);
  border-color: rgba(14, 165, 233, 0.22);
  border-left: 1px solid rgba(14, 165, 233, 0.22);
  padding-left: 10px;
  box-shadow: inset 3px 0 0 #0ea5e9;
}
.session-icon {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: #e2e8f0;
  position: relative;
}
.session-icon::after {
  content: '';
  position: absolute;
  inset: 8px 7px 9px;
  border-radius: 4px;
  border: 1.5px solid #64748b;
  border-bottom-width: 3px;
}
.draft-icon {
  background: linear-gradient(145deg, #7dd3fc, #0284c7);
}
.draft-icon::after {
  border-color: rgba(255, 255, 255, 0.85);
}
.session-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.session-panel .chat-session-item .title {
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.35;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}
.session-panel .chat-session-item .sub {
  font-size: 11px;
  color: var(--color-text-soft);
}
.session-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-soft);
  cursor: pointer;
  opacity: 0.5;
}
.session-more:hover {
  background: rgba(15, 23, 42, 0.06);
  color: var(--color-text);
  opacity: 1;
}
.session-panel .chat-session-item:hover .session-more,
.session-panel .chat-session-item.active .session-more {
  opacity: 1;
}
.session-pager {
  padding: 8px 12px 12px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
}
.panel,
.chat-panel {
  min-height: 70vh;
  display: flex;
  flex-direction: column;
}
.chat-panel :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chat-empty {
  position: relative;
  margin: 48px auto 24px;
  max-width: 420px;
  text-align: center;
  padding: 28px 20px;
}
.chat-empty__avatar {
  width: 108px;
  height: 108px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  animation: float-soft 3.2s ease-in-out infinite;
}
.mascot {
  width: 108px;
  height: 108px;
  filter: drop-shadow(0 14px 24px rgba(2, 132, 199, 0.28));
}
.chat-empty__title {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.03em;
}
.chat-empty__desc {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--color-text-muted);
}
.chat-empty__tips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}
.chat-empty__tips span {
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--color-accent-soft);
  color: var(--color-accent-deep);
  font-size: 12px;
  font-weight: 600;
}
@keyframes float-soft {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}
.sources {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 8px;
  max-width: 92%;
}
.sources summary {
  cursor: pointer;
  color: var(--color-accent-deep);
  margin-bottom: 4px;
}
.feedback {
  margin-top: 6px;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.composer {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}
.composer :deep(.el-textarea__inner) {
  border-radius: 14px;
  box-shadow: none;
  background: #f8fafc;
}
.send-row {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.composer-tip {
  font-size: 12px;
  color: var(--color-text-soft);
}
.send-actions {
  display: flex;
  gap: 8px;
}
</style>

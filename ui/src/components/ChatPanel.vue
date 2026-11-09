<template>
  <div class="bg-white flex flex-col" :class="compact ? 'h-full' : 'rounded-2xl shadow-card border border-slate-100 p-6'">
    <div v-if="!compact" class="flex items-center gap-2 mb-3">
      <h2 class="text-base font-bold text-slate-800">Chat</h2>
      <p class="text-xs text-slate-400 truncate flex-1 min-w-0">{{ scopeLabel }}</p>
      <button @click="railOpen = !railOpen" :aria-expanded="railOpen" class="md:hidden bg-slate-100 rounded-lg px-2.5 py-1.5 text-xs hover:bg-slate-200">Inbox</button>
      <span v-if="sessionId" class="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-mono shrink-0">{{ String(sessionId).slice(0, 8) }}</span>
    </div>
    <p v-if="compact" class="text-xs text-slate-400 truncate px-4 pt-1 -mb-1">{{ scopeLabel }}</p>
    <div class="grid gap-4 md:grid-cols-[280px_1fr]" :class="{ 'md:grid-cols-1': compact }">
      <aside v-if="!compact" v-show="railOpen" aria-label="Chat history" class="border border-slate-200 rounded-xl flex flex-col min-h-0">
        <div class="p-3 border-b border-slate-100">
          <p class="text-sm font-semibold text-slate-700">Inbox <span class="text-xs font-normal text-slate-400">({{ historySessions.length }})</span></p>
          <div class="relative mt-2">
            <input v-model="historyQuery" placeholder="Search conversations…" aria-label="Search conversations" class="w-full border border-slate-200 rounded-lg px-3 py-1.5 pr-8 text-sm focus:border-indigo-500" />
            <button v-if="historyQuery" @click="historyQuery = ''" aria-label="Clear search" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
          </div>
          <button @click="newSession" class="mt-2 w-full bg-indigo-600 text-white rounded-lg px-3 py-2 text-sm font-medium hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">+ New chat</button>
        </div>
        <div class="p-2 overflow-y-auto scroll-slim max-h-[40vh] md:max-h-[60vh]">
          <p v-if="historyLoading" class="text-sm text-slate-400 px-2 py-1">Loading…</p>
          <p v-else-if="!filteredSessions.length" class="text-sm text-slate-400 px-2 py-1">{{ historyQuery ? 'No matches.' : 'No conversations yet.' }}</p>
          <ul role="listbox" aria-label="Conversations" v-else class="space-y-1" @keydown="onListKey">
            <li>
              <button @click="backToLive" :aria-current="viewingSid ? undefined : 'true'" class="w-full text-left px-3 py-2 rounded-lg border-l-2 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 text-sm" :class="!viewingSid ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-transparent text-slate-700'">
                <span class="font-medium">Live chat</span><span v-if="sessionId" class="block text-xs text-slate-400 font-mono">{{ String(sessionId).slice(0, 8) }}</span>
              </button>
            </li>
            <li v-for="s in filteredSessions" :key="s.session_id">
              <button @click="openHistory(s.session_id)" :aria-current="viewingSid === s.session_id ? 'true' : undefined" class="w-full text-left px-3 py-2 rounded-lg border-l-2 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 text-sm" :class="viewingSid === s.session_id ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-transparent text-slate-700'">
                <span class="flex justify-between gap-2"><span class="font-medium truncate">{{ sessionScope(s) }}</span><span class="text-[11px] text-slate-400 shrink-0">{{ relativeTime(s.last_active) }}</span></span>
                <span v-if="s.preview" class="block text-xs text-slate-400 truncate">{{ s.preview }}</span><span class="block text-[11px] text-slate-300">{{ s.count }} messages</span>
              </button>
            </li>
          </ul>
        </div>
      </aside>
      <div class="min-w-0 flex flex-col flex-1 min-h-0">
    <div class="flex items-center gap-2 px-4 py-2 border-b border-slate-100">
      <select ref="scopeSelect" v-model="accountId" aria-label="Account" :disabled="internal" class="flex-1 min-w-0 border border-slate-200 rounded-full px-3 py-1.5 text-xs bg-white focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400">
        <option value="">Account…</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <label class="flex items-center gap-1 text-xs text-slate-600 shrink-0">
        <input type="checkbox" v-model="internal" class="w-3.5 h-3.5 accent-indigo-600" /> internal
      </label>
      <button v-if="compact" @click="newSession" aria-label="New chat" class="shrink-0 grid place-items-center w-7 h-7 rounded-full hover:bg-slate-100 text-slate-500"><svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 3v14M3 10h14" stroke-linecap="round"/></svg></button>
    </div>
    <div v-if="viewingSid" class="mb-3 flex items-center justify-between bg-indigo-50 text-indigo-700 text-sm rounded-lg px-3 py-2">
      <span>Viewing history — read-only</span>
      <button @click="backToLive" class="font-medium underline">Back to live</button>
    </div>
    <div
      ref="thread"
      @scroll="onScroll"
      aria-live="polite"
      class="scroll-slim px-4 py-3 flex-1 min-h-0 overflow-y-auto space-y-3 bg-white"
      :class="{ 'h-[15rem]': compact, 'h-[50vh]': !compact }"
    >
      <div v-for="(m, i) in displayMessages" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
        <div class="max-w-[82%] min-w-0">
          <div
            :class="m.role === 'user' ? 'bg-indigo-600 text-white rounded-2xl rounded-br-md' : 'bg-slate-100 text-slate-800 rounded-2xl rounded-bl-md'"
            class="px-3.5 py-2 text-sm whitespace-pre-wrap break-words leading-relaxed"
          >
            {{ m.text }}
          </div>
          <div class="flex flex-wrap items-center gap-1.5 mt-1" :class="m.role === 'user' ? 'justify-end' : ''">
            <span class="text-[11px] text-slate-400">{{ m.time }}</span>
            <span v-if="m.escalated" class="text-[11px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-medium">escalated{{ m.department ? ` → ${m.department}` : '' }}</span>
            <span v-else-if="m.category" class="text-[11px] text-slate-400">{{ m.category }}</span>
          </div>
          <p v-if="m.notice" class="text-xs text-amber-600 mt-1">{{ m.notice }}</p>
        </div>
      </div>
      <div v-if="loading" class="flex gap-2.5 items-center" aria-live="polite">
        <span class="grid place-items-center w-7 h-7 rounded-full text-xs font-bold bg-violet-100 text-violet-700">S</span>
        <span class="flex gap-1 bg-white border border-slate-200 rounded-2xl rounded-tl-md px-3.5 py-3 shadow-sm">
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 150ms"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 300ms"></span>
        </span>
      </div>
      <div v-if="viewerLoading" class="h-full grid place-content-center text-center px-4">
        <p class="text-sm text-slate-500 font-medium">Loading history…</p>
      </div>
      <div v-else-if="!displayMessages.length && !loading" class="h-full grid place-content-center text-center px-4">
        <svg viewBox="0 0 48 48" class="w-12 h-12 mx-auto mb-3 text-indigo-300" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12a6 6 0 0 1 6-6h20a6 6 0 0 1 6 6v12a6 6 0 0 1-6 6H20l-9 8V12Z"/><circle cx="18" cy="18" r="1.5" fill="currentColor"/><circle cx="25" cy="18" r="1.5" fill="currentColor"/><circle cx="32" cy="18" r="1.5" fill="currentColor"/></svg>
        <p class="text-sm text-slate-500 font-medium">{{ viewingSid ? 'No messages in this session' : emptyTitle }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ viewingSid ? 'This session expired or is empty.' : emptyHint }}</p>
        <button v-if="!viewingSid && !internal.value && !accountId" @click="focusScope" class="mt-3 bg-indigo-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-indigo-700">Choose account</button>
      </div>
    </div>
    <form @submit.prevent="send" class="flex gap-2 items-end px-4 pb-3 pt-2 border-t border-slate-100 bg-white">
      <label id="composer-hint" class="sr-only">Type a question. Enter sends, Shift+Enter adds a new line.</label>
      <textarea
        v-model="question"
        placeholder="Type a message…"
        :disabled="loading || !!viewingSid"
        :aria-describedby="viewingSid ? 'readonly-hint' : 'composer-hint'"
        rows="1"
        class="border border-slate-200 rounded-full px-4 py-2.5 flex-1 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 resize-none"
        @keydown.enter.exact.prevent="send"
      />
      <button
        :disabled="loading || !!viewingSid || !question.trim()"
        :aria-label="loading ? 'Sending question' : 'Send question'"
        class="grid place-items-center w-10 h-10 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 shrink-0"
      >
        <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
        <svg v-else viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10h12M11 5l5 5-5 5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </form>
    <p v-if="viewingSid" id="readonly-hint" class="mt-2 text-xs text-slate-400">Read-only — select Live chat to send. <button @click="backToLive" class="underline font-medium">Go to Live chat</button></p>
    <p v-if="error" class="mt-2 text-sm text-red-600" role="alert">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { api, currentRole } from '../api.js'

const props = defineProps({ compact: { type: Boolean, default: false } })

const accounts = ref([])
const accountId = ref('')
const internal = ref(currentRole() !== 'staff')
const sessionId = ref(null)
const SESSION_KEY = 'chat_session'
let restoring = false

function saveSession() {
  try {
    if (sessionId.value) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({
        sid: sessionId.value, accountId: accountId.value, internal: internal.value
      }))
    } else {
      localStorage.removeItem(SESSION_KEY)
    }
  } catch { /* private mode etc. — session just won't survive reload */ }
}

function restoreSession() {
  try {
    const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null')
    if (!s?.sid) return
    restoring = true
    internal.value = !!s.internal
    accountId.value = s.accountId || ''
    nextTick(() => {
      sessionId.value = s.sid
      restoring = false
      // rebuild the visible thread — a bare session id after reload looks
      // like the session was cleared
      api.getSessionHistory(s.sid)
        .then(({ data }) => {
          // never clobber messages the user already sent in the meantime
          if (sessionId.value !== s.sid || messages.value.length) return
          messages.value = (data.turns || []).map((t) => ({
            role: t.role,
            text: t.content,
            time: t.ts ? new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
            escalated: !!t.escalated,
            department: t.department || null,
            category: t.escalated ? null : t.category,
          }))
        })
        .catch(() => { /* history unavailable — stay on empty thread */ })
    })
  } catch { /* corrupt entry — start fresh */ }
}
const question = ref('')
const railOpen = ref(true)
const scopeSelect = ref(null)
const messages = ref([])
const viewingSid = ref(null) // in-memory only, never persisted to SESSION_KEY
const viewerMessages = ref([])
const historyQuery = ref('')
const historySessions = ref([])
const historyLoading = ref(false)
const viewerLoading = ref(false)
const displayMessages = computed(() => viewingSid.value ? viewerMessages.value : messages.value)
const filteredSessions = computed(() => {
  const q = historyQuery.value.trim().toLowerCase()
  if (!q) return historySessions.value
  return historySessions.value.filter((s) => (s.preview || '').toLowerCase().includes(q) || sessionTitle(s).toLowerCase().includes(q))
})
const error = ref('')
const loading = ref(false)
const thread = ref(null)
const stick = ref(true) // follow new messages only while scrolled near the bottom

const scopeLabel = computed(() => {
  if (internal.value) return 'Scope: internal documents'
  const a = accounts.value.find((x) => x.id === accountId.value)
  return a ? `Scope: ${a.name}` : 'Scope: no account selected'
})

const emptyTitle = computed(() => {
  if (internal.value) return 'Ask about internal knowledge'
  const a = accounts.value.find((x) => x.id === accountId.value)
  return a ? `Ask about ${a.name}` : 'Pick a scope to start'
})

const emptyHint = computed(() => {
  if (internal.value) return 'Answers come from internal documents only — no account content.'
  return accountId.value ? 'Answers are scoped to this account only.' : 'Select an account above, or check internal.'
})

function focusScope() {
  scopeSelect.value?.focus()
}
function onListKey(e) {
  if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
  const btns = [...e.currentTarget.querySelectorAll('button:not([disabled])')]
  if (!btns.length) return
  e.preventDefault()
  const i = btns.indexOf(document.activeElement)
  const next = e.key === 'ArrowDown' ? Math.min(i + 1, btns.length - 1) : Math.max(i - 1, 0)
  ;(btns[next] || btns[0]).focus()
}
function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function onScroll() {
  const el = thread.value
  if (!el) return
  stick.value = el.scrollHeight - el.scrollTop - el.clientHeight < 48
}

async function scrollDown() {
  if (!stick.value) return
  await nextTick()
  thread.value?.scrollTo({ top: thread.value.scrollHeight })
}

function newSession() {
  viewingSid.value = null
  viewerMessages.value = []
  viewerLoading.value = false
  sessionId.value = null
  saveSession()
  messages.value = []
  error.value = ''
  question.value = ''
}

function sessionScope(s) {
  return s.account_id ? (accounts.value.find((a) => a.id === s.account_id)?.name || 'Account') : 'Internal'
}
function relativeTime(ts) {
  if (!ts) return ''
  const diff = Date.now() - ts * 1000
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'now'
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}d`
  return new Date(ts * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' })
}
function sessionTitle(s) {
  return `${sessionScope(s)} · ${s.last_active ? new Date(s.last_active * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : s.session_id}`
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const { data } = await api.listSessions({ limit: 20 })
    historySessions.value = Array.isArray(data) ? data : (data.items || [])
  } catch { historySessions.value = [] } finally { historyLoading.value = false }
}

async function openHistory(sid) {
  viewingSid.value = sid
  viewerMessages.value = []
  viewerLoading.value = true
  try {
    const { data } = await api.getSessionHistory(sid)
    if (viewingSid.value !== sid) return // user navigated away mid-fetch
    viewerMessages.value = (data.turns || []).map((t) => ({
      role: t.role, text: t.content,
      time: t.ts ? new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
      escalated: !!t.escalated, department: t.department || null,
      category: t.escalated ? null : t.category,
    }))
  } catch { viewerMessages.value = []; error.value = 'Could not load history session.' } finally { if (viewingSid.value === sid) viewerLoading.value = false }
}

function backToLive() {
  viewingSid.value = null
  viewerMessages.value = []
  viewerLoading.value = false
  error.value = ''
}

async function send() {
  error.value = ''
  if (!accountId.value && !internal.value) {
    error.value = 'Select an account or check internal.'
    return
  }
  const q = question.value.trim()
  if (!q) return
  question.value = ''
  stick.value = true
  messages.value.push({ role: 'user', text: q, time: nowLabel() })
  loading.value = true
  scrollDown()
  try {
    const { data } = await api.chat({
      session_id: sessionId.value,
      account_id: internal.value ? null : accountId.value,
      question: q
    })
    sessionId.value = data.session_id
    saveSession()
    viewingSid.value = null
    viewerMessages.value = []
    loadHistory()
    const notices = []
    if (data.session_expired) notices.push('Previous session context expired (30-min window).')
    messages.value.push({
      role: 'assistant',
      text: data.answer,
      time: nowLabel(),
      escalated: data.escalated,
      department: data.department,
      category: data.escalated ? null : data.category,
      notice: notices.join(' ')
    })
  } catch (e) {
    // restore the optimistic bubble + text so the message is not lost
    if (messages.value.at(-1)?.role === 'user') messages.value.pop()
    question.value = q
    error.value = e.response?.data?.detail || 'Chat failed. Your message was restored — press Send to retry.'
  } finally {
    loading.value = false
    scrollDown()
  }
}

onMounted(async () => {
  restoreSession()
  loadHistory()
  try {
    const { data } = await api.listAccounts()
    accounts.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load accounts.'
  }
})

// scope switch invalidates the bound session and the displayed thread
watch([accountId, internal], () => {
  viewingSid.value = null
  viewerMessages.value = []
  viewerLoading.value = false
  if (restoring) return  // restoring a persisted session, not a user switch
  sessionId.value = null
  saveSession()
  messages.value = []
})
</script>

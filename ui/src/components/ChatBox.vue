<template>
  <div class="bg-white flex flex-col h-full">
    <p class="text-xs text-slate-400 truncate px-4 pt-2">{{ scopeLabel }}</p>
    <div class="min-w-0 flex flex-col flex-1 min-h-0">
    <div class="flex items-center gap-2 px-4 py-2 border-b border-slate-100">
      <select ref="scopeSelect" v-model="accountId" aria-label="Account" :disabled="internal" class="flex-1 min-w-0 border border-slate-200 rounded-full px-3 py-1.5 text-xs bg-white focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400">
        <option value="">Account…</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <label class="flex items-center gap-1 text-xs text-slate-600 shrink-0">
        <input type="checkbox" v-model="internal" class="w-3.5 h-3.5 accent-indigo-600" /> internal
      </label>
      <button @click="newSession" aria-label="New chat" class="shrink-0 grid place-items-center w-7 h-7 rounded-full hover:bg-slate-100 text-slate-500"><svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 3v14M3 10h14" stroke-linecap="round"/></svg></button>
    </div>
    <div
      ref="thread"
      @scroll="onScroll"
      aria-live="polite"
      class="scroll-slim px-4 py-3 flex-1 min-h-0 overflow-y-auto space-y-3 bg-white"
    >
      <div v-for="(m, i) in messages" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
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
      <div v-if="loading" class="flex items-center" aria-live="polite">
        <span class="flex gap-1 bg-slate-100 rounded-2xl rounded-bl-md px-3.5 py-3">
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 150ms"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 300ms"></span>
        </span>
      </div>
      <div v-if="!messages.length && !loading" class="h-full grid place-content-center text-center px-4">
        <svg viewBox="0 0 48 48" class="w-12 h-12 mx-auto mb-3 text-indigo-300" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12a6 6 0 0 1 6-6h20a6 6 0 0 1 6 6v12a6 6 0 0 1-6 6H20l-9 8V12Z"/><circle cx="18" cy="18" r="1.5" fill="currentColor"/><circle cx="25" cy="18" r="1.5" fill="currentColor"/><circle cx="32" cy="18" r="1.5" fill="currentColor"/></svg>
        <p class="text-sm text-slate-500 font-medium">{{ emptyTitle }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ emptyHint }}</p>
        <button v-if="!internal && !accountId" @click="focusScope" class="mt-3 bg-indigo-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-indigo-700">Choose account</button>
      </div>
    </div>
    <form @submit.prevent="send" class="flex gap-2 items-end px-4 pb-3 pt-2 border-t border-slate-100 bg-white">
      <label id="composer-hint" class="sr-only">Type a question. Enter sends, Shift+Enter adds a new line.</label>
      <textarea
        v-model="question"
        placeholder="Type a message…"
        :disabled="loading"
        aria-describedby="composer-hint"
        rows="1"
        class="border border-slate-200 rounded-full px-4 py-2.5 flex-1 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 resize-none"
        @keydown.enter.exact.prevent="send"
      />
      <button
        :disabled="loading || !question.trim()"
        :aria-label="loading ? 'Sending question' : 'Send question'"
        class="grid place-items-center w-10 h-10 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 shrink-0"
      >
        <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
        <svg v-else viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10h12M11 5l5 5-5 5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </form>
    <p v-if="error" class="px-4 pb-2 text-sm text-red-600" role="alert">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { api, currentRole } from '../api.js'

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
  } catch { }
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
      api.getSessionHistory(s.sid)
        .then(({ data }) => {
          if (sessionId.value !== s.sid || messages.value.length) return
          messages.value = (data.turns || []).map((t) => ({
            role: t.role,
            text: t.content,
            time: t.ts ? new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
            escalated: !!t.escalated,
            department: t.department || null,
            category: t.escalated ? null : t.category,
          }))
          stick.value = true
          scrollDown(true)
        })
        .catch(() => { })
    })
  } catch { }
}
const question = ref('')
const scopeSelect = ref(null)
const messages = ref([])
const error = ref('')
const loading = ref(false)
const thread = ref(null)
const stick = ref(true)

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
function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function onScroll() {
  const el = thread.value
  if (!el) return
  stick.value = el.scrollHeight - el.scrollTop - el.clientHeight < 48
}

async function scrollDown(force = false) {
  if (!force && !stick.value) return
  await nextTick()
  thread.value?.scrollTo({ top: thread.value.scrollHeight })
}

function newSession() {
  sessionId.value = null
  saveSession()
  messages.value = []
  error.value = ''
  question.value = ''
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
  stick.value = true
  scrollDown(true)
  try {
    const { data } = await api.listAccounts()
    accounts.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load accounts.'
  }
})

watch([accountId, internal], () => {
  if (restoring) return
  sessionId.value = null
  saveSession()
  messages.value = []
})
</script>

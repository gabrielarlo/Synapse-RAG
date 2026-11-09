<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-slate-800">Chat</h2>
        <p class="text-xs text-slate-400 mt-0.5">{{ scopeLabel }}</p>
      </div>
      <span v-if="sessionId" class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-mono shrink-0">session {{ String(sessionId).slice(0, 8) }}</span>
    </div>
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <select v-model="accountId" aria-label="Account" class="border border-slate-200 rounded-lg px-3 py-2 bg-white focus:border-indigo-500">
        <option value="">Select account</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <label class="flex items-center gap-1.5 text-sm text-slate-600">
        <input type="checkbox" v-model="internal" class="w-4 h-4 accent-indigo-600" /> internal
      </label>
      <button @click="newSession" :disabled="!messages.length && !sessionId" class="bg-slate-100 rounded-lg px-4 py-2 text-sm hover:bg-slate-200 disabled:opacity-50 transition-colors">New session</button>
    </div>
    <div
      ref="thread"
      @scroll="onScroll"
      aria-live="polite"
      class="scroll-slim border border-slate-200 rounded-xl p-4 h-[60vh] min-h-[20rem] max-h-[42rem] overflow-y-auto mb-4 space-y-4 bg-gradient-to-b from-slate-50 to-white"
    >
      <div v-for="(m, i) in messages" :key="i" class="flex gap-2.5" :class="m.role === 'user' ? 'flex-row-reverse' : ''">
        <span
          class="grid place-items-center w-7 h-7 rounded-full text-xs font-bold shrink-0"
          :class="m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-violet-100 text-violet-700'"
          aria-hidden="true"
        >{{ m.role === 'user' ? 'Y' : 'S' }}</span>
        <div class="max-w-[80%] min-w-0">
          <div
            :class="m.role === 'user' ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-md' : 'bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-md shadow-sm'"
            class="px-3.5 py-2.5 text-sm whitespace-pre-wrap break-words"
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
      <div v-if="!messages.length && !loading" class="h-full grid place-content-center text-center px-4">
        <svg viewBox="0 0 48 48" class="w-12 h-12 mx-auto mb-3 text-indigo-300" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12a6 6 0 0 1 6-6h20a6 6 0 0 1 6 6v12a6 6 0 0 1-6 6H20l-9 8V12Z"/><circle cx="18" cy="18" r="1.5" fill="currentColor"/><circle cx="25" cy="18" r="1.5" fill="currentColor"/><circle cx="32" cy="18" r="1.5" fill="currentColor"/></svg>
        <p class="text-sm text-slate-500 font-medium">{{ emptyTitle }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ emptyHint }}</p>
      </div>
    </div>
    <form @submit.prevent="send" class="flex gap-2">
      <input
        v-model="question"
        placeholder="Type a question…"
        aria-label="Question"
        autocomplete="off"
        :disabled="loading"
        class="border border-slate-200 rounded-lg px-3 py-2 flex-1 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400"
        required
      />
      <button
        :disabled="loading || !question.trim()"
        :aria-label="loading ? 'Sending question' : 'Send question'"
        class="bg-indigo-600 text-white rounded-lg px-5 py-2 hover:bg-indigo-700 disabled:opacity-50 transition-colors font-medium min-w-[5rem]"
      >
        {{ loading ? '…' : 'Send' }}
      </button>
    </form>
    <p v-if="error" class="mt-2 text-sm text-red-600" role="alert">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { api, currentRole } from '../api.js'

const accounts = ref([])
const accountId = ref('')
const internal = ref(currentRole() !== 'staff')
const sessionId = ref(null)
const question = ref('')
const messages = ref([])
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
  return accountId.value ? 'Answers are scoped to this account plus internal documents.' : 'Select an account above, or check internal.'
})

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
  sessionId.value = null
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
  try {
    const { data } = await api.listAccounts()
    accounts.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load accounts.'
  }
})

// scope switch invalidates the bound session and the displayed thread
watch([accountId, internal], () => {
  sessionId.value = null
  messages.value = []
})
</script>

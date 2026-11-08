<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold text-slate-800">Chat</h2>
      <span v-if="sessionId" class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-mono">session {{ String(sessionId).slice(0, 8) }}</span>
    </div>
    <div class="flex gap-2 mb-4">
      <select v-model="accountId" aria-label="Account" class="border border-slate-200 rounded-lg px-3 py-2 bg-white focus:border-indigo-500">
        <option value="">Select account</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <button @click="newSession" class="bg-slate-100 rounded-lg px-4 py-2 text-sm hover:bg-slate-200 transition-colors">New session</button>
    </div>
    <div ref="thread" class="scroll-slim border border-slate-200 rounded-xl p-4 h-80 overflow-y-auto mb-4 space-y-4 bg-gradient-to-b from-slate-50 to-white">
      <div v-for="(m, i) in messages" :key="i" class="flex gap-2.5" :class="m.role === 'user' ? 'flex-row-reverse' : ''">
        <span
          class="grid place-items-center w-7 h-7 rounded-full text-xs font-bold shrink-0"
          :class="m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-violet-100 text-violet-700'"
          aria-hidden="true"
        >{{ m.role === 'user' ? 'Y' : 'S' }}</span>
        <div class="max-w-[80%]">
          <div
            :class="m.role === 'user' ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-md' : 'bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-md shadow-sm'"
            class="px-3.5 py-2.5 text-sm whitespace-pre-wrap"
          >
            {{ m.text }}
          </div>
          <div v-if="m.notice" class="text-xs text-amber-600 mt-1">{{ m.notice }}</div>
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
      <div v-if="!messages.length && !loading" class="text-center py-8">
        <svg viewBox="0 0 48 48" class="w-12 h-12 mx-auto mb-3 text-indigo-300" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12a6 6 0 0 1 6-6h20a6 6 0 0 1 6 6v12a6 6 0 0 1-6 6H20l-9 8V12Z"/><circle cx="18" cy="18" r="1.5" fill="currentColor"/><circle cx="25" cy="18" r="1.5" fill="currentColor"/><circle cx="32" cy="18" r="1.5" fill="currentColor"/></svg>
        <p class="text-sm text-slate-400">Ask a question scoped to the selected account.</p>
      </div>
    </div>
    <form @submit.prevent="send" class="flex gap-2">
      <input v-model="question" placeholder="Type a question…" aria-label="Question" class="border border-slate-200 rounded-lg px-3 py-2 flex-1 focus:border-indigo-500" required />
      <button :disabled="loading" class="bg-indigo-600 text-white rounded-lg px-5 py-2 hover:bg-indigo-700 disabled:opacity-50 transition-colors font-medium">
        {{ loading ? '…' : 'Send' }}
      </button>
    </form>
    <p v-if="error" class="mt-2 text-sm text-red-600" role="alert">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { api } from '../api.js'

const accounts = ref([])
const accountId = ref('')
const sessionId = ref(null)
const question = ref('')
const messages = ref([])
const error = ref('')
const loading = ref(false)
const thread = ref(null)

async function scrollDown() {
  await nextTick()
  thread.value?.scrollTo({ top: thread.value.scrollHeight })
}

function newSession() {
  sessionId.value = null
}

async function send() {
  error.value = ''
  if (!accountId.value) {
    error.value = 'Select an account first.'
    return
  }
  const q = question.value
  question.value = ''
  messages.value.push({ role: 'user', text: q })
  loading.value = true
  scrollDown()
  try {
    const { data } = await api.chat({
      session_id: sessionId.value,
      account_id: accountId.value,
      question: q
    })
    sessionId.value = data.session_id
    const notices = []
    if (data.session_expired) notices.push('Previous session context expired (30-min window).')
    if (data.escalated) notices.push(`Escalated${data.department ? ` → ${data.department}` : ''}.`)
    messages.value.push({
      role: 'assistant',
      text: data.answer,
      notice: notices.join(' ') || (data.category ? `Category: ${data.category}` : '')
    })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Chat failed.'
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
</script>

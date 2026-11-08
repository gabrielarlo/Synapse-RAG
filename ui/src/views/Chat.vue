<template>
  <div class="bg-white rounded shadow p-6">
    <h2 class="text-xl font-bold mb-4 text-gray-800">Chat</h2>
    <div class="flex gap-2 mb-4">
      <select v-model="accountId" class="border rounded px-3 py-2">
        <option value="">Select account</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <button @click="newSession" class="bg-gray-200 rounded px-4 py-2 text-sm hover:bg-gray-300">New session</button>
    </div>
    <div class="border rounded p-3 h-80 overflow-y-auto mb-4 space-y-3 bg-gray-50">
      <div v-for="(m, i) in messages" :key="i" :class="m.role === 'user' ? 'text-right' : 'text-left'">
        <div
          :class="m.role === 'user' ? 'inline-block bg-blue-600 text-white' : 'inline-block bg-white border'"
          class="px-3 py-2 rounded text-sm max-w-full whitespace-pre-wrap"
        >
          {{ m.text }}
        </div>
        <div v-if="m.notice" class="text-xs text-amber-600 mt-1">{{ m.notice }}</div>
      </div>
      <p v-if="!messages.length" class="text-sm text-gray-400">Ask a question scoped to the selected account.</p>
    </div>
    <form @submit.prevent="send" class="flex gap-2">
      <input v-model="question" placeholder="Type a question…" class="border rounded px-3 py-2 flex-1" required />
      <button :disabled="loading" class="bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50">
        {{ loading ? '…' : 'Send' }}
      </button>
    </form>
    <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const accounts = ref([])
const accountId = ref('')
const sessionId = ref(null)
const question = ref('')
const messages = ref([])
const error = ref('')
const loading = ref(false)

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

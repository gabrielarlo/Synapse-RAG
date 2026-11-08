<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold text-slate-800">Documents</h2>
      <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">{{ docs.length }} file{{ docs.length === 1 ? '' : 's' }}</span>
    </div>
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <select v-model="accountId" aria-label="Account" class="border border-slate-200 rounded-lg px-3 py-2 bg-white focus:border-indigo-500">
        <option value="">Select account</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <label class="flex items-center gap-1.5 text-sm text-slate-600">
        <input type="checkbox" v-model="internal" class="w-4 h-4 accent-indigo-600" /> internal
      </label>
      <input type="file" @change="onFile" aria-label="File" class="text-sm text-slate-600 file:mr-2 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200" />
      <button @click="upload" :disabled="!file" class="bg-indigo-600 text-white rounded-lg px-4 py-2 hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium">
        Upload
      </button>
      <button @click="load" class="bg-slate-100 rounded-lg px-4 py-2 hover:bg-slate-200 transition-colors text-sm">Refresh</button>
    </div>
    <p v-if="error" class="text-sm text-red-600 mb-2" role="alert">{{ error }}</p>
    <p v-if="msg" class="text-sm text-green-600 mb-2" role="status">{{ msg }}</p>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-slate-400 border-b border-slate-100"><th class="py-2 font-medium">File</th><th class="font-medium">Scope</th><th class="font-medium">Status</th></tr></thead>
      <tbody>
        <tr v-for="d in docs" :key="d.id" class="border-b border-slate-100 last:border-0 hover:bg-slate-50/70 transition-colors">
          <td class="py-2.5 font-medium text-slate-700">{{ d.filename }}</td>
          <td class="text-slate-500">{{ d.scope || (d.account_id || 'internal') }}</td>
          <td><span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="d.status === 'ready' ? 'bg-emerald-50 text-emerald-700' : d.status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'">{{ d.status }}</span></td>
        </tr>
      </tbody>
    </table>
    <p v-if="!docs.length" class="text-sm text-slate-400 mt-3">No documents.</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const accounts = ref([])
const docs = ref([])
const accountId = ref('')
const internal = ref(false)
const file = ref(null)
const error = ref('')
const msg = ref('')

function scopeParams() {
  return internal.value ? { internal: true } : accountId.value ? { account_id: accountId.value } : null
}

async function load() {
  error.value = ''
  const params = scopeParams()
  if (!params) {
    error.value = 'Select an account or internal.'
    return
  }
  try {
    const { data } = await api.listDocuments(params)
    docs.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load documents.'
  }
}

function onFile(e) {
  file.value = e.target.files[0] || null
}

async function upload() {
  error.value = ''
  msg.value = ''
  const params = scopeParams()
  if (!params) {
    error.value = 'Select an account or internal.'
    return
  }
  try {
    const { data } = await api.uploadDocument(file.value, params)
    msg.value = `Queued (job ${data.job_id}, ${data.status}).`
    file.value = null
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Upload failed.'
  }
}

onMounted(async () => {
  try {
    const { data } = await api.listAccounts()
    accounts.value = data
  } catch { /* scoped users may still chat; ignore */ }
})
</script>

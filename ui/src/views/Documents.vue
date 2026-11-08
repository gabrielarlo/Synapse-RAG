<template>
  <div class="bg-white rounded shadow p-6">
    <h2 class="text-xl font-bold mb-4 text-gray-800">Documents</h2>
    <div class="flex flex-wrap gap-2 mb-4">
      <select v-model="accountId" class="border rounded px-3 py-2">
        <option value="">Select account</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <label class="flex items-center gap-1 text-sm">
        <input type="checkbox" v-model="internal" /> internal
      </label>
      <input type="file" @change="onFile" class="text-sm" />
      <button @click="upload" :disabled="!file" class="bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50">
        Upload
      </button>
      <button @click="load" class="bg-gray-200 rounded px-4 py-2 hover:bg-gray-300">Refresh</button>
    </div>
    <p v-if="error" class="text-sm text-red-600 mb-2">{{ error }}</p>
    <p v-if="msg" class="text-sm text-green-600 mb-2">{{ msg }}</p>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-gray-500 border-b"><th class="py-2">File</th><th>Scope</th><th>Status</th></tr></thead>
      <tbody>
        <tr v-for="d in docs" :key="d.id" class="border-b">
          <td class="py-2">{{ d.filename }}</td>
          <td>{{ d.scope || (d.account_id || 'internal') }}</td>
          <td><span class="px-2 py-0.5 rounded text-xs bg-gray-100">{{ d.status }}</span></td>
        </tr>
      </tbody>
    </table>
    <p v-if="!docs.length" class="text-sm text-gray-500 mt-2">No documents.</p>
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

<template>
  <div class="bg-white rounded shadow p-6">
    <h2 class="text-xl font-bold mb-2 text-gray-800">Audit trail</h2>
    <p class="text-sm text-gray-500 mb-4">
      Admin only. Tip: in Chat, admins can prefix a question with <code class="bg-gray-100 px-1 rounded">audit: </code>
      (e.g. <code class="bg-gray-100 px-1 rounded">audit: uploads per day</code>).
    </p>
    <div class="flex flex-wrap gap-2 mb-4">
      <input v-model="filters.action" placeholder="Action filter" class="border rounded px-3 py-2 text-sm" />
      <input v-model="filters.account_id" placeholder="Account ID" class="border rounded px-3 py-2 text-sm" />
      <input v-model.number="filters.limit" type="number" min="1" class="border rounded px-3 py-2 text-sm w-28" />
      <button @click="load" class="bg-blue-600 text-white rounded px-4 py-2 text-sm hover:bg-blue-700">Load</button>
    </div>
    <p v-if="error" class="text-sm text-red-600 mb-2">{{ error }}</p>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-gray-500 border-b"><th class="py-2">Time</th><th>Actor</th><th>Action</th><th>Scope</th><th>Detail</th></tr></thead>
      <tbody>
        <tr v-for="(e, i) in events" :key="i" class="border-b">
          <td class="py-2">{{ e.ts }}</td>
          <td>{{ e.actor }}</td>
          <td>{{ e.action }}</td>
          <td>{{ e.scope }}</td>
          <td class="max-w-xs truncate">{{ e.detail }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!events.length && !error" class="text-sm text-gray-500 mt-2">No events.</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const events = ref([])
const error = ref('')
const filters = ref({ limit: 100, action: '', account_id: '' })

async function load() {
  error.value = ''
  const params = { limit: filters.value.limit || 100 }
  if (filters.value.action) params.action = filters.value.action
  if (filters.value.account_id) params.account_id = filters.value.account_id
  try {
    const { data } = await api.listAudit(params)
    events.value = data
  } catch (e) {
    error.value =
      e.response?.status === 403
        ? 'Forbidden: admin only.'
        : e.response?.data?.detail || 'Failed to load audit trail.'
  }
}

onMounted(load)
</script>

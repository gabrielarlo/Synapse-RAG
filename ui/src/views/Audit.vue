<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-xl font-bold text-slate-800">Audit trail</h2>
      <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">{{ events.length }} event{{ events.length === 1 ? '' : 's' }}</span>
    </div>
    <p class="text-sm text-slate-500 mb-4">
      Admin only. Tip: in Chat, admins can prefix a question with <code class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">audit: </code>
      (e.g. <code class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">audit: uploads per day</code>).
    </p>
    <div class="flex flex-wrap gap-2 mb-4">
      <BaseInput v-model="filters.action" placeholder="Action filter" aria-label="Action filter" class="text-sm" />
      <BaseInput v-model="filters.account_id" placeholder="Account ID" aria-label="Account ID" class="text-sm" />
      <BaseInput v-model.number="filters.limit" type="number" min="1" aria-label="Limit" class="text-sm w-28" />
      <button @click="load" class="bg-indigo-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-indigo-700 transition-colors font-medium">Load</button>
    </div>
    <p v-if="error" class="text-sm text-red-600 mb-2" role="alert">{{ error }}</p>
    <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead><tr class="text-left text-slate-400 border-b border-slate-100"><th class="py-2 font-medium">Time</th><th class="font-medium">Actor</th><th class="font-medium">Action</th><th class="font-medium">Scope</th><th class="font-medium">Detail</th></tr></thead>
      <tbody>
        <tr v-for="(e, i) in events" :key="i" class="border-b border-slate-100 last:border-0 hover:bg-slate-50/70 transition-colors">
          <td class="py-2.5 text-slate-500 whitespace-nowrap">{{ e.ts }}</td>
          <td class="text-slate-700">{{ e.actor }}</td>
          <td><span class="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">{{ e.action }}</span></td>
          <td class="text-slate-500">{{ e.scope }}</td>
          <td class="max-w-xs truncate text-slate-500">{{ e.detail }}</td>
        </tr>
      </tbody>
    </table>
    </div>
    <p v-if="!events.length && !error" class="text-sm text-slate-400 mt-3">No events match these filters.</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

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

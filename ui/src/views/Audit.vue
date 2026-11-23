<template>
  <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-100 dark:border-slate-700 p-4 sm:p-6 flex flex-col gap-4">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100">Audit trail</h2>
        <p class="text-xs text-slate-400 mt-0.5">Admin-only activity log. Filter by action or account and inspect recent events.</p>
      </div>
      <span class="shrink-0 text-xs px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-medium tabular-nums" aria-live="polite">{{ events.length }} event{{ events.length === 1 ? '' : 's' }}</span>
    </div>

    <div class="rounded-xl border border-indigo-100 dark:border-white/10 bg-indigo-50/60 dark:bg-indigo-500/10 px-3 py-2.5 text-xs text-indigo-900 dark:text-indigo-200 flex gap-2">
      <span class="shrink-0 mt-0.5" aria-hidden="true">💡</span>
      <p class="min-w-0 leading-relaxed">In Chat, admins can prefix a question with <code class="bg-white dark:bg-slate-900 border border-indigo-100 dark:border-white/10 px-1.5 py-0.5 rounded font-mono text-indigo-700 dark:text-indigo-300">audit: </code> e.g. <code class="bg-white dark:bg-slate-900 border border-indigo-100 dark:border-white/10 px-1.5 py-0.5 rounded font-mono text-indigo-700 dark:text-indigo-300">audit: uploads per day</code>.</p>
    </div>

    <div class="flex flex-col gap-2">
      <div class="flex flex-col sm:flex-row gap-2">
        <label for="audit-action" class="sr-only">Action filter</label>
        <BaseInput id="audit-action" v-model="filters.action" placeholder="Action filter — e.g. login, create_account" aria-label="Action filter" class="flex-1 min-w-0" />
        <label for="audit-account" class="sr-only">Account filter</label>
        <select id="audit-account" v-model="filters.account_id" aria-label="Account filter" class="flex-1 min-w-0 sm:max-w-[14rem] border border-slate-200 dark:border-slate-700 rounded-full px-4 py-2.5 bg-white dark:bg-slate-900 text-sm focus:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
          <option value="">All accounts</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <label for="audit-limit" class="sr-only">Limit</label>
        <BaseInput id="audit-limit" v-model.number="filters.limit" type="number" :min="1" :max="200" aria-label="Limit" class="w-full sm:w-28" />
      </div>
      <div class="flex flex-col sm:flex-row gap-2">
        <button @click="load" :disabled="loading" class="flex-1 sm:flex-none min-h-11 rounded-full bg-indigo-600 text-white px-5 py-2.5 hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
          <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
          {{ loading ? 'Loading…' : 'Load' }}
        </button>
        <button @click="clearFilters" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-sm font-medium text-slate-700 dark:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">Clear</button>
        <span class="hidden sm:inline-flex items-center text-xs text-slate-400 ml-1">Limit 1–200</span>
      </div>
      <p class="text-xs text-slate-400">Filters are server-side. Leave blank to see the most recent {{ filters.limit || 100 }} events.</p>
    </div>

    <div v-if="error" class="flex items-start gap-2 rounded-xl px-3 py-2.5 text-sm" :class="isForbidden ? 'bg-amber-50 dark:bg-amber-500/15 border border-amber-100 dark:border-white/10 text-amber-800 dark:text-amber-200' : 'bg-red-50 dark:bg-red-500/15 border border-red-100 dark:border-white/10 text-red-700 dark:text-red-300'" role="alert">
      <span class="shrink-0 mt-0.5" aria-hidden="true">{{ isForbidden ? '🔒' : '⚠' }}</span>
      <div class="flex-1 min-w-0">
        <p class="break-words">{{ error }}</p>
        <p v-if="isForbidden" class="text-xs opacity-80 mt-1">Switch to an admin account or contact an admin. Staff and unauthenticated users cannot view the audit trail.</p>
      </div>
      <button @click="error=''" aria-label="Dismiss error" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-black/5 dark:hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">✕</button>
    </div>

    <div v-if="loading && !events.length" class="space-y-2">
      <div v-for="i in 5" :key="i" class="animate-pulse border border-slate-100 dark:border-slate-700 rounded-xl p-3 flex gap-3">
        <div class="w-20 h-3 bg-slate-100 dark:bg-slate-800 rounded"></div>
        <div class="w-16 h-3 bg-slate-100 dark:bg-slate-800 rounded"></div>
        <div class="w-24 h-3 bg-slate-100 dark:bg-slate-800 rounded hidden sm:block"></div>
        <div class="flex-1 h-3 bg-slate-100 dark:bg-slate-800 rounded"></div>
      </div>
    </div>

    <template v-if="events.length">
      <div class="hidden md:block overflow-x-auto rounded-xl border border-slate-100 dark:border-slate-700" tabindex="0" role="region" aria-labelledby="audit-caption">
        <table class="w-full text-sm">
          <caption id="audit-caption" class="sr-only">Audit events for selected filters</caption>
          <thead class="bg-slate-50 dark:bg-slate-800 text-left text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700">
            <tr>
              <th scope="col" class="py-2.5 px-3 font-medium whitespace-nowrap">Time</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Actor</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Action</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Scope</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in events" :key="i" class="border-b border-slate-100 dark:border-slate-700 last:border-0 hover:bg-slate-50/70 dark:hover:bg-slate-800/70 transition-colors">
              <td class="py-2.5 px-3 text-slate-500 dark:text-slate-400 whitespace-nowrap tabular-nums" :title="e.ts">{{ formatTime(e.ts) }}</td>
              <td class="py-2.5 px-3 text-slate-800 dark:text-slate-100 font-medium max-w-[10rem] truncate" :title="e.actor">{{ e.actor }}</td>
              <td class="py-2.5 px-3"><span class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium border" :class="actionTone(e.action)">{{ e.action }}</span></td>
              <td class="py-2.5 px-3 text-slate-500 dark:text-slate-400 max-w-[10rem] truncate" :title="displayScope(e)">{{ displayScope(e) }}</td>
              <td class="py-2.5 px-3 text-slate-500 dark:text-slate-400 max-w-xs truncate" :title="displayDetail(e.detail)">{{ displayDetail(e.detail) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <ul class="md:hidden space-y-3" role="list" aria-label="Audit events">
        <li v-for="(e, i) in events" :key="i" class="border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-white dark:bg-slate-900">
          <div class="flex items-start justify-between gap-2">
            <span class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium border shrink-0" :class="actionTone(e.action)">{{ e.action }}</span>
            <span class="text-xs text-slate-400 tabular-nums whitespace-nowrap" :title="e.ts">{{ formatTime(e.ts) }}</span>
          </div>
          <dl class="mt-2 grid grid-cols-2 gap-2 text-xs">
            <div><dt class="text-slate-400">Actor</dt><dd class="text-slate-700 dark:text-slate-200 font-medium truncate" :title="e.actor">{{ e.actor }}</dd></div>
            <div><dt class="text-slate-400">Scope</dt><dd class="text-slate-600 dark:text-slate-300 truncate" :title="displayScope(e)">{{ displayScope(e) }}</dd></div>
          </dl>
          <p v-if="e.detail" class="mt-2 text-xs text-slate-500 dark:text-slate-400 break-words" :title="displayDetail(e.detail)"><span class="text-slate-400">Detail:</span> {{ displayDetail(e.detail) }}</p>
        </li>
      </ul>
    </template>

    <div v-else-if="!loading && !error" class="grid place-items-center text-center py-10 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <div class="grid place-items-center w-12 h-12 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-indigo-400 mb-3" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 4h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 8h6M7 12h6M7 10h3" stroke-linecap="round"/></svg>
      </div>
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No events match these filters</p>
      <p class="text-xs text-slate-400 mt-1 max-w-sm">Try clearing the action or account filter, or raise the limit. New events appear as activity happens.</p>
      <button @click="clearFilters" class="mt-3 min-h-9 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">Clear filters</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, errorDetail } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

const events = ref([])
const error = ref('')
const loading = ref(false)
const filters = ref({ limit: 100, action: '', account_id: '' })
const accounts = ref([])

const accountMap = computed(() => {
  const m = {}
  for (const a of accounts.value) m[a.id] = a.name
  return m
})

function displayScope(e) {
  const id = e.account_id || e.scope
  if (!id) return '—'
  // Never display raw UUIDs — show human-readable name or fallback
  return accountMap.value[id] || '—'
}

function displayDetail(detail) {
  if (!detail) return '—'
  // Replace account UUIDs with names, but leave unrelated UUIDs (e.g. document IDs) intact
  return detail.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, (m) => {
    const name = accountMap.value[m] || accountMap.value[m.toLowerCase()]
    return name ? name : m
  })
}

const isForbidden = computed(() => error.value.toLowerCase().includes('forbidden') || error.value.toLowerCase().includes('admin only'))

function formatTime(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return String(ts)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function actionTone(action) {
  const a = String(action || '').toLowerCase()
  if (a.includes('login') || a.includes('auth')) return 'bg-sky-50 dark:bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-100 dark:border-white/10'
  if (a.includes('create') || a.includes('issue') || a.includes('assign')) return 'bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-100 dark:border-white/10'
  if (a.includes('delete') || a.includes('revoke') || a.includes('remove') || a.includes('unassign')) return 'bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 border-red-100 dark:border-white/10'
  if (a.includes('upload') || a.includes('document')) return 'bg-violet-50 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300 border-violet-100 dark:border-white/10'
  if (a.includes('chat') || a.includes('audit')) return 'bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-100 dark:border-white/10'
  return 'bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-100 dark:border-white/10'
}

function clearFilters() {
  filters.value = { limit: 100, action: '', account_id: '' }
  load()
}

async function loadAccounts() {
  try {
    const { data } = await api.listAccounts()
    accounts.value = Array.isArray(data) ? data : []
  } catch {
    // keep empty — displayScope will fallback to '—' instead of raw UUID
  }
}

async function load() {
  loading.value = true
  error.value = ''
  const rawLimit = Number(filters.value.limit)
  const limit = Number.isFinite(rawLimit) ? Math.min(200, Math.max(1, Math.floor(rawLimit))) : 100
  filters.value.limit = limit
  const params = { limit }
  const action = filters.value.action.trim()
  const accountId = filters.value.account_id.trim()
  if (action) params.action = action
  if (accountId) params.account_id = accountId
  try {
    const { data } = await api.listAudit(params)
    events.value = Array.isArray(data) ? data : []
  } catch (e) {
    const status = e.response?.status
    if (status === 403) {
      error.value = 'Forbidden: admin only.'
    } else {
      error.value = errorDetail(e, 'Failed to load audit trail.')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAccounts()
  load()
})
</script>

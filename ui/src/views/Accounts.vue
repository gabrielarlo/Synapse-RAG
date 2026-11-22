<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-4 sm:p-6 flex flex-col gap-4">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-slate-800">Accounts</h2>
        <p class="text-xs text-slate-400 mt-0.5">Create and manage account workspaces for scoped retrieval.</p>
      </div>
      <span class="shrink-0 text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium tabular-nums" aria-live="polite">{{ filteredAccounts.length }} of {{ accounts.length }} total</span>
    </div>

    <form @submit.prevent="create" class="flex flex-col sm:flex-row gap-2 sm:items-start" novalidate>
      <div class="flex-1 min-w-0">
        <label for="account-name" class="sr-only">New account name</label>
        <BaseInput
          id="account-name"
          v-model="name"
          placeholder="New account name"
          aria-label="New account name"
          :aria-describedby="nameError ? 'account-error' : 'account-help'"
          :aria-invalid="!!nameError"
          class="w-full"
          required
          autocomplete="off"
          @blur="touched = true"
        />
        <p id="account-help" class="text-xs text-slate-400 mt-1.5">2–64 characters. Letters, numbers, spaces, hyphens and underscores.</p>
        <p v-if="nameError" id="account-error" class="text-xs text-red-600 mt-1" role="alert">{{ nameError }}</p>
      </div>
      <button
        :disabled="!trimmedName || creating"
        class="shrink-0 min-h-11 rounded-full bg-indigo-600 text-white px-5 py-2.5 hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600 w-full sm:w-auto"
      >
        <svg v-if="creating" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
        {{ creating ? 'Creating…' : 'Create' }}
      </button>
    </form>

    <div class="flex gap-2">
      <label for="account-search" class="sr-only">Search accounts</label>
      <div class="relative flex-1 min-w-0">
        <BaseInput id="account-search" v-model="search" placeholder="Search accounts…" aria-label="Search accounts" class="w-full pr-10" />
        <button
          v-if="search"
          @click="search = ''"
          aria-label="Clear search"
          class="absolute right-1 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        >✕</button>
      </div>
      <button @click="load" :disabled="loading" class="shrink-0 min-h-11 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 inline-flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
        <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin text-slate-500" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
        Refresh
      </button>
    </div>

    <div v-if="error" class="flex items-start gap-2 bg-red-50 border border-red-100 text-red-700 rounded-xl px-3 py-2.5" role="alert">
      <span class="shrink-0 mt-0.5" aria-hidden="true">⚠</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ error }}</p>
      <button @click="error=''" aria-label="Dismiss error" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">✕</button>
    </div>
    <div v-if="msg" class="flex items-start gap-2 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-xl px-3 py-2.5" role="status">
      <span class="shrink-0 mt-0.5" aria-hidden="true">✓</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ msg }}</p>
      <button @click="msg=''" aria-label="Dismiss message" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-emerald-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">✕</button>
    </div>

    <div v-if="loading && !accounts.length" class="space-y-2">
      <div v-for="i in 3" :key="i" class="animate-pulse flex items-center gap-3 border border-slate-100 rounded-xl p-3">
        <div class="w-9 h-9 rounded-full bg-slate-100 shrink-0"></div>
        <div class="flex-1 min-w-0 space-y-2">
          <div class="h-3 bg-slate-100 rounded w-1/3"></div>
          <div class="h-2.5 bg-slate-100 rounded w-1/4"></div>
        </div>
        <div class="w-16 h-3 bg-slate-100 rounded"></div>
      </div>
    </div>

    <ul v-else-if="filteredAccounts.length" class="space-y-2" role="list" aria-label="Accounts">
      <li v-for="a in filteredAccounts" :key="a.id" class="border border-slate-200 rounded-xl px-3 py-2.5 flex items-center justify-between gap-3 hover:bg-slate-50/70 transition-colors">
        <span class="flex items-center gap-2.5 min-w-0 flex-1">
          <span class="grid place-items-center w-9 h-9 rounded-full bg-violet-100 text-violet-700 text-xs font-bold shrink-0" aria-hidden="true">{{ (a.name || '?').slice(0, 1).toUpperCase() }}</span>
          <span class="min-w-0">
            <span class="block font-medium text-slate-800 text-sm truncate" :title="a.name">{{ a.name }}</span>
            <span class="block text-xs text-slate-400 truncate">Created {{ a.created_at ? timeAgo(a.created_at) : 'recently' }}</span>
          </span>
        </span>
        <span class="flex items-center gap-2 shrink-0">
          <span class="text-xs text-slate-400">—</span>
        </span>
      </li>
    </ul>

    <div v-else-if="search && !filteredAccounts.length" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 rounded-xl bg-slate-50/50">
      <p class="text-sm font-medium text-slate-600">No matches for “{{ search }}”</p>
      <p class="text-xs text-slate-400 mt-1">Try a different search or <button @click="search=''" class="underline hover:text-slate-600">clear filter</button>.</p>
    </div>

    <div v-else-if="!accounts.length && !loading" class="grid place-items-center text-center py-10 border border-dashed border-slate-200 rounded-xl bg-slate-50/50">
      <div class="grid place-items-center w-12 h-12 rounded-xl bg-white border border-slate-200 text-indigo-400 mb-3" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="7" r="3"/><path d="M3.5 16a6.5 6.5 0 0 1 13 0"/></svg>
      </div>
      <p class="text-sm font-medium text-slate-600">No accounts yet</p>
      <p class="text-xs text-slate-400 mt-1 max-w-sm">Create your first workspace above. Accounts scope documents, chat and audit trails per tenant.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, errorDetail } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

const accounts = ref([])
const name = ref('')
const error = ref('')
const msg = ref('')
const search = ref('')
const loading = ref(false)
const creating = ref(false)
const touched = ref(false)
const copiedId = ref('')

const trimmedName = computed(() => name.value.trim())

const nameError = computed(() => {
  if (!touched.value && !error.value) return ''
  const v = trimmedName.value
  if (!v && touched.value) return 'Account name is required.'
  if (v && v.length < 2) return 'Use at least 2 characters.'
  if (v && v.length > 64) return 'Keep it under 64 characters.'
  return ''
})

const filteredAccounts = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return accounts.value
  return accounts.value.filter((a) => String(a.name).toLowerCase().includes(q) || String(a.id).toLowerCase().includes(q))
})

function timeAgo(ts) {
  if (!ts) return 'recently'
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return 'recently'
  const sec = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (sec < 60) return 'moments ago'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} minute${min === 1 ? '' : 's'} ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} hour${hr === 1 ? '' : 's'} ago`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} day${day === 1 ? '' : 's'} ago`
  return new Date(ts).toLocaleDateString()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.listAccounts()
    accounts.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = errorDetail(e, 'Failed to load accounts.')
  } finally {
    loading.value = false
  }
}

async function create() {
  touched.value = true
  const v = trimmedName.value
  if (!v) {
    error.value = 'Enter an account name.'
    return
  }
  if (v.length < 2 || v.length > 64) {
    error.value = nameError.value || 'Check the account name.'
    return
  }
  creating.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.createAccount(v)
    name.value = ''
    touched.value = false
    msg.value = `Created “${v}”.`
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Create failed.')
  } finally {
    creating.value = false
  }
}

async function copyId(id) {
  try {
    await navigator.clipboard.writeText(String(id))
    copiedId.value = String(id)
    setTimeout(() => { if (copiedId.value === String(id)) copiedId.value = '' }, 1500)
  } catch {
    error.value = 'Copy failed — select and copy manually.'
  }
}

onMounted(load)
</script>

<template>
  <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-100 dark:border-slate-700 p-4 sm:p-6 flex flex-col gap-4">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100">Accounts</h2>
        <p class="text-xs text-slate-400 mt-0.5">Create and manage account workspaces for scoped retrieval.</p>
      </div>
      <span class="shrink-0 text-xs px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-medium tabular-nums" aria-live="polite">{{ filteredAccounts.length }} of {{ accounts.length }} total</span>
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
        <p v-if="nameError" id="account-error" class="text-xs text-red-600 dark:text-red-400 mt-1" role="alert">{{ nameError }}</p>
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
        <BaseInput ref="searchInput" id="account-search" v-model="search" placeholder="Search accounts…" aria-label="Search accounts" class="w-full pr-10" autofocus />
        <button
          v-if="search"
          @click="search = ''"
          aria-label="Clear search"
          class="absolute right-1 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        >✕</button>
      </div>
      <button @click="load" :disabled="loading" class="shrink-0 min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
        <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
        Refresh
      </button>
    </div>

    <div v-if="isAdmin" role="group" aria-label="Account status filter" class="flex gap-1 p-1 rounded-full bg-slate-100 dark:bg-slate-800 w-full sm:w-auto sm:self-start">
      <button
        type="button"
        :aria-pressed="statusFilter === 'active'"
        @click="statusFilter = 'active'"
        class="flex-1 sm:flex-none min-h-11 rounded-full px-4 py-2 text-sm font-medium inline-flex items-center justify-center gap-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        :class="statusFilter === 'active' ? 'bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
      >Active <span class="text-xs tabular-nums opacity-70">{{ activeCount }}</span></button>
      <button
        type="button"
        :aria-pressed="statusFilter === 'archived'"
        @click="statusFilter = 'archived'"
        class="flex-1 sm:flex-none min-h-11 rounded-full px-4 py-2 text-sm font-medium inline-flex items-center justify-center gap-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        :class="statusFilter === 'archived' ? 'bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
      >Archived <span class="text-xs tabular-nums opacity-70">{{ archivedCount }}</span></button>
    </div>

    <div v-if="error" class="flex items-start gap-2 bg-red-50 dark:bg-red-500/15 border border-red-100 dark:border-white/10 text-red-700 dark:text-red-300 rounded-xl px-3 py-2.5" role="alert">
      <span class="shrink-0 mt-0.5" aria-hidden="true">⚠</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ error }}</p>
      <button @click="error=''" aria-label="Dismiss error" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-red-100 dark:hover:bg-red-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">✕</button>
    </div>
    <div v-if="msg" class="flex items-start gap-2 bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-100 dark:border-white/10 text-emerald-700 dark:text-emerald-300 rounded-xl px-3 py-2.5" role="status">
      <span class="shrink-0 mt-0.5" aria-hidden="true">✓</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ msg }}</p>
      <button @click="msg=''" aria-label="Dismiss message" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-emerald-100 dark:hover:bg-emerald-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">✕</button>
    </div>

    <div v-if="loading && !accounts.length" class="space-y-2">
      <div v-for="i in 3" :key="i" class="animate-pulse flex items-center gap-3 border border-slate-100 dark:border-slate-700 rounded-xl p-3">
        <div class="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-800 shrink-0"></div>
        <div class="flex-1 min-w-0 space-y-2">
          <div class="h-3 bg-slate-100 dark:bg-slate-800 rounded w-1/3"></div>
          <div class="h-2.5 bg-slate-100 dark:bg-slate-800 rounded w-1/4"></div>
        </div>
        <div class="w-16 h-3 bg-slate-100 dark:bg-slate-800 rounded"></div>
      </div>
    </div>

    <ul v-else-if="filteredAccounts.length" class="space-y-2" role="list" aria-label="Accounts">
      <li v-for="a in filteredAccounts" :key="a.id" class="border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 flex items-center justify-between gap-3 hover:bg-slate-50/70 dark:hover:bg-slate-800/70 transition-colors">
        <span class="flex items-center gap-2.5 min-w-0 flex-1">
          <span class="grid place-items-center w-9 h-9 rounded-full bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 text-xs font-bold shrink-0" aria-hidden="true">{{ (a.name || '?').slice(0, 1).toUpperCase() }}</span>
          <span class="min-w-0">
            <span class="block font-medium text-slate-800 dark:text-slate-100 text-sm truncate" :title="a.name">{{ a.name }}</span>
            <span class="block text-xs text-slate-400 truncate">Created {{ a.created_at ? timeAgo(a.created_at) : 'recently' }}</span>
          </span>
        </span>
        <span class="flex items-center gap-2 shrink-0">
          <template v-if="isAdmin">
            <template v-if="a.is_archived">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0 bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300">Archived</span>
              <button
                type="button"
                :disabled="archiving"
                @click="unarchive(a)"
                :aria-label="`Unarchive ${a.name}`"
                :title="`Unarchive ${a.name}`"
                class="grid place-items-center w-11 h-11 rounded-full text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-500/15 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
              >
                <svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M3 7.5h14v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9Z" />
                  <path d="M2.5 4.5h15v3h-15z" />
                  <path d="M10 16V9m0 0-2 2m2-2 2 2" />
                </svg>
              </button>
            </template>
            <button
              v-else
              type="button"
              :disabled="archiving"
              @click="askArchive(a)"
              :aria-label="`Archive ${a.name}`"
              :title="`Archive ${a.name}`"
              class="grid place-items-center w-11 h-11 rounded-full text-slate-400 hover:text-red-600 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-500/15 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600"
            >
              <svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M3 7.5h14v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9Z" />
                <path d="M2.5 4.5h15v3h-15z" />
                <path d="M8 11h4" />
              </svg>
            </button>
          </template>
          <span v-else class="text-xs text-slate-400">—</span>
        </span>
      </li>
    </ul>

    <div v-else-if="search && !filteredAccounts.length" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No matches for “{{ search }}”</p>
      <p class="text-xs text-slate-400 mt-1">Try a different search or <button @click="search=''" class="underline hover:text-slate-600 dark:hover:text-slate-300">clear filter</button>.</p>
    </div>

    <div v-else-if="!accounts.length && !loading" class="grid place-items-center text-center py-10 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <div class="grid place-items-center w-12 h-12 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-indigo-400 mb-3" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="7" r="3"/><path d="M3.5 16a6.5 6.5 0 0 1 13 0"/></svg>
      </div>
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No accounts yet</p>
      <p class="text-xs text-slate-400 mt-1 max-w-sm">Create your first workspace above. Accounts scope documents, chat and audit trails per tenant.</p>
    </div>

    <div v-else-if="!filteredAccounts.length" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No {{ statusFilter }} accounts</p>
      <p class="text-xs text-slate-400 mt-1">{{ statusFilter === 'archived' ? 'Archived accounts will appear here.' : 'All accounts are archived — switch to Archived to see them.' }}</p>
    </div>

    <dialog ref="archiveDialog" aria-labelledby="archive-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onArchiveClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5">
        <h3 id="archive-title" class="font-semibold text-slate-800 dark:text-slate-100">Archive account</h3>
        <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Archive “{{ archiveTarget?.name }}”? Its documents will be unavailable for chat, external FAQ and management until you unarchive it. No data is deleted.</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelArchive" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600" autofocus>Cancel</button>
          <button type="button" @click="confirmArchive" :disabled="archiving" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600">
            <svg v-if="archiving" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Archive
          </button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { api, errorDetail, currentRole } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

const accounts = ref([])
const name = ref('')
const error = ref('')
const msg = ref('')
const search = ref('')
const statusFilter = ref('active')
const loading = ref(false)
const creating = ref(false)
const touched = ref(false)
const copiedId = ref('')
const searchInput = ref(null)
const isAdmin = computed(() => currentRole() === 'admin')
const archiveDialog = ref(null)
const archiveTarget = ref(null)
const archiving = ref(false)

const trimmedName = computed(() => name.value.trim())

const nameError = computed(() => {
  if (!touched.value && !error.value) return ''
  const v = trimmedName.value
  if (!v && touched.value) return 'Account name is required.'
  if (v && v.length < 2) return 'Use at least 2 characters.'
  if (v && v.length > 64) return 'Keep it under 64 characters.'
  return ''
})

const activeCount = computed(() => accounts.value.filter((a) => !a.is_archived).length)
const archivedCount = computed(() => accounts.value.filter((a) => a.is_archived).length)

const statusFiltered = computed(() =>
  accounts.value.filter((a) => (a.is_archived === true) === (statusFilter.value === 'archived')))

const filteredAccounts = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return statusFiltered.value
  return statusFiltered.value.filter((a) => String(a.name).toLowerCase().includes(q) || String(a.id).toLowerCase().includes(q))
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

function askArchive(a) {
  archiveTarget.value = a
  archiving.value = false
  archiveDialog.value?.showModal()
}

function cancelArchive() {
  archiveDialog.value?.close()
}

function onArchiveClosed() {
  archiveTarget.value = null
}

async function confirmArchive() {
  const target = archiveTarget.value
  if (!target) return
  archiving.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.archiveAccount(target.id)
    archiveDialog.value?.close()
    msg.value = `Archived “${target.name}”. Its documents are no longer available.`
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Archive failed.')
    archiveDialog.value?.close()
  } finally {
    archiving.value = false
  }
}

async function unarchive(a) {
  archiving.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.unarchiveAccount(a.id)
    msg.value = `Unarchived “${a.name}”. Documents are available again.`
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Unarchive failed.')
  } finally {
    archiving.value = false
  }
}

onMounted(async () => {
  await load()
  await nextTick()
  // Autofocus search for keyboard users; respects SPA navigation (autofocus attr alone only fires on full page load)
  const el = searchInput.value?.$el ?? document.getElementById('account-search')
  el?.focus?.()
})
</script>

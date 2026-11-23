<template>
  <div class="grid gap-4 md:gap-6 md:grid-cols-2">
    <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-100 dark:border-slate-700 p-4 sm:p-6 flex flex-col gap-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100">Users</h2>
          <p class="text-xs text-slate-400 mt-0.5">Manage user accounts and roles.</p>
        </div>
        <span class="shrink-0 text-xs px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-medium tabular-nums" aria-live="polite">{{ filteredUsers.length }} of {{ users.length }} total</span>
      </div>

      <form @submit.prevent="createUser" class="space-y-2" novalidate>
        <div>
          <label for="staff-username" class="sr-only">Username</label>
          <BaseInput
            id="staff-username"
            v-model="form.username"
            placeholder="Username"
            aria-label="Username"
            :aria-describedby="userError ? 'staff-username-error' : 'staff-username-help'"
            :aria-invalid="!!userError"
            class="w-full"
            required
            autocomplete="username"
            @blur="touched.username = true"
          />
          <p id="staff-username-help" class="text-xs text-slate-400 mt-1.5">2–32 characters. Letters, numbers, hyphens, underscores.</p>
          <p v-if="userError" id="staff-username-error" class="text-xs text-red-600 dark:text-red-400 mt-1" role="alert">{{ userError }}</p>
        </div>
        <div>
          <label for="staff-password" class="sr-only">Password</label>
          <div class="relative">
            <BaseInput
              id="staff-password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Password"
              aria-label="Password"
              :aria-describedby="passwordError ? 'staff-password-error' : 'staff-password-help'"
              :aria-invalid="!!passwordError"
              autocomplete="new-password"
              class="w-full pr-11"
              required
              @blur="touched.password = true"
            />
            <button type="button" @click="showPassword = !showPassword" :aria-label="showPassword ? 'Hide password' : 'Show password'" :aria-pressed="showPassword" class="absolute right-1 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
              <svg v-if="showPassword" viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2 10s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6Z"/><circle cx="10" cy="10" r="2.5"/><path d="M3 3l14 14" stroke-linecap="round"/></svg>
              <svg v-else viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2 10s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6Z"/><circle cx="10" cy="10" r="2.5"/></svg>
            </button>
          </div>
          <p id="staff-password-help" class="text-xs text-slate-400 mt-1.5">At least 6 characters.</p>
          <p v-if="passwordError" id="staff-password-error" class="text-xs text-red-600 dark:text-red-400 mt-1" role="alert">{{ passwordError }}</p>
        </div>
        <label for="staff-role" class="sr-only">Role</label>
        <select id="staff-role" v-model="form.role" aria-label="Role" class="w-full min-h-11 border border-slate-200 dark:border-slate-700 rounded-full px-4 py-2.5 bg-white dark:bg-slate-900 text-sm focus:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
          <option value="staff">staff — scoped to assigned accounts</option>
          <option value="admin">admin — full access</option>
        </select>

        <button :disabled="creating || !canCreate" class="w-full min-h-11 rounded-full bg-indigo-600 text-white px-5 py-2.5 hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
          <svg v-if="creating" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
          {{ creating ? 'Creating…' : 'Create user' }}
        </button>
      </form>

      <div class="flex gap-2">
        <label for="user-search" class="sr-only">Search users</label>
        <div class="relative flex-1 min-w-0">
          <BaseInput id="user-search" v-model="search" placeholder="Search users…" aria-label="Search users" class="w-full pr-10" />
          <button v-if="search" @click="search=''" aria-label="Clear search" class="absolute right-1 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">✕</button>
        </div>
        <button @click="load" :disabled="loading" class="shrink-0 min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
          <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
          Refresh
        </button>
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

      <div v-if="loading && !users.length" class="space-y-2">
        <div v-for="i in 3" :key="i" class="animate-pulse flex items-center gap-3 border border-slate-100 dark:border-slate-700 rounded-xl p-3">
          <div class="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-800 shrink-0"></div>
          <div class="flex-1 min-w-0 space-y-2">
            <div class="h-3 bg-slate-100 dark:bg-slate-800 rounded w-1/3"></div>
            <div class="h-2.5 bg-slate-100 dark:bg-slate-800 rounded w-1/4"></div>
          </div>
          <div class="w-12 h-3 bg-slate-100 dark:bg-slate-800 rounded"></div>
        </div>
      </div>

      <ul v-else-if="filteredUsers.length" class="space-y-2" role="list" aria-label="Users">
        <li v-for="u in filteredUsers" :key="u.id || u.username" class="border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 flex items-center justify-between gap-3 hover:bg-slate-50/70 dark:hover:bg-slate-800/70 transition-colors">
          <span class="flex items-center gap-2.5 min-w-0 flex-1">
            <span class="grid place-items-center w-9 h-9 rounded-full text-xs font-bold shrink-0" :class="(u.role || '') === 'admin' ? 'bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'" aria-hidden="true">{{ (u.username || '?').slice(0, 1).toUpperCase() }}</span>
            <span class="min-w-0">
              <span class="flex items-center gap-1.5 flex-wrap">
                <span class="text-slate-800 dark:text-slate-100 font-medium text-sm truncate" :title="u.username">{{ u.username }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0" :class="(u.role || '') === 'admin' ? 'bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'">{{ u.role || '—' }}</span>
                <span v-if="!u.is_active" class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">Inactive</span>
              </span>
              <span class="block text-xs text-slate-400 truncate">—</span>
            </span>
          </span>
          <button v-if="canDeactivate(u)" type="button" @click="askDeactivate(u)" :aria-label="`Deactivate ${u.username}`" :title="`Deactivate ${u.username}`" class="shrink-0 grid place-items-center w-11 h-11 rounded-full border border-red-200 dark:border-white/10 bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600">
            <svg viewBox="0 0 20 20" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="7" cy="7" r="2.6"/><path d="M2.5 16c.7-2.6 2.4-3.8 4.5-3.8 1 0 1.9.2 2.6.7M13 12l4 4m0-4-4 4" stroke-linecap="round"/></svg>
          </button>
          <span v-else class="text-xs text-slate-400 shrink-0 hidden sm:block">—</span>
        </li>
      </ul>

      <div v-else-if="search && !filteredUsers.length" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
        <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No matches for “{{ search }}”</p>
        <p class="text-xs text-slate-400 mt-1">Try a different search or <button @click="search=''" class="underline hover:text-slate-600 dark:hover:text-slate-300">clear filter</button>.</p>
      </div>

      <div v-else-if="!users.length && !loading" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
        <div class="grid place-items-center w-12 h-12 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-indigo-400 mb-3" aria-hidden="true">
          <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="7" r="3"/><path d="M3.5 16a6.5 6.5 0 0 1 13 0"/></svg>
        </div>
        <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No users yet</p>
        <p class="text-xs text-slate-400 mt-1 max-w-sm">Create the first staff or admin account above. Admins can manage all workspaces; staff are scoped to assignments.</p>
      </div>
    </div>

    <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-100 dark:border-slate-700 p-4 sm:p-6 flex flex-col gap-4 h-fit">
      <div>
        <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100">Assign staff to account</h2>
        <p class="text-xs text-slate-400 mt-0.5">Link staff users to account workspaces for retrieval.</p>
      </div>

      <div class="space-y-3">
        <div>
          <label for="assign-account" class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Account</label>
          <select id="assign-account" v-model="accountId" aria-label="Account" class="w-full min-h-11 border border-slate-200 dark:border-slate-700 rounded-full px-4 py-2.5 bg-white dark:bg-slate-900 text-sm focus:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
            <option value="">Select account</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
        </div>
        <div>
          <label for="assign-user" class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">User</label>
          <select id="assign-user" v-model="userId" aria-label="User" class="w-full min-h-11 border border-slate-200 dark:border-slate-700 rounded-full px-4 py-2.5 bg-white dark:bg-slate-900 text-sm focus:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
            <option value="">Select user</option>
            <option v-for="u in users" :key="u.id || u.username" :value="u.id">{{ u.username }} — {{ u.role || 'staff' }}</option>
          </select>
        </div>
        <div class="flex flex-col sm:flex-row gap-2">
          <button @click="assign" :disabled="assigning || !accountId || !userId" class="flex-1 min-h-11 rounded-full bg-emerald-600 text-white px-4 py-2.5 hover:bg-emerald-700 disabled:opacity-50 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">
            <svg v-if="assigning" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            {{ assigning ? 'Assigning…' : 'Assign' }}
          </button>
          <button @click="unassign" :disabled="assigning || !accountId || !userId" class="flex-1 min-h-11 rounded-full border border-red-200 dark:border-white/10 bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 px-4 py-2.5 hover:bg-red-100 dark:hover:bg-red-500/25 disabled:opacity-50 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">
            <svg v-if="assigning" viewBox="0 0 20 20" class="w-4 h-4 animate-spin text-red-500 dark:text-red-400" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Unassign
          </button>
        </div>
        <p class="text-xs text-slate-400">Assign gives retrieval access; unassign revokes it. Requires both fields.</p>
      </div>

      <div v-if="assignError" class="flex items-start gap-2 bg-red-50 dark:bg-red-500/15 border border-red-100 dark:border-white/10 text-red-700 dark:text-red-300 rounded-xl px-3 py-2.5" role="alert">
        <span class="shrink-0 mt-0.5" aria-hidden="true">⚠</span>
        <p class="text-sm flex-1 min-w-0 break-words">{{ assignError }}</p>
        <button @click="assignError=''" aria-label="Dismiss error" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-red-100 dark:hover:bg-red-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">✕</button>
      </div>
      <div v-if="assignMsg" class="flex items-start gap-2 bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-100 dark:border-white/10 text-emerald-700 dark:text-emerald-300 rounded-xl px-3 py-2.5" role="status">
        <span class="shrink-0 mt-0.5" aria-hidden="true">✓</span>
        <p class="text-sm flex-1 min-w-0 break-words">{{ assignMsg }}</p>
        <button @click="assignMsg=''" aria-label="Dismiss message" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-emerald-100 dark:hover:bg-emerald-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">✕</button>
      </div>
    </div>
  </div>

  <dialog ref="deactivateDialog" aria-labelledby="deactivate-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onDeactivateClosed">
    <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5">
      <h3 id="deactivate-title" class="font-semibold text-slate-800 dark:text-slate-100">Deactivate user</h3>
      <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Deactivate “{{ deactivateTarget?.username }}”? They will lose access immediately, including any active sessions.</p>
      <div class="mt-5 flex justify-end gap-2">
        <button type="button" @click="cancelDeactivate" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600" autofocus>Cancel</button>
        <button type="button" @click="confirmDeactivate" :disabled="deactivating" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600">
          <svg v-if="deactivating" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
          Deactivate
        </button>
      </div>
    </form>
  </dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, errorDetail, currentRole, currentUsername } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

const users = ref([])
const accounts = ref([])
const form = ref({ username: '', password: '', role: 'staff' })
const accountId = ref('')
const userId = ref('')
const error = ref('')
const msg = ref('')
const assignError = ref('')
const assignMsg = ref('')
const search = ref('')
const loading = ref(false)
const creating = ref(false)
const assigning = ref(false)
const showPassword = ref(false)
const touched = ref({ username: false, password: false })
const deactivateDialog = ref(null)
const deactivateTarget = ref(null)
const deactivating = ref(false)

const isAdmin = computed(() => currentRole() === 'admin')
function canDeactivate(u) {
  return isAdmin.value && u.is_active !== false && u.username !== currentUsername()
}
function askDeactivate(u) {
  deactivateTarget.value = u
  deactivating.value = false
  deactivateDialog.value?.showModal()
}
function cancelDeactivate() {
  deactivateDialog.value?.close()
}
function onDeactivateClosed() {
  deactivateTarget.value = null
}
async function confirmDeactivate() {
  const target = deactivateTarget.value
  if (!target) return
  deactivating.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.deactivateUser(target.id)
    deactivateDialog.value?.close()
    msg.value = `${target.username} deactivated. Access revoked.`
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Deactivate failed.')
    deactivateDialog.value?.close()
  } finally {
    deactivating.value = false
  }
}

const filteredUsers = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => String(u.username).toLowerCase().includes(q) || String(u.role).toLowerCase().includes(q) || String(u.id).toLowerCase().includes(q))
})

const userError = computed(() => {
  if (!touched.value.username && !error.value) return ''
  const v = form.value.username.trim()
  if (!v && touched.value.username) return 'Username is required.'
  if (v && v.length < 2) return 'Use at least 2 characters.'
  if (v && v.length > 32) return 'Keep it under 32 characters.'
  return ''
})

const passwordError = computed(() => {
  if (!touched.value.password && !error.value) return ''
  const v = form.value.password
  if (!v && touched.value.password) return 'Password is required.'
  if (v && v.length < 6) return 'Use at least 6 characters.'
  return ''
})

const canCreate = computed(() => {
  const u = form.value.username.trim()
  const p = form.value.password
  return u.length >= 2 && u.length <= 32 && p.length >= 6
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [u, a] = await Promise.all([api.listUsers(), api.listAccounts()])
    users.value = Array.isArray(u.data) ? u.data : []
    accounts.value = Array.isArray(a.data) ? a.data : []
  } catch (e) {
    error.value = errorDetail(e, 'Failed to load.')
  } finally {
    loading.value = false
  }
}

async function createUser() {
  touched.value = { username: true, password: true }
  if (!canCreate.value) {
    error.value = userError.value || passwordError.value || 'Check the fields above.'
    return
  }
  creating.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.createUser(form.value.username.trim(), form.value.password, form.value.role)
    form.value = { username: '', password: '', role: 'staff' }
    touched.value = { username: false, password: false }
    showPassword.value = false
    msg.value = 'User created.'
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Create failed.')
  } finally {
    creating.value = false
  }
}

async function assign() {
  if (!accountId.value || !userId.value) {
    assignError.value = 'Choose an account and a user.'
    return
  }
  assigning.value = true
  assignError.value = ''
  assignMsg.value = ''
  try {
    await api.assignStaff(accountId.value, userId.value)
    assignMsg.value = 'Assigned.'
  } catch (e) {
    assignError.value = errorDetail(e, 'Assign failed.')
  } finally {
    assigning.value = false
  }
}

async function unassign() {
  if (!accountId.value || !userId.value) {
    assignError.value = 'Choose an account and a user.'
    return
  }
  assigning.value = true
  assignError.value = ''
  assignMsg.value = ''
  try {
    await api.unassignStaff(accountId.value, userId.value)
    assignMsg.value = 'Unassigned.'
  } catch (e) {
    assignError.value = errorDetail(e, 'Unassign failed.')
  } finally {
    assigning.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="grid gap-6 md:grid-cols-2">
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-bold text-slate-800">Users</h2>
        <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">{{ users.length }} total</span>
      </div>
      <form @submit.prevent="createUser" class="space-y-2 mb-4">
        <input v-model="form.username" placeholder="Username" aria-label="Username" class="w-full border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500" required />
        <input v-model="form.password" type="password" placeholder="Password" aria-label="Password" autocomplete="new-password" class="w-full border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500" required />
        <select v-model="form.role" aria-label="Role" class="w-full border border-slate-200 rounded-lg px-3 py-2 bg-white focus:border-indigo-500">
          <option value="staff">staff</option>
          <option value="admin">admin</option>
        </select>
        <button class="bg-indigo-600 text-white rounded-lg px-4 py-2 hover:bg-indigo-700 transition-colors font-medium">Create user</button>
      </form>
      <ul class="divide-y divide-slate-100 text-sm">
        <li v-for="u in users" :key="u.id || u.username" class="py-2.5 flex items-center justify-between gap-3">
          <span class="flex items-center gap-2.5 min-w-0">
            <span class="grid place-items-center w-7 h-7 rounded-full bg-violet-100 text-violet-700 text-xs font-bold shrink-0" aria-hidden="true">{{ (u.username || '?').slice(0, 1).toUpperCase() }}</span>
            <span class="text-slate-700 font-medium truncate">{{ u.username }}</span>
            <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="(u.role || '') === 'admin' ? 'bg-violet-100 text-violet-700' : 'bg-slate-100 text-slate-600'">{{ u.role || u.id }}</span>
          </span>
          <span class="text-xs text-slate-400 font-mono shrink-0">id: {{ u.id }}</span>
        </li>
      </ul>
    </div>
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6 h-fit">
      <h2 class="text-xl font-bold mb-4 text-slate-800">Assign staff to account</h2>
      <div class="space-y-2">
        <select v-model="accountId" aria-label="Account" class="w-full border border-slate-200 rounded-lg px-3 py-2 bg-white focus:border-indigo-500">
          <option value="">Select account</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <select v-model="userId" aria-label="User" class="w-full border border-slate-200 rounded-lg px-3 py-2 bg-white focus:border-indigo-500">
          <option value="">Select user</option>
          <option v-for="u in users" :key="u.id || u.username" :value="u.id">{{ u.username }}</option>
        </select>
        <div class="flex gap-2">
          <button @click="assign" class="bg-emerald-600 text-white rounded-lg px-4 py-2 hover:bg-emerald-700 transition-colors font-medium">Assign</button>
          <button @click="unassign" class="bg-red-600/90 text-white rounded-lg px-4 py-2 hover:bg-red-700 transition-colors font-medium">Unassign</button>
        </div>
      </div>
      <p v-if="error" class="mt-3 text-sm text-red-600" role="alert">{{ error }}</p>
      <p v-if="msg" class="mt-3 text-sm text-green-600" role="status">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const users = ref([])
const accounts = ref([])
const form = ref({ username: '', password: '', role: 'staff' })
const accountId = ref('')
const userId = ref('')
const error = ref('')
const msg = ref('')

async function load() {
  error.value = ''
  try {
    const [u, a] = await Promise.all([api.listUsers(), api.listAccounts()])
    users.value = u.data
    accounts.value = a.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load.'
  }
}

async function createUser() {
  error.value = ''
  msg.value = ''
  try {
    await api.createUser(form.value.username, form.value.password, form.value.role)
    form.value = { username: '', password: '', role: 'staff' }
    msg.value = 'User created.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Create failed.'
  }
}

async function assign() {
  error.value = ''
  msg.value = ''
  try {
    await api.assignStaff(accountId.value, userId.value)
    msg.value = 'Assigned.'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Assign failed.'
  }
}

async function unassign() {
  error.value = ''
  msg.value = ''
  try {
    await api.unassignStaff(accountId.value, userId.value)
    msg.value = 'Unassigned.'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unassign failed.'
  }
}

onMounted(load)
</script>

<template>
  <div class="grid gap-6 md:grid-cols-2">
    <div class="bg-white rounded shadow p-6">
      <h2 class="text-xl font-bold mb-4 text-gray-800">Users</h2>
      <form @submit.prevent="createUser" class="space-y-2 mb-4">
        <input v-model="form.username" placeholder="Username" class="w-full border rounded px-3 py-2" required />
        <input v-model="form.password" type="password" placeholder="Password" class="w-full border rounded px-3 py-2" required />
        <select v-model="form.role" class="w-full border rounded px-3 py-2">
          <option value="staff">staff</option>
          <option value="admin">admin</option>
        </select>
        <button class="bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700">Create user</button>
      </form>
      <ul class="divide-y text-sm">
        <li v-for="u in users" :key="u.id || u.username" class="py-2 flex justify-between">
          <span>{{ u.username }} <span class="text-gray-400">({{ u.role || u.id }})</span></span>
          <span class="text-gray-400">id: {{ u.id }}</span>
        </li>
      </ul>
    </div>
    <div class="bg-white rounded shadow p-6">
      <h2 class="text-xl font-bold mb-4 text-gray-800">Assign staff to account</h2>
      <div class="space-y-2">
        <select v-model="accountId" class="w-full border rounded px-3 py-2">
          <option value="">Select account</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <select v-model="userId" class="w-full border rounded px-3 py-2">
          <option value="">Select user</option>
          <option v-for="u in users" :key="u.id || u.username" :value="u.id">{{ u.username }}</option>
        </select>
        <div class="flex gap-2">
          <button @click="assign" class="bg-green-600 text-white rounded px-4 py-2 hover:bg-green-700">Assign</button>
          <button @click="unassign" class="bg-red-600 text-white rounded px-4 py-2 hover:bg-red-700">Unassign</button>
        </div>
      </div>
      <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
      <p v-if="msg" class="mt-3 text-sm text-green-600">{{ msg }}</p>
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

<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold text-slate-800">Accounts</h2>
      <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">{{ accounts.length }} total</span>
    </div>
    <form @submit.prevent="create" class="flex gap-2 mb-4">
      <BaseInput v-model="name" placeholder="New account name" aria-label="New account name" class="flex-1" required />
      <button class="bg-indigo-600 text-white rounded-lg px-4 py-2 hover:bg-indigo-700 transition-colors font-medium">Create</button>
    </form>
    <p v-if="error" class="text-sm text-red-600 mb-2" role="alert">{{ error }}</p>
    <ul class="divide-y divide-slate-100">
      <li v-for="a in accounts" :key="a.id" class="py-2.5 flex items-center justify-between text-sm gap-3">
        <span class="flex items-center gap-2.5 min-w-0">
          <span class="grid place-items-center w-7 h-7 rounded-full bg-violet-100 text-violet-700 text-xs font-bold shrink-0" aria-hidden="true">{{ (a.name || '?').slice(0, 1).toUpperCase() }}</span>
          <span class="font-medium text-slate-700 truncate">{{ a.name }}</span>
        </span>
        <span class="text-xs text-slate-400 font-mono shrink-0">#{{ a.id }}</span>
      </li>
    </ul>
    <p v-if="!accounts.length && !error" class="text-sm text-slate-400 mt-2">No accounts yet — create one above.</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

const accounts = ref([])
const name = ref('')
const error = ref('')

async function load() {
  error.value = ''
  try {
    const { data } = await api.listAccounts()
    accounts.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load accounts.'
  }
}

async function create() {
  try {
    await api.createAccount(name.value)
    name.value = ''
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Create failed.'
  }
}

onMounted(load)
</script>

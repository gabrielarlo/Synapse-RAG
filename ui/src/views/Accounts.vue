<template>
  <div class="bg-white rounded shadow p-6">
    <h2 class="text-xl font-bold mb-4 text-gray-800">Accounts</h2>
    <form @submit.prevent="create" class="flex gap-2 mb-4">
      <input v-model="name" placeholder="New account name" class="border rounded px-3 py-2 flex-1" required />
      <button class="bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700">Create</button>
    </form>
    <p v-if="error" class="text-sm text-red-600 mb-2">{{ error }}</p>
    <ul class="divide-y">
      <li v-for="a in accounts" :key="a.id" class="py-2 flex justify-between text-sm">
        <span class="font-medium">{{ a.name }}</span>
        <span class="text-gray-400">#{{ a.id }}</span>
      </li>
    </ul>
    <p v-if="!accounts.length && !error" class="text-sm text-gray-500">No accounts.</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

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

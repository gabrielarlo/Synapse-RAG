<template>
  <div class="max-w-sm mx-auto mt-20 bg-white rounded shadow p-6">
    <h2 class="text-xl font-bold mb-4 text-gray-800">Login</h2>
    <form @submit.prevent="submit" class="space-y-3">
      <input v-model="username" placeholder="Username" class="w-full border rounded px-3 py-2" required />
      <input v-model="password" type="password" placeholder="Password" class="w-full border rounded px-3 py-2" required />
      <button class="w-full bg-blue-600 text-white rounded py-2 hover:bg-blue-700" :disabled="loading">
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.login(username.value, password.value)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    router.push('/chat')
  } catch (e) {
    error.value =
      e.response?.status === 429
        ? 'Too many attempts. Please wait and retry.'
        : e.response?.data?.detail || 'Login failed.'
  } finally {
    loading.value = false
  }
}
</script>

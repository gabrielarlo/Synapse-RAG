<template>
  <div class="min-h-screen grid place-items-center px-4 py-12">
    <div class="w-full max-w-3xl grid md:grid-cols-2 overflow-hidden rounded-2xl shadow-pop bg-white border border-slate-100">
      <div class="hidden md:flex flex-col justify-between p-8 text-white bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-700">
        <div class="flex items-center gap-2.5">
          <span class="grid place-items-center w-9 h-9 rounded-lg bg-white/20 font-bold">S</span>
          <p class="font-bold">Synapse RAG</p>
        </div>
        <div>
          <h2 class="text-2xl font-bold leading-snug">Ask your docs.<br />Get cited answers.</h2>
          <p class="mt-2 text-sm text-indigo-100">Scoped by account. Audited by default.</p>
        </div>
        <p class="text-xs text-indigo-200">Secure sign-in below</p>
      </div>
      <div class="p-8">
        <h2 class="text-xl font-bold mb-1 text-slate-800">Welcome back</h2>
        <p class="text-sm text-slate-500 mb-5">Sign in to continue.</p>
        <form @submit.prevent="submit" class="space-y-3">
          <label class="block text-sm">
            <span class="text-slate-600 font-medium">Username</span>
            <input v-model="username" placeholder="Username" autocomplete="username" class="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500" required />
          </label>
          <label class="block text-sm">
            <span class="text-slate-600 font-medium">Password</span>
            <input v-model="password" type="password" placeholder="Password" autocomplete="current-password" class="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 focus:border-indigo-500" required />
          </label>
          <button class="w-full bg-indigo-600 text-white rounded-lg py-2.5 hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50" :disabled="loading">
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
        <p v-if="error" class="mt-3 text-sm text-red-600" role="alert">{{ error }}</p>
      </div>
    </div>
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

<template>
  <div class="flex min-h-screen bg-gray-100">
    <aside v-if="loggedIn" class="w-60 shrink-0 bg-gray-900 text-gray-200 flex flex-col">
      <div class="px-5 py-4 text-lg font-bold text-white border-b border-gray-700">
        Synapse RAG
      </div>
      <nav class="flex-1 p-3 space-y-1 text-sm">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="block px-3 py-2 rounded hover:bg-gray-800"
          active-class="bg-gray-800 text-white"
        >
          {{ link.label }}
        </RouterLink>
      </nav>
      <button @click="logout" class="m-3 px-3 py-2 rounded bg-gray-800 hover:bg-gray-700 text-left text-sm">
        Logout
      </button>
    </aside>
    <div class="flex-1 flex flex-col min-w-0">
      <header v-if="loggedIn" class="bg-white border-b px-6 py-3 flex items-center justify-between">
        <h1 class="font-semibold text-gray-800">Dashboard</h1>
        <span class="text-xs text-gray-500">API: {{ apiBase }}</span>
      </header>
      <main class="flex-1 p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const links = [
  { to: '/chat', label: 'Chat' },
  { to: '/documents', label: 'Documents' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/staff', label: 'Staff' },
  { to: '/audit', label: 'Audit' }
]
const loggedIn = computed(() => route.path !== '/login' || !!localStorage.getItem('access_token'))
const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  router.push('/login')
}
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <aside
      v-if="loggedIn"
      class="w-60 shrink-0 h-screen sticky top-0 flex flex-col overflow-y-auto text-slate-200 bg-gradient-to-b from-slate-950 via-slate-900 to-indigo-950"
    >
      <div class="px-5 py-4 flex items-center gap-2.5 border-b border-white/10">
        <span class="grid place-items-center w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 shadow-pop text-white font-bold">S</span>
        <div class="leading-tight">
          <p class="text-white font-bold">Synapse RAG</p>
          <p class="text-[11px] text-slate-400">Knowledge assistant</p>
        </div>
      </div>
      <nav class="flex-1 p-3 space-y-1 text-sm" aria-label="Primary">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
          active-class="!bg-indigo-600 !text-white shadow-pop"
        >
          <span class="w-4 h-4 shrink-0" v-html="link.icon" aria-hidden="true"></span>
          {{ link.label }}
        </RouterLink>
      </nav>
      <button
        @click="logout"
        class="m-3 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-left text-sm transition-colors"
      >
        Logout
      </button>
    </aside>
    <div class="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
      <header
        v-if="loggedIn"
        class="bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0"
      >
        <h1 class="font-semibold text-slate-800">{{ pageTitle }}</h1>
        <span class="text-xs text-slate-400">API: {{ apiBase }}</span>
      </header>
      <main class="flex-1 overflow-y-auto p-6 pb-24">
        <RouterView />
      </main>
    </div>
    <button
      v-if="showFab"
      ref="fabBtn"
      type="button"
      @click="togglePopup"
      :aria-expanded="popupOpen"
      aria-controls="chat-popup"
      aria-label="Open chat"
      class="fixed bottom-6 right-6 z-20 grid place-items-center w-14 h-14 rounded-full bg-indigo-600 text-white shadow-pop hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
      style="margin-bottom: env(safe-area-inset-bottom)"
    >
      <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 5.5A2.5 2.5 0 0 1 5.5 3h9A2.5 2.5 0 0 1 17 5.5v6a2.5 2.5 0 0 1-2.5 2.5H8l-4 3.5v-12Z"/></svg>
    </button>
    <div v-if="popupOpen && route.path !== '/chat'" id="chat-popup" role="dialog" aria-modal="false" aria-label="Chat" class="fixed bottom-24 right-6 z-30 w-[min(22rem,calc(100vw-2rem))] h-[32rem] max-h-[75vh] flex flex-col shadow-2xl shadow-indigo-950/20 rounded-2xl bg-white overflow-hidden border border-slate-200" @keydown.esc="closePopup">
      <div class="flex items-center gap-2.5 px-4 py-3 shrink-0 border-b border-slate-100 bg-gradient-to-r from-indigo-50/80 to-white">
        <span class="grid place-items-center w-8 h-8 rounded-full bg-indigo-600 text-white shrink-0"><svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 5.5A2.5 2.5 0 0 1 5.5 3h9A2.5 2.5 0 0 1 17 5.5v6a2.5 2.5 0 0 1-2.5 2.5H8l-4 3.5v-12Z"/></svg></span>
        <span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-slate-800">Chat</span><span class="block text-[11px] text-emerald-600"><span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 align-middle"></span>Online</span></span>
        <button type="button" @click="closePopup" aria-label="Close chat" class="grid place-items-center w-8 h-8 rounded-full hover:bg-slate-100 text-slate-500 text-lg leading-none">×</button>
      </div>
      <div class="flex-1 overflow-hidden min-h-0 flex flex-col">
        <ChatBox />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ChatBox from './components/ChatBox.vue'

const router = useRouter()
const route = useRoute()
const links = [
  { to: '/chat', label: 'Chat', icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 5.5A2.5 2.5 0 0 1 5.5 3h9A2.5 2.5 0 0 1 17 5.5v6a2.5 2.5 0 0 1-2.5 2.5H8l-4 3.5v-12Z"/></svg>' },
  { to: '/documents', label: 'Documents', icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 2.5h6l4 4v11H5z"/><path d="M11 2.5v4h4"/></svg>' },
  { to: '/accounts', label: 'Accounts', icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10" cy="6.5" r="3"/><path d="M3.5 17c1-3.5 3.5-5 6.5-5s5.5 1.5 6.5 5"/></svg>' },
  { to: '/staff', label: 'Staff', icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="7" cy="7" r="2.5"/><circle cx="13.5" cy="8" r="2"/><path d="M2.5 16c.8-2.8 2.5-4 4.5-4s3.7 1.2 4.5 4M11.5 12.5c2 .2 3.4 1.3 4 3.5"/></svg>' },
  { to: '/audit', label: 'Audit', icon: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 2.5 3 5v5c0 4.5 3 7 7 7.5 4-.5 7-3 7-7.5V5z"/><path d="m7.5 10 1.8 1.8L12.8 8"/></svg>' }
]
const titles = { '/chat': 'Chat', '/documents': 'Documents', '/accounts': 'Accounts', '/staff': 'Staff', '/audit': 'Audit trail' }
const pageTitle = computed(() => titles[route.path] || 'Dashboard')
const showFab = computed(() => loggedIn.value && route.path !== '/chat')
const popupOpen = ref(false)
const fabBtn = ref(null)
function togglePopup() {
  popupOpen.value = !popupOpen.value
  if (popupOpen.value) nextTick(() => document.querySelector('#chat-popup textarea')?.focus())
}
function closePopup() {
  popupOpen.value = false
  fabBtn.value?.focus()
}
watch(() => route.path, () => { popupOpen.value = false })
const loggedIn = computed(() => route.path !== '/login' && !!localStorage.getItem('access_token'))
const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  router.push('/login')
}
</script>

<template>
  <button
    type="button"
    @click="cycle"
    :aria-label="label"
    :title="label"
    :data-theme="mode"
    class="shrink-0 grid place-items-center w-11 h-11 rounded-full border border-slate-200 bg-white/70 text-slate-600 hover:bg-slate-100 hover:text-indigo-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-indigo-300"
  >
    <svg v-if="mode === 'light'" viewBox="0 0 20 20" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      <circle cx="10" cy="10" r="3.5" /><path d="M10 2v1.5M10 16.5V18M2 10h1.5M16.5 10H18M4.4 4.4l1 1M14.6 14.6l1 1M15.6 4.4l-1 1M5.4 14.6l-1 1" stroke-linecap="round" />
    </svg>
    <svg v-else-if="mode === 'dark'" viewBox="0 0 20 20" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      <path d="M16.5 12.8A7 7 0 0 1 7.2 3.5 7 7 0 1 0 16.5 12.8Z" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <svg v-else viewBox="0 0 20 20" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      <rect x="2.5" y="3.5" width="15" height="10" rx="1.5" /><path d="M7 17h6M10 13.5V17" stroke-linecap="round" />
    </svg>
  </button>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const MODES = ['light', 'dark', 'system']
const NAMES = { light: 'Light', dark: 'Dark', system: 'System' }
const query = window.matchMedia('(prefers-color-scheme: dark)')

// The .dark class is the same for 'dark' and 'system'+OS-dark — mode must come from the stored preference.
function readMode() {
  try {
    const stored = localStorage.getItem('theme')
    if (MODES.includes(stored)) return stored
  } catch {}
  return 'system'
}
function isDark(m) {
  return m === 'dark' || (m === 'system' && query.matches)
}
function apply() {
  const dark = isDark(mode.value)
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
  document.documentElement.dataset.theme = mode.value
}

const mode = ref(readMode())
const label = computed(() => {
  const next = MODES[(MODES.indexOf(mode.value) + 1) % MODES.length]
  return `Theme: ${NAMES[mode.value]}. Switch to ${NAMES[next]}`
})

function cycle() {
  mode.value = MODES[(MODES.indexOf(mode.value) + 1) % MODES.length]
  try { localStorage.setItem('theme', mode.value) } catch {}
  apply()
}
function onSchemeChange() {
  if (mode.value === 'system') apply()
}

onMounted(() => {
  apply()
  if (query.addEventListener) query.addEventListener('change', onSchemeChange)
  else query.addListener(onSchemeChange)
})
onUnmounted(() => {
  if (query.removeEventListener) query.removeEventListener('change', onSchemeChange)
  else query.removeListener(onSchemeChange)
})
</script>

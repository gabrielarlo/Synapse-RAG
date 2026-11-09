<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold text-slate-800">Documents</h2>
      <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">{{ docs.length }} file{{ docs.length === 1 ? '' : 's' }}</span>
    </div>
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <select v-model="accountId" aria-label="Account" class="border border-slate-200 rounded-full px-4 py-2.5 bg-white focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400">
        <option value="">Select account</option>
        <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <label class="flex items-center gap-1.5 text-sm text-slate-600">
        <input type="checkbox" v-model="internal" class="w-4 h-4 accent-indigo-600" /> internal
      </label>
      <input ref="fileInput" type="file" @change="onFile" aria-label="File" class="text-sm text-slate-600 file:mr-2 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200" />
      <button @click="upload" :disabled="!file" class="bg-indigo-600 text-white rounded-lg px-4 py-2 hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium">
        Upload
      </button>
      <button @click="load" class="bg-slate-100 rounded-lg px-4 py-2 hover:bg-slate-200 transition-colors text-sm">Refresh</button>
    </div>
    <p v-if="error" class="text-sm text-red-600 mb-2" role="alert">{{ error }}</p>
    <p v-if="msg" class="text-sm text-green-600 mb-2" role="status">{{ msg }}</p>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-slate-400 border-b border-slate-100"><th class="py-2 font-medium">File</th><th class="font-medium">Scope</th><th class="font-medium">Version</th><th class="font-medium">Category</th><th class="font-medium">Status</th><th class="font-medium text-right">Actions</th></tr></thead>
      <tbody>
        <tr v-for="d in docs" :key="d.id" class="border-b border-slate-100 last:border-0 hover:bg-slate-50/70 transition-colors">
          <td class="py-2.5 font-medium text-slate-700">{{ d.filename }}</td>
          <td class="text-slate-500">{{ d.scope || (d.account_id || 'internal') }}</td>
          <td class="text-slate-500 tabular-nums">v{{ d.version ?? 1 }}</td>
          <td>
            <span v-if="d.category" class="px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700">{{ d.category }}</span>
            <span v-else class="text-slate-300">—</span>
          </td>
          <td><span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="d.status === 'ready' ? 'bg-emerald-50 text-emerald-700' : d.status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'">{{ d.status }}</span>
            <p v-if="d.status === 'failed'" class="text-xs text-red-600 mt-1 max-w-xs truncate" :title="d.error || 'Processing failed with no further detail.'">{{ d.error || 'Processing failed with no further detail.' }}</p>
          </td>
          <td class="text-right whitespace-nowrap">
            <button @click="openView(d.id, $event)" class="text-slate-600 hover:text-slate-900 text-xs font-medium px-2 py-1 rounded hover:bg-slate-100 transition-colors">View</button>
            <button @click="pickReplace(d.id)" class="text-indigo-600 hover:text-indigo-800 text-xs font-medium px-2 py-1 rounded hover:bg-indigo-50 transition-colors">Replace</button>
            <button @click="remove(d)" class="text-red-600 hover:text-red-800 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
    <input ref="replaceInput" type="file" class="hidden" aria-hidden="true" tabindex="-1" @change="onReplaceFile" />

    <div
      v-if="viewOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-slate-900/50 p-4"
      @click.self="closeView"
    >
      <div
        ref="viewCard"
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-view-title"
        class="bg-white rounded-2xl shadow-pop w-full max-w-2xl max-h-[85vh] flex flex-col"
        @keydown.tab="trapTab"
      >
        <div class="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-100">
          <div class="min-w-0">
            <h3 id="doc-view-title" class="font-semibold text-slate-800 truncate">{{ viewing?.filename || 'Document' }}</h3>
            <p v-if="viewing" class="text-xs text-slate-400 mt-0.5">
              {{ viewing.account_id || 'internal' }} · v{{ viewing.version ?? 1 }} · {{ viewing.chunk_count }} chunk{{ viewing.chunk_count === 1 ? '' : 's' }}
            </p>
          </div>
          <button ref="viewClose" @click="closeView" aria-label="Close document view" class="shrink-0 text-slate-400 hover:text-slate-700 rounded-lg px-2 py-1 hover:bg-slate-100 transition-colors">✕</button>
        </div>
        <div class="px-5 py-4 overflow-y-auto scroll-slim space-y-4">
          <p v-if="viewingError" class="text-sm text-red-600" role="alert">{{ viewingError }}</p>
          <div v-else-if="!viewing" class="text-sm text-slate-400">Loading…</div>
          <template v-else>
            <dl class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
              <div><dt class="text-xs text-slate-400">Status</dt><dd class="text-slate-700">{{ viewing.status }}</dd></div>
              <div><dt class="text-xs text-slate-400">Category</dt><dd class="text-slate-700">{{ viewing.category || '—' }}</dd></div>
              <div><dt class="text-xs text-slate-400">Version</dt><dd class="text-slate-700">v{{ viewing.version ?? 1 }}</dd></div>
              <div><dt class="text-xs text-slate-400">Scope</dt><dd class="text-slate-700">{{ viewing.account_id || 'internal' }}</dd></div>
              <div><dt class="text-xs text-slate-400">Uploaded by</dt><dd class="text-slate-700 truncate">{{ viewing.uploaded_by || '—' }}</dd></div>
              <div><dt class="text-xs text-slate-400">Created</dt><dd class="text-slate-700">{{ timeAgo(viewing.created_at) }}</dd></div>
              <div><dt class="text-xs text-slate-400">Updated</dt><dd class="text-slate-700">{{ timeAgo(viewing.updated_at) }}</dd></div>
            </dl>
            <p v-if="viewing.error" class="text-sm text-red-600">{{ viewing.error }}</p>
            <div>
              <p class="text-xs text-slate-400 mb-1.5">
                Extracted text
                <span v-if="viewing.truncated">— showing {{ viewing.chunks.length }} of {{ viewing.chunk_count }} chunks</span>
              </p>
              <pre class="text-xs leading-relaxed whitespace-pre-wrap break-words bg-slate-50 border border-slate-200 rounded-xl p-3 max-h-72 overflow-y-auto scroll-slim text-slate-700">{{ viewing.chunks.join('\n\n') || '(no extracted text)' }}</pre>
            </div>
          </template>
        </div>
      </div>
    </div>
    <p v-if="!docs.length" class="text-sm text-slate-400 mt-3">No documents.</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { api, currentRole, errorDetail } from '../api.js'

const accounts = ref([])
const docs = ref([])
const accountId = ref('')
const internal = ref(currentRole() !== 'staff')
const file = ref(null)
const fileInput = ref(null)
const error = ref('')
const msg = ref('')
const replaceInput = ref(null)
const replaceTarget = ref(null)
const viewOpen = ref(false)
const viewing = ref(null)
const viewingError = ref('')
const viewCard = ref(null)
const viewClose = ref(null)
let lastFocused = null
let pollTimer = null

function scopeParams() {
  return internal.value ? { internal: true } : accountId.value ? { account_id: accountId.value } : null
}

function isPending() {
  return docs.value.some((d) => d.status !== 'ready' && d.status !== 'failed')
}

function timeAgo(ts) {
  if (!ts) return '—'
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return '—'
  const sec = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (sec < 60) return 'moments ago'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} minute${min === 1 ? '' : 's'} ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} hour${hr === 1 ? '' : 's'} ago`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} day${day === 1 ? '' : 's'} ago`
  const mo = Math.floor(day / 30)
  if (mo < 12) return `${mo} month${mo === 1 ? '' : 's'} ago`
  const yr = Math.floor(day / 365)
  return `${yr} year${yr === 1 ? '' : 's'} ago`
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function quietLoad() {
  const params = scopeParams()
  if (!params) return
  try {
    const { data } = await api.listDocuments(params)
    docs.value = data
  } catch { /* keep last state; next tick retries */ }
  if (!isPending()) stopPoll()
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(quietLoad, 3000)
}

function syncPoll() {
  if (isPending()) startPoll()
  else stopPoll()
}

async function load() {
  error.value = ''
  const params = scopeParams()
  if (!params) {
    error.value = 'Select an account or internal.'
    return
  }
  try {
    const { data } = await api.listDocuments(params)
    docs.value = data
    syncPoll()
  } catch (e) {
    error.value = errorDetail(e, 'Failed to load documents.')
  }
}

function onFile(e) {
  file.value = e.target.files[0] || null
}

async function upload() {
  error.value = ''
  msg.value = ''
  const params = scopeParams()
  if (!params) {
    error.value = 'Select an account or internal.'
    return
  }
  if (!file.value) return
  // Same name already in this scope: offer a new version instead of a twin.
  const existing = docs.value.find((d) => d.filename === file.value.name)
  if (existing && !window.confirm(
    `"${file.value.name}" already exists (v${existing.version ?? 1}). Upload as a newer version?`
  )) return
  try {
    const { data } = existing
      ? await api.replaceDocument(existing.id, file.value)
      : await api.uploadDocument(file.value, params)
    msg.value = existing
      ? `Updated ${file.value.name} → v${data.version}, re-queued.`
      : `Queued (job ${data.job_id}, ${data.status}).`
    file.value = null
    if (fileInput.value) fileInput.value.value = '' // allow re-selecting same file
    await load()
    if (isPending()) startPoll()
  } catch (e) {
    error.value = errorDetail(e, 'Upload failed.')
  }
}

function pickReplace(id) {
  replaceTarget.value = id
  replaceInput.value?.click()
}

function openView(id, event) {
  lastFocused = event?.currentTarget || document.activeElement
  viewOpen.value = true
  viewing.value = null
  viewingError.value = ''
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onViewKey)
  api.getDocument(id)
    .then(({ data }) => { viewing.value = data })
    .catch((e) => { viewingError.value = errorDetail(e, 'Failed to load document.') })
    .finally(() => nextTick(() => viewClose.value?.focus()))
}

function closeView() {
  viewOpen.value = false
  viewing.value = null
  viewingError.value = ''
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onViewKey)
  lastFocused?.focus?.()
  lastFocused = null
}

function onViewKey(e) {
  if (e.key === 'Escape') closeView()
}

function trapTab(e) {
  const el = viewCard.value
  if (!el) return
  const items = el.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

async function onReplaceFile(e) {
  const f = e.target.files?.[0]
  const id = replaceTarget.value
  e.target.value = ''
  replaceTarget.value = null
  if (!f || !id) return
  error.value = ''
  msg.value = ''
  try {
    const { data } = await api.replaceDocument(id, f)
    msg.value = `Replaced with ${f.name} → v${data.version}, re-queued.`
    await load()
    if (isPending()) startPoll()
  } catch (err) {
    error.value = errorDetail(err, 'Replace failed.')
  }
}

async function remove(d) {
  if (!window.confirm(`Delete "${d.filename}" and its vectors? This cannot be undone.`)) return
  error.value = ''
  msg.value = ''
  try {
    await api.deleteDocument(d.id)
    msg.value = `Deleted ${d.filename}.`
    await load()
  } catch (err) {
    error.value = errorDetail(err, 'Delete failed.')
  }
}

onMounted(async () => {
  try {
    const { data } = await api.listAccounts()
    accounts.value = data
  } catch { /* scoped users may still chat; ignore */ }
  if (scopeParams()) await load()
})

watch([accountId, internal], async () => {
  stopPoll()
  await load()
})

onUnmounted(() => {
  stopPoll()
  window.removeEventListener('keydown', onViewKey)
  document.body.style.overflow = ''
})
</script>

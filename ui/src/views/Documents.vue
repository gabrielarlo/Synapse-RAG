<template>
  <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-4 sm:p-6 flex flex-col min-h-0">
    <div class="flex items-start justify-between gap-3 mb-4">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-slate-800">Documents</h2>
        <p class="text-xs text-slate-400 mt-0.5">Upload, version and inspect account or internal knowledge sources.</p>
      </div>
      <span class="shrink-0 text-xs px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium tabular-nums">{{ docs.length }} file{{ docs.length === 1 ? '' : 's' }}</span>
    </div>

    <div class="flex flex-col gap-3 mb-4">
      <div class="flex flex-col sm:flex-row gap-2 sm:items-center">
        <select v-model="accountId" aria-label="Account" class="flex-1 min-w-0 min-h-11 border border-slate-200 rounded-full px-4 py-2.5 bg-white text-sm focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400">
          <option value="">Select account</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <label class="flex items-center gap-1.5 text-sm text-slate-600 min-h-11 shrink-0">
          <input type="checkbox" v-model="internal" class="w-4 h-4 accent-indigo-600" /> internal
        </label>
        <button @click="load" :disabled="loadingDocs" class="min-h-11 bg-slate-100 rounded-full px-4 py-2 hover:bg-slate-200 transition-colors text-sm font-medium disabled:opacity-50 inline-flex items-center gap-2 shrink-0">
          <svg v-if="loadingDocs" viewBox="0 0 20 20" class="w-4 h-4 animate-spin text-slate-500" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
          Refresh
        </button>
      </div>

      <div
        @dragover.prevent="onDragOver"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        :class="['border-2 border-dashed rounded-xl px-4 py-4 flex flex-col sm:flex-row items-start sm:items-center gap-3 transition-colors', dragOver ? 'border-indigo-300 bg-indigo-50/60' : 'border-slate-200 bg-slate-50/50 hover:bg-slate-50']"
      >
        <div class="grid place-items-center w-10 h-10 rounded-xl bg-white border border-slate-200 text-indigo-600 shrink-0" aria-hidden="true">
          <svg viewBox="0 0 20 20" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 3.5v9M6.5 9.5l3.5 3.5 3.5-3.5"/><path d="M3.5 14.5v1A1.5 1.5 0 0 0 5 17h10a1.5 1.5 0 0 0 1.5-1.5v-1" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-slate-700">Drop a file here or <label for="doc-file" class="text-indigo-600 hover:text-indigo-700 underline cursor-pointer">browse</label></p>
          <p class="text-xs text-slate-400 truncate">{{ file ? file.name + ' · ' + (file.size > 1024*1024 ? (file.size/1024/1024).toFixed(1)+' MB' : (file.size/1024).toFixed(0)+' KB') : 'PDF, text, markdown — max 10 MB' }}</p>
        </div>
        <input id="doc-file" ref="fileInput" type="file" @change="onFile" class="sr-only" aria-label="Choose file to upload" />
        <div class="flex gap-2 shrink-0 w-full sm:w-auto">
          <label for="doc-file" class="flex-1 sm:flex-none min-h-11 grid place-items-center rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 cursor-pointer">Choose file</label>
          <button @click="upload" :disabled="!file || uploading" class="flex-1 sm:flex-none min-h-11 bg-indigo-600 text-white rounded-full px-5 py-2 hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2">
            <svg v-if="uploading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            {{ uploading ? 'Uploading…' : 'Upload' }}
          </button>
        </div>
      </div>
      <p v-if="file" class="text-xs text-slate-500">
        Selected: <span class="font-medium text-slate-700">{{ file.name }}</span>
        <button @click="clearFile" class="ml-2 text-slate-400 hover:text-slate-600 underline">Clear</button>
      </p>
    </div>

    <div v-if="error" class="flex items-start gap-2 bg-red-50 border border-red-100 text-red-700 rounded-xl px-3 py-2.5 mb-3" role="alert">
      <span class="shrink-0 mt-0.5" aria-hidden="true">⚠</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ error }}</p>
      <button @click="error=''" aria-label="Dismiss error" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-red-100">✕</button>
    </div>
    <div v-if="msg" class="flex items-start gap-2 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-xl px-3 py-2.5 mb-3" role="status">
      <span class="shrink-0 mt-0.5" aria-hidden="true">✓</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ msg }}</p>
      <button @click="msg=''" aria-label="Dismiss message" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-emerald-100">✕</button>
    </div>

    <div v-if="!docs.length && !error" class="grid place-items-center text-center py-10 border border-dashed border-slate-200 rounded-xl bg-slate-50/50">
      <div class="grid place-items-center w-12 h-12 rounded-xl bg-white border border-slate-200 text-indigo-400 mb-3" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 2.5h6l4 4v11H5z"/><path d="M11 2.5v4h4" stroke-linecap="round" stroke-linejoin="round"/><path d="M7 11h6M7 14h4" stroke-linecap="round"/></svg>
      </div>
      <p class="text-sm font-medium text-slate-600">No documents</p>
      <p class="text-xs text-slate-400 mt-1 max-w-sm">Choose a scope above and upload a file, or drop it in the zone. Supported files are chunked and indexed for retrieval.</p>
    </div>

    <template v-if="docs.length">
      <div class="hidden md:block overflow-x-auto rounded-xl border border-slate-100">
        <table class="w-full text-sm">
          <caption class="sr-only">Documents for selected scope</caption>
          <thead class="bg-slate-50 text-left text-slate-500 border-b border-slate-100">
            <tr>
              <th scope="col" class="py-2.5 px-3 font-medium">File</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Scope</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Version</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Category</th>
              <th scope="col" class="py-2.5 px-3 font-medium">Status</th>
              <th scope="col" class="py-2.5 px-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in docs" :key="d.id" class="border-b border-slate-100 last:border-0 hover:bg-slate-50/70 transition-colors">
              <td class="py-2.5 px-3 font-medium text-slate-700">
                <span class="truncate max-w-[16rem] inline-block align-middle" :title="d.filename">{{ d.filename }}</span>
              </td>
              <td class="py-2.5 px-3 text-slate-500 truncate max-w-[10rem]" :title="d.scope || (d.account_id || 'internal')">{{ d.scope || (d.account_id || 'internal') }}</td>
              <td class="py-2.5 px-3 text-slate-500 tabular-nums">v{{ d.version ?? 1 }}</td>
              <td class="py-2.5 px-3">
                <span v-if="d.category" class="px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700">{{ d.category }}</span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="py-2.5 px-3">
                <span class="px-2 py-1 rounded-full text-xs font-medium" :class="d.status === 'ready' ? 'bg-emerald-50 text-emerald-700' : d.status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'">{{ d.status }}</span>
                <p v-if="d.status === 'failed'" class="text-xs text-red-600 mt-1 max-w-xs truncate" :title="d.error || 'Processing failed with no further detail.'">{{ d.error || 'Processing failed.' }}</p>
              </td>
              <td class="py-2.5 px-3 text-right">
                <div class="inline-flex items-center gap-1.5">
                  <button @click="openView(d.id, $event)" :aria-label="`View ${d.filename}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">View</button>
                  <button @click="pickReplace(d.id)" :aria-label="`Replace ${d.filename}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-indigo-100 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">Replace</button>
                  <button @click="openTransfer(d)" :aria-label="`Transfer ${d.filename}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-amber-100 bg-amber-50 text-amber-700 hover:bg-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-600">Transfer</button>
                  <button @click="requestDelete(d)" :aria-label="`Delete ${d.filename}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-red-100 bg-red-50 text-red-700 hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">Delete</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <ul class="md:hidden space-y-3" role="list" aria-label="Documents">
        <li v-for="d in docs" :key="d.id" class="border border-slate-200 rounded-xl p-3 bg-white">
          <div class="flex items-start justify-between gap-2">
            <p class="font-medium text-slate-800 text-sm truncate min-w-0 flex-1" :title="d.filename">{{ d.filename }}</p>
            <span class="px-2 py-0.5 rounded-full text-xs font-medium shrink-0" :class="d.status === 'ready' ? 'bg-emerald-50 text-emerald-700' : d.status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'">{{ d.status }}</span>
          </div>
          <dl class="mt-2 grid grid-cols-2 gap-2 text-xs">
            <div><dt class="text-slate-400">Scope</dt><dd class="text-slate-600 truncate">{{ d.scope || (d.account_id || 'internal') }}</dd></div>
            <div><dt class="text-slate-400">Version</dt><dd class="text-slate-600 tabular-nums">v{{ d.version ?? 1 }}</dd></div>
            <div><dt class="text-slate-400">Category</dt><dd class="text-slate-600 truncate">{{ d.category || '—' }}</dd></div>
            <div><dt class="text-slate-400">Status</dt><dd class="text-slate-600 truncate">{{ d.status }}</dd></div>
          </dl>
          <p v-if="d.status === 'failed'" class="text-xs text-red-600 mt-2 break-words">{{ d.error || 'Processing failed.' }}</p>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <button @click="openView(d.id, $event)" :aria-label="`View ${d.filename}`" class="min-h-11 rounded-full border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">View</button>
            <button @click="pickReplace(d.id)" :aria-label="`Replace ${d.filename}`" class="min-h-11 rounded-full border border-indigo-100 bg-indigo-50 text-xs font-medium text-indigo-700 hover:bg-indigo-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">Replace</button>
            <button @click="openTransfer(d)" :aria-label="`Transfer ${d.filename}`" class="min-h-11 rounded-full border border-amber-100 bg-amber-50 text-xs font-medium text-amber-700 hover:bg-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-600">Transfer</button>
            <button @click="requestDelete(d)" :aria-label="`Delete ${d.filename}`" class="min-h-11 rounded-full border border-red-100 bg-red-50 text-xs font-medium text-red-700 hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">Delete</button>
          </div>
        </li>
      </ul>
    </template>

    <input ref="replaceInput" type="file" class="hidden" aria-hidden="true" tabindex="-1" @change="onReplaceFile" />

    <dialog ref="viewDialog" class="p-0 bg-transparent max-w-none w-full max-h-none h-full backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4 overscroll-contain" @close="onViewClosed" @click="onViewBackdropClick">
      <div class="bg-white rounded-2xl shadow-pop w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        <div class="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-100">
          <div class="min-w-0">
            <h3 id="doc-view-title" class="font-semibold text-slate-800 truncate">{{ viewing?.filename || 'Document' }}</h3>
            <p v-if="viewing" class="text-xs text-slate-400 mt-0.5">
              {{ viewing.account_id || 'internal' }} · v{{ viewing.version ?? 1 }} · {{ viewing.chunk_count }} chunk{{ viewing.chunk_count === 1 ? '' : 's' }}
            </p>
          </div>
          <button @click="closeView" aria-label="Close document view" class="shrink-0 grid place-items-center w-10 h-10 rounded-full hover:bg-slate-100 text-slate-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">✕</button>
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
        <div class="px-5 py-3 border-t border-slate-100 flex justify-end">
          <button @click="closeView" class="min-h-11 rounded-full bg-slate-900 text-white px-5 py-2 text-sm font-medium hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">Close</button>
        </div>
      </div>
    </dialog>

    <dialog ref="confirmDialog" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onConfirmClosed">
      <form method="dialog" class="bg-white rounded-2xl shadow-pop w-full max-w-md p-5">
        <h3 class="font-semibold text-slate-800">{{ confirmTitle }}</h3>
        <p class="text-sm text-slate-600 mt-1.5 break-words">{{ confirmMessage }}</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelConfirm" class="min-h-11 rounded-full border border-slate-200 bg-white px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600" autofocus>Cancel</button>
          <button type="button" @click="doConfirm" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" :class="confirmVariant === 'danger' ? 'bg-red-600 text-white hover:bg-red-700 focus-visible:outline-red-600' : 'bg-indigo-600 text-white hover:bg-indigo-700 focus-visible:outline-indigo-600'">{{ confirmActionLabel }}</button>
        </div>
      </form>
    </dialog>

    <dialog ref="transferDialog" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onTransferClosed">
      <form method="dialog" class="bg-white rounded-2xl shadow-pop w-full max-w-md p-5" @submit.prevent="doTransfer">
        <h3 class="font-semibold text-slate-800">Transfer document</h3>
        <p class="text-sm text-slate-600 mt-1.5 break-words">Move "{{ transferDoc?.filename }}" to another account you have access to.</p>
        <label class="block mt-4 text-sm font-medium text-slate-700">Target account
          <select v-model="transferTarget" class="mt-1 w-full min-h-11 border border-slate-200 rounded-full px-4 py-2.5 bg-white text-sm focus:border-indigo-500">
            <option value="">Select account</option>
            <option v-for="a in transferOptions" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
        </label>
        <p v-if="transferOptions.length === 0" class="text-xs text-amber-600 mt-2">No other accounts available.</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="closeTransfer" class="min-h-11 rounded-full border border-slate-200 bg-white px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Cancel</button>
          <button type="submit" :disabled="!transferTarget || transferring" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 inline-flex items-center gap-2">
            <svg v-if="transferring" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Transfer
          </button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
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
const viewing = ref(null)
const viewingError = ref('')
const viewDialog = ref(null)
let lastFocused = null
let pollTimer = null
const loadingDocs = ref(false)
const uploading = ref(false)
const dragOver = ref(false)
const confirmDialog = ref(null)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmActionLabel = ref('')
const confirmVariant = ref('danger')
let confirmAction = null
let pendingDuplicate = null
const transferDialog = ref(null)
const transferDoc = ref(null)
const transferTarget = ref('')
const transferring = ref(false)
const transferOptions = computed(() => accounts.value.filter(a => a.id !== transferDoc.value?.account_id))

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
  loadingDocs.value = true
  try {
    const { data } = await api.listDocuments(params)
    docs.value = data
    syncPoll()
  } catch (e) {
    error.value = errorDetail(e, 'Failed to load documents.')
  } finally {
    loadingDocs.value = false
  }
}

function clearFile() {
  file.value = null
  pendingDuplicate = null
  if (fileInput.value) fileInput.value.value = ''
}

function onFile(e) {
  file.value = e.target.files[0] || null
  pendingDuplicate = null
}

function onDragOver() {
  dragOver.value = true
}

function onDrop(e) {
  dragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) {
    file.value = f
    pendingDuplicate = null
  }
}

async function doUpload(existing) {
  uploading.value = true
  try {
    const params = scopeParams()
    const { data } = existing
      ? await api.replaceDocument(existing.id, file.value)
      : await api.uploadDocument(file.value, params)
    msg.value = existing
      ? `Updated ${file.value.name} → v${data.version}, re-queued.`
      : `Queued (job ${data.job_id}, ${data.status}).`
    clearFile()
    await load()
    if (isPending()) startPoll()
  } catch (e) {
    error.value = errorDetail(e, 'Upload failed.')
  } finally {
    uploading.value = false
  }
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
  const existing = docs.value.find((d) => d.filename === file.value.name)
  if (existing) {
    pendingDuplicate = existing
    openConfirm({
      title: 'Update existing file?',
      message: `"${file.value.name}" already exists (v${existing.version ?? 1}). Upload as a newer version?`,
      actionLabel: 'Update',
      variant: 'default',
      action: () => {
        const ex = pendingDuplicate
        pendingDuplicate = null
        doUpload(ex)
      },
    })
    return
  }
  await doUpload(null)
}

function openConfirm({ title, message, actionLabel, variant = 'danger', action }) {
  confirmTitle.value = title
  confirmMessage.value = message
  confirmActionLabel.value = actionLabel
  confirmVariant.value = variant
  confirmAction = action
  nextTick(() => {
    try { confirmDialog.value?.showModal() } catch {}
  })
}

function cancelConfirm() {
  try { confirmDialog.value?.close() } catch {}
}

function doConfirm() {
  const fn = confirmAction
  try { confirmDialog.value?.close() } catch {}
  if (fn) fn()
}

function onConfirmClosed() {
  confirmAction = null
  pendingDuplicate = null
}

function pickReplace(id) {
  replaceTarget.value = id
  replaceInput.value?.click()
}

function openView(id, event) {
  lastFocused = event?.currentTarget || document.activeElement
  viewing.value = null
  viewingError.value = ''
  try { viewDialog.value?.showModal() } catch {}
  api.getDocument(id)
    .then(({ data }) => { viewing.value = data })
    .catch((e) => { viewingError.value = errorDetail(e, 'Failed to load document.') })
}

function closeView() {
  try { viewDialog.value?.close() } catch {}
}

function onViewClosed() {
  viewing.value = null
  viewingError.value = ''
  lastFocused?.focus?.()
  lastFocused = null
}

function onViewBackdropClick(e) {
  const dlg = viewDialog.value
  if (!dlg) return
  const r = dlg.getBoundingClientRect()
  const outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom
  if (outside) closeView()
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

function openTransfer(d) {
  transferDoc.value = d
  transferTarget.value = ''
  nextTick(() => { try { transferDialog.value?.showModal() } catch {} })
}
function closeTransfer() {
  try { transferDialog.value?.close() } catch {}
}
function onTransferClosed() {
  transferDoc.value = null
  transferTarget.value = ''
  transferring.value = false
}
async function doTransfer() {
  if (!transferDoc.value || !transferTarget.value) return
  transferring.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.transferDocument(transferDoc.value.id, transferTarget.value)
    const targetName = accounts.value.find(a => a.id === transferTarget.value)?.name || transferTarget.value
    msg.value = `Moved ${transferDoc.value.filename} to ${targetName}.`
    closeTransfer()
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Transfer failed.')
  } finally {
    transferring.value = false
  }
}

function requestDelete(d) {
  openConfirm({
    title: 'Delete document?',
    message: `Delete "${d.filename}" and its vectors? This cannot be undone.`,
    actionLabel: 'Delete',
    variant: 'danger',
    action: async () => {
      error.value = ''
      msg.value = ''
      try {
        await api.deleteDocument(d.id)
        msg.value = `Deleted ${d.filename}.`
        await load()
      } catch (err) {
        error.value = errorDetail(err, 'Delete failed.')
      }
    },
  })
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
})
</script>

<style scoped>
dialog:modal { overscroll-behavior: contain; }
dialog::backdrop { overscroll-behavior: contain; }
</style>

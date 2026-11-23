<template>
  <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-100 dark:border-slate-700 p-4 sm:p-6 flex flex-col gap-6">
    <div class="flex flex-col sm:flex-row items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100">External API</h2>
        <p class="text-xs text-slate-400 mt-0.5">Give third-party apps RAG answers scoped to one account — no internal credentials exposed.</p>
      </div>
      <div class="flex gap-2 shrink-0">
        <a :href="swaggerUrl" target="_blank" rel="noopener" class="min-h-11 inline-flex items-center gap-2 rounded-full bg-indigo-600 text-white px-5 py-2.5 hover:bg-indigo-700 text-sm font-medium">Swagger UI <span aria-hidden="true">↗</span></a>
        <a :href="openapiUrl" target="_blank" rel="noopener" class="min-h-11 inline-flex items-center gap-2 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">openapi.json</a>
      </div>
    </div>

    <div v-if="onlyStaff" class="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-400/20 rounded-xl px-3 py-2.5 text-sm text-amber-700 dark:text-amber-300">
      Staff accounts can chat and upload within assigned accounts. Only admins can issue API keys — ask your admin to create one for this account.
    </div>

    <div class="grid lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 space-y-4">
        <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-slate-50/50 dark:bg-slate-800/50">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">1. Get an API key (admin)</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Go to <RouterLink to="/accounts" class="underline text-indigo-600 dark:text-indigo-400">Accounts</RouterLink> → pick an account → <span class="font-medium">API Keys</span> → Issue. Copy the secret once — it is shown only at issuance and rotation.</p>
        </div>
        <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-slate-50/50 dark:bg-slate-800/50">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">2. Query the RAG</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">POST <code class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-0.5">/ext/faq</code> with <code>X-API-Key</code> + <code>X-API-Secret</code> headers. Stateless, per-key rate-limited ({{ faqRate }}) and scoped to the key's account only — <code>internal</code> docs are never returned and <code>audit:</code> is treated as literal text.</p>
          <div class="mt-3 grid gap-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-300">cURL</span>
              <button @click="copy(curlExample)" class="text-xs px-2 py-1 rounded-full border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-900">{{ copiedCurl ? 'Copied' : 'Copy' }}</button>
            </div>
            <pre class="overflow-x-auto text-xs bg-slate-950 text-slate-200 rounded-lg p-3">{{ curlExample }}</pre>
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-300">Python</span>
              <button @click="copy(pyExample)" class="text-xs px-2 py-1 rounded-full border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-900">{{ copiedPy ? 'Copied' : 'Copy' }}</button>
            </div>
            <pre class="overflow-x-auto text-xs bg-slate-950 text-slate-200 rounded-lg p-3">{{ pyExample }}</pre>
          </div>
        </div>
        <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">Where Swagger fits</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">All endpoints are listed in Swagger — try the external call from there with your key/secret in the header fields. Token management (<code>issue / list / rotate / revoke</code>) is under the <span class="font-medium">credentials</span> tag; the RAG call is <span class="font-medium">POST /ext/faq</span>.</p>
        </div>
      </div>
      <div class="space-y-3">
        <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">Headers</h3>
          <dl class="mt-2 space-y-2 text-xs">
            <div><dt class="font-mono font-medium">X-API-Key</dt><dd class="text-slate-500 dark:text-slate-400">key_id, e.g. sk_...</dd></div>
            <div><dt class="font-mono font-medium">X-API-Secret</dt><dd class="text-slate-500 dark:text-slate-400">plaintext secret from issuance/rotation</dd></div>
          </dl>
          <p class="text-xs text-slate-400 mt-3">Bearer JWTs are for the dashboard only — external callers never need them.</p>
        </div>
        <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-white dark:bg-slate-900">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">Response</h3>
          <pre class="mt-2 text-xs bg-slate-950 text-slate-200 rounded-lg p-3 overflow-x-auto">{
  "answer": "…grounded text…",
  "category": "external_faq"
}</pre>
          <p class="text-xs text-slate-400 mt-2">401 revoked/bad key·secret · 429 per-key rate-limited · 403 account archived · 503 model down.</p>
        </div>
        <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-indigo-50/50 dark:bg-indigo-500/10">
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100">Tip</h3>
          <p class="text-xs text-slate-600 dark:text-slate-300 mt-1">One key per integration. Rotate rather than sharing — old secret stops working on rotation.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { currentRole } from '../api.js'

const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const swaggerUrl = computed(() => `${base}/api/docs`)
const openapiUrl = computed(() => `${base}/openapi.json`)
const onlyStaff = computed(() => currentRole() === 'staff')
const faqRate = '60 req / 60s per key+IP'

const curlExample = `curl -X POST "${
  base || 'http://localhost:8000'
}/ext/faq" \\
  -H "X-API-Key: sk_..." \\
  -H "X-API-Secret: ..." \\
  -H "Content-Type: application/json" \\
  -d '{"question":"What is the refund policy?"}'`

const pyExample = `import requests
r = requests.post("${base || 'http://localhost:8000'}/ext/faq",
    headers={"X-API-Key": "sk_...", "X-API-Secret": "..."},
    json={"question": "What is the refund policy?"})
print(r.json()["answer"])`

const copiedCurl = ref(false)
const copiedPy = ref(false)
async function copy(text) {
  try { await navigator.clipboard.writeText(text) } catch {}
  const isCurl = text === curlExample
  if (isCurl) { copiedCurl.value = true; setTimeout(() => copiedCurl.value = false, 1200) }
  else { copiedPy.value = true; setTimeout(() => copiedPy.value = false, 1200) }
}
</script>

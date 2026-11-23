<template>
  <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-100 dark:border-slate-700 p-4 sm:p-6 flex flex-col gap-4">
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100">Accounts</h2>
        <p class="text-xs text-slate-400 mt-0.5">Create and manage account workspaces for scoped retrieval.</p>
      </div>
      <div class="flex items-center gap-2 shrink-0 self-start">
        <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-medium tabular-nums" aria-live="polite">{{ filteredAccounts.length }} of {{ accounts.length }} total</span>
        <button
          type="button"
          @click="openCreate"
          class="min-h-11 rounded-full bg-indigo-600 text-white px-5 py-2.5 hover:bg-indigo-700 transition-colors text-sm font-medium inline-flex items-center justify-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        >
          <svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 10V3M3 10h14" stroke-linecap="round"/></svg>
          New account
        </button>
      </div>
    </div>

    <dialog ref="createDialog" aria-labelledby="create-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onCreateClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5" @submit.prevent="create">
        <h3 id="create-title" class="font-semibold text-slate-800 dark:text-slate-100">New account</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Create a workspace to scope documents, chat and audit trails.</p>
        <label for="account-name" class="block mt-4 text-sm font-medium text-slate-700 dark:text-slate-200">Account name</label>
        <BaseInput
          id="account-name"
          ref="createNameInput"
          v-model="name"
          placeholder="e.g. Acme Corp"
          aria-label="Account name"
          :aria-describedby="nameError ? 'account-error' : 'account-help'"
          :aria-invalid="!!nameError"
          class="w-full mt-1"
          required
          autocomplete="off"
          @blur="touched = true"
        />
        <p id="account-help" class="text-xs text-slate-400 mt-1.5">2–64 characters. Letters, numbers, spaces, hyphens and underscores.</p>
        <p v-if="nameError" id="account-error" class="text-xs text-red-600 dark:text-red-400 mt-1" role="alert">{{ nameError }}</p>
        <p v-if="createError" class="text-sm text-red-600 dark:text-red-400 mt-2" role="alert">{{ createError }}</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelCreate" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">Cancel</button>
          <button type="submit" :disabled="!trimmedName || creating" class="min-h-11 rounded-full bg-indigo-600 text-white px-5 py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
            <svg v-if="creating" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            {{ creating ? 'Creating…' : 'Create' }}
          </button>
        </div>
      </form>
    </dialog>

    <div class="flex gap-2">
      <label for="account-search" class="sr-only">Search accounts</label>
      <div class="relative flex-1 min-w-0">
        <BaseInput ref="searchInput" id="account-search" v-model="search" placeholder="Search accounts…" aria-label="Search accounts" class="w-full pr-10" autofocus />
        <button
          v-if="search"
          @click="search = ''"
          aria-label="Clear search"
          class="absolute right-1 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        >✕</button>
      </div>
      <button @click="load" :disabled="loading" class="shrink-0 min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600">
        <svg v-if="loading" viewBox="0 0 20 20" class="w-4 h-4 animate-spin text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
        Refresh
      </button>
    </div>

    <div v-if="isAdmin" role="group" aria-label="Account status filter" class="flex gap-1 p-1 rounded-full bg-slate-100 dark:bg-slate-800 w-full sm:w-auto sm:self-start">
      <button
        type="button"
        :aria-pressed="statusFilter === 'active'"
        @click="statusFilter = 'active'"
        class="flex-1 sm:flex-none min-h-11 rounded-full px-4 py-2 text-sm font-medium inline-flex items-center justify-center gap-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        :class="statusFilter === 'active' ? 'bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
      >Active <span class="text-xs tabular-nums opacity-70">{{ activeCount }}</span></button>
      <button
        type="button"
        :aria-pressed="statusFilter === 'archived'"
        @click="statusFilter = 'archived'"
        class="flex-1 sm:flex-none min-h-11 rounded-full px-4 py-2 text-sm font-medium inline-flex items-center justify-center gap-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
        :class="statusFilter === 'archived' ? 'bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-300 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
      >Archived <span class="text-xs tabular-nums opacity-70">{{ archivedCount }}</span></button>
    </div>

    <div v-if="error" class="flex items-start gap-2 bg-red-50 dark:bg-red-500/15 border border-red-100 dark:border-white/10 text-red-700 dark:text-red-300 rounded-xl px-3 py-2.5" role="alert">
      <span class="shrink-0 mt-0.5" aria-hidden="true">⚠</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ error }}</p>
      <button @click="error=''" aria-label="Dismiss error" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-red-100 dark:hover:bg-red-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600">✕</button>
    </div>
    <div v-if="msg" class="flex items-start gap-2 bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-100 dark:border-white/10 text-emerald-700 dark:text-emerald-300 rounded-xl px-3 py-2.5" role="status">
      <span class="shrink-0 mt-0.5" aria-hidden="true">✓</span>
      <p class="text-sm flex-1 min-w-0 break-words">{{ msg }}</p>
      <button @click="msg=''" aria-label="Dismiss message" class="shrink-0 grid place-items-center w-8 h-8 -my-1 -mr-1 rounded-full hover:bg-emerald-100 dark:hover:bg-emerald-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600">✕</button>
    </div>

    <div v-if="loading && !accounts.length" class="space-y-2">
      <div v-for="i in 3" :key="i" class="animate-pulse flex items-center gap-3 border border-slate-100 dark:border-slate-700 rounded-xl p-3">
        <div class="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-800 shrink-0"></div>
        <div class="flex-1 min-w-0 space-y-2">
          <div class="h-3 bg-slate-100 dark:bg-slate-800 rounded w-1/3"></div>
          <div class="h-2.5 bg-slate-100 dark:bg-slate-800 rounded w-1/4"></div>
        </div>
        <div class="w-16 h-3 bg-slate-100 dark:bg-slate-800 rounded"></div>
      </div>
    </div>

    <ul v-else-if="filteredAccounts.length" class="space-y-2" role="list" aria-label="Accounts">
      <li v-for="a in filteredAccounts" :key="a.id" class="border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 flex items-center justify-between gap-3 hover:bg-slate-50/70 dark:hover:bg-slate-800/70 transition-colors">
        <span class="flex items-center gap-2.5 min-w-0 flex-1">
          <span class="grid place-items-center w-9 h-9 rounded-full bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 text-xs font-bold shrink-0" aria-hidden="true">{{ (a.name || '?').slice(0, 1).toUpperCase() }}</span>
          <span class="min-w-0">
            <span class="block font-medium text-slate-800 dark:text-slate-100 text-sm truncate" :title="a.name">{{ a.name }}</span>
            <span class="block text-xs text-slate-400 truncate">Created {{ a.created_at ? timeAgo(a.created_at) : 'recently' }}</span>
          </span>
        </span>
        <span class="flex items-center gap-1.5 shrink-0">
          <button
            v-if="isAdmin"
            type="button"
            @click="openKeys(a)"
            :aria-label="`API keys for ${a.name}`"
            :title="`API keys for ${a.name}`"
            class="min-h-9 inline-flex items-center gap-1.5 rounded-full border border-indigo-100 dark:border-white/10 bg-indigo-50 dark:bg-indigo-500/15 px-3 py-1.5 text-xs font-medium text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
          >
            <svg viewBox="0 0 20 20" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M5 10a2.5 2.5 0 0 1 2.5-2.5h3A2.5 2.5 0 0 1 13 10v2a2 2 0 0 1-2 2H7.5A2.5 2.5 0 0 1 5 11.5V10Z"/><path d="M8 7.5V6a2 2 0 0 1 4 0v1.5"/><circle cx="9.2" cy="11" r="0.9"/></svg>
            API Keys
          </button>
          <template v-if="isAdmin">
            <template v-if="a.is_archived">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0 bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300">Archived</span>
              <button
                type="button"
                :disabled="archiving"
                @click="unarchive(a)"
                :aria-label="`Unarchive ${a.name}`"
                :title="`Unarchive ${a.name}`"
                class="grid place-items-center w-9 h-9 rounded-full text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-500/15 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-600"
              >
                <svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M3 7.5h14v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9Z" />
                  <path d="M2.5 4.5h15v3h-15z" />
                  <path d="M10 16V9m0 0-2 2m2-2 2 2" />
                </svg>
              </button>
            </template>
            <button
              v-else
              type="button"
              :disabled="archiving"
              @click="askArchive(a)"
              :aria-label="`Archive ${a.name}`"
              :title="`Archive ${a.name}`"
              class="grid place-items-center w-9 h-9 rounded-full text-slate-400 hover:text-red-600 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-500/15 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-600"
            >
              <svg viewBox="0 0 20 20" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M3 7.5h14v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9Z" />
                <path d="M2.5 4.5h15v3h-15z" />
                <path d="M8 11h4" />
              </svg>
            </button>
          </template>
          <span v-else-if="!isAdmin" class="text-xs text-slate-400">—</span>
        </span>
      </li>
    </ul>

    <div v-else-if="search && !filteredAccounts.length" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No matches for “{{ search }}”</p>
      <p class="text-xs text-slate-400 mt-1">Try a different search or <button @click="search=''" class="underline hover:text-slate-600 dark:hover:text-slate-300">clear filter</button>.</p>
    </div>

    <div v-else-if="!accounts.length && !loading" class="grid place-items-center text-center py-10 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <div class="grid place-items-center w-12 h-12 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-indigo-400 mb-3" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="7" r="3"/><path d="M3.5 16a6.5 6.5 0 0 1 13 0"/></svg>
      </div>
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No accounts yet</p>
      <p class="text-xs text-slate-400 mt-1 max-w-sm">Use New account to create your first workspace. Accounts scope documents, chat and audit trails per tenant.</p>
    </div>

    <div v-else-if="!filteredAccounts.length" class="grid place-items-center text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/60">
      <p class="text-sm font-medium text-slate-600 dark:text-slate-300">No {{ statusFilter }} accounts</p>
      <p class="text-xs text-slate-400 mt-1">{{ statusFilter === 'archived' ? 'Archived accounts will appear here.' : 'All accounts are archived — switch to Archived to see them.' }}</p>
    </div>

    <dialog ref="archiveDialog" aria-labelledby="archive-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onArchiveClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5">
        <h3 id="archive-title" class="font-semibold text-slate-800 dark:text-slate-100">Archive account</h3>
        <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Archive “{{ archiveTarget?.name }}”? Its documents will be unavailable for chat, external FAQ and management until you unarchive it. No data is deleted.</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelArchive" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600" autofocus>Cancel</button>
          <button type="button" @click="confirmArchive" :disabled="archiving" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600">
            <svg v-if="archiving" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Archive
          </button>
        </div>
      </form>
    </dialog>

    <dialog ref="keysDialog" class="p-0 bg-transparent max-w-none w-full max-h-none h-full backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4 overscroll-contain" @close="onKeysClosed">
      <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        <div class="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-100 dark:border-slate-700">
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-800 dark:text-slate-100 truncate">API Keys — {{ keysAccount?.name }}</h3>
            <p class="text-xs text-slate-400 mt-0.5">Manage third-party keys for this account. Secrets are shown only once. Default expiry 90 days.</p>
            <RouterLink to="/api-docs" @click="keysDialog?.close()" class="text-xs text-indigo-600 dark:text-indigo-400 underline mt-1 inline-block">How to use → API Docs</RouterLink>
          </div>
          <button @click="closeKeys" aria-label="Close" class="shrink-0 grid place-items-center w-10 h-10 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400">✕</button>
        </div>
        <div class="px-5 py-4 overflow-y-auto space-y-3">
          <div v-if="lastSecret" class="border border-amber-200 dark:border-amber-400/30 bg-amber-50 dark:bg-amber-500/10 rounded-xl p-3">
            <p class="text-xs font-medium text-amber-800 dark:text-amber-200">Copy this secret now — it will not be shown again</p>
            <p v-if="lastSecret.label" class="text-xs text-slate-500 dark:text-slate-400 mt-1">Label: <span class="font-medium">{{ lastSecret.label }}</span> · Expires {{ lastSecret.expires_at ? timeAgo(lastSecret.expires_at) : 'in 90 days' }}</p>
            <div class="mt-2 flex items-center gap-2">
              <code class="flex-1 min-w-0 break-all text-xs bg-white dark:bg-slate-900 border border-amber-200 dark:border-amber-400/20 rounded-lg px-2.5 py-2">{{ lastSecret.secret }}</code>
              <button @click="copySecret(lastSecret.secret)" class="shrink-0 min-h-9 rounded-full border border-amber-200 dark:border-amber-400/30 bg-white dark:bg-slate-900 px-3 py-1.5 text-xs font-medium hover:bg-amber-50 dark:hover:bg-amber-500/10">{{ copiedSecret ? 'Copied' : 'Copy' }}</button>
            </div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Key: <span class="font-mono">{{ lastSecret.key_id }}</span></p>
            <button @click="lastSecret = null" class="text-xs underline text-slate-500 dark:text-slate-400 mt-1">Dismiss</button>
          </div>
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ keys.length }} key{{ keys.length === 1 ? '' : 's' }}</p>
            <button @click="askIssue" :disabled="issuing || keysLoading" class="min-h-9 rounded-full bg-indigo-600 text-white px-4 py-1.5 text-xs font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2">
              <svg v-if="issuing" viewBox="0 0 20 20" class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
              {{ issuing ? 'Issuing…' : 'Issue key' }}
            </button>
          </div>
          <p v-if="keysError" class="text-sm text-red-600 dark:text-red-400" role="alert">{{ keysError }}</p>
          <p v-if="keysLoading" class="text-sm text-slate-400">Loading…</p>
          <ul v-else-if="keys.length" class="space-y-2">
            <li v-for="k in keys" :key="k.key_id" class="border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 flex flex-col gap-2">
              <div class="flex items-start justify-between gap-3">
                <span class="min-w-0 flex-1">
                  <span class="font-mono text-xs font-medium text-slate-800 dark:text-slate-100 break-all">{{ k.key_id }}</span>
                  <span v-if="k.label" class="block text-xs font-medium text-slate-600 dark:text-slate-300 truncate">{{ k.label }}</span>
                  <span class="block text-xs text-slate-400 mt-0.5">
                    Created {{ timeAgo(k.created_at) }}
                    · Expires {{ k.expires_at ? expiryLabel(k.expires_at) : '—' }}
                    <span v-if="isExpired(k)" class="text-red-600 dark:text-red-400 font-medium">· Expired</span>
                    <span v-else :class="k.revoked ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'">· {{ k.revoked ? 'Revoked' : 'Active' }}</span>
                  </span>
                </span>
                <span class="flex items-center gap-1 shrink-0">
                  <button @click="askRotate(k)" :disabled="rotatingId === k.key_id" :aria-label="`Rotate ${k.key_id}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5">
                    <svg v-if="rotatingId === k.key_id" viewBox="0 0 20 20" class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
                    Rotate
                  </button>
                </span>
              </div>
              <div class="flex items-center gap-1.5">
                <button v-if="!k.revoked && !isExpired(k)" @click="askRevoke(k)" :disabled="revokingId === k.key_id" :aria-label="`Revoke ${k.label || k.key_id}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-amber-100 dark:border-white/10 bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 hover:bg-amber-100 disabled:opacity-50">Revoke</button>
                <button @click="askDelete(k)" :disabled="deletingId === k.key_id" :aria-label="`Delete ${k.label || k.key_id}`" class="min-h-9 px-3 py-1.5 rounded-full text-xs font-medium border border-red-100 dark:border-white/10 bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 hover:bg-red-100 disabled:opacity-50 inline-flex items-center gap-1.5">
                  <svg v-if="deletingId === k.key_id" viewBox="0 0 20 20" class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
                  Delete
                </button>
                <span v-if="k.revoked" class="text-xs text-slate-400 ml-1">Revoked</span>
              </div>
            </li>
          </ul>
          <p v-else class="text-sm text-slate-400">No keys yet. Issue one to let a third party query this account's knowledge.</p>
        </div>
        <div class="px-5 py-3 border-t border-slate-100 dark:border-slate-700 flex justify-end">
          <button @click="closeKeys" class="min-h-11 rounded-full bg-slate-900 dark:bg-slate-700 text-white px-5 py-2 text-sm font-medium hover:bg-slate-800">Close</button>
        </div>
      </div>
    </dialog>

    <!-- Issue confirmation with label + expiry -->
    <dialog ref="issueDialog" aria-labelledby="issue-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onIssueClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5" @submit.prevent="confirmIssue">
        <h3 id="issue-title" class="font-semibold text-slate-800 dark:text-slate-100">Issue API key</h3>
        <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Create a new key for “{{ keysAccount?.name }}”? The plaintext secret will be shown only once.</p>
        <label class="block mt-4 text-sm font-medium text-slate-700 dark:text-slate-200">Label <span class="text-slate-400 font-normal">(optional)</span>
          <input v-model="newLabel" placeholder="e.g. prod-integration" maxlength="64" class="mt-1 w-full min-h-11 border border-slate-200 dark:border-slate-700 rounded-full px-4 py-2 bg-white dark:bg-slate-900 text-sm" />
        </label>
        <label class="block mt-3 text-sm font-medium text-slate-700 dark:text-slate-200">Expires in (days)
          <input v-model.number="newExpiryDays" type="number" min="1" max="365" class="mt-1 w-full min-h-11 border border-slate-200 dark:border-slate-700 rounded-full px-4 py-2 bg-white dark:bg-slate-900 text-sm" />
        </label>
        <p class="text-xs text-slate-400 mt-1">Default 90 days. Minimum 1, maximum 365.</p>
        <p v-if="issueError" class="text-sm text-red-600 dark:text-red-400 mt-2" role="alert">{{ issueError }}</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelIssue" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">Cancel</button>
          <button type="submit" :disabled="issuing" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2">
            <svg v-if="issuing" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Create key
          </button>
        </div>
      </form>
    </dialog>

    <dialog ref="rotateDialog" aria-labelledby="rotate-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onRotateClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5">
        <h3 id="rotate-title" class="font-semibold text-slate-800 dark:text-slate-100">Rotate key</h3>
        <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Rotate <span class="font-mono text-xs">{{ pendingRotateKey?.key_id }}</span><span v-if="pendingRotateKey?.label"> (“{{ pendingRotateKey.label }}”)</span>? The old secret will stop working immediately and a new secret will be shown once.</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelRotate" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">Cancel</button>
          <button type="button" @click="confirmRotate" :disabled="!!rotatingId" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2">
            <svg v-if="rotatingId" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Rotate
          </button>
        </div>
      </form>
    </dialog>

    <dialog ref="revokeDialog" aria-labelledby="revoke-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onRevokeClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5">
        <h3 id="revoke-title" class="font-semibold text-slate-800 dark:text-slate-100">Revoke key</h3>
        <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Revoke <span class="font-mono text-xs">{{ pendingRevokeKey?.key_id }}</span><span v-if="pendingRevokeKey?.label"> (“{{ pendingRevokeKey.label }}”)</span>? The third party will immediately lose access. You can rotate to restore with a new secret, or delete the key.</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelRevoke" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">Cancel</button>
          <button type="button" @click="confirmRevoke" :disabled="!!revokingId" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 inline-flex items-center gap-2">
            <svg v-if="revokingId" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Revoke
          </button>
        </div>
      </form>
    </dialog>

    <dialog ref="deleteDialog" aria-labelledby="delete-title" class="p-0 bg-transparent max-w-none backdrop:bg-slate-900/50 open:grid open:place-items-center open:p-4" @close="onDeleteClosed">
      <form method="dialog" class="bg-white dark:bg-slate-900 rounded-2xl shadow-pop w-full max-w-md p-5">
        <h3 id="delete-title" class="font-semibold text-slate-800 dark:text-slate-100">Delete key</h3>
        <p class="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">Delete <span class="font-mono text-xs">{{ pendingDeleteKey?.key_id }}</span><span v-if="pendingDeleteKey?.label"> (“{{ pendingDeleteKey.label }}”)</span>? This cannot be undone. The third party will lose access and the key will be removed permanently.</p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" @click="cancelDelete" class="min-h-11 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">Cancel</button>
          <button type="button" @click="confirmDelete" :disabled="!!deletingId" class="min-h-11 rounded-full px-5 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 inline-flex items-center gap-2">
            <svg v-if="deletingId" viewBox="0 0 20 20" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3a7 7 0 1 0 7 7" stroke-linecap="round"/></svg>
            Delete permanently
          </button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { api, errorDetail, currentRole } from '../api.js'
import BaseInput from '../components/BaseInput.vue'

const accounts = ref([])
const name = ref('')
const error = ref('')
const msg = ref('')
const search = ref('')
const statusFilter = ref('active')
const loading = ref(false)
const creating = ref(false)
const touched = ref(false)
const copiedId = ref('')
const searchInput = ref(null)
const createDialog = ref(null)
const createNameInput = ref(null)
const createError = ref('')
const isAdmin = computed(() => currentRole() === 'admin')
const archiveDialog = ref(null)
const archiveTarget = ref(null)
const archiving = ref(false)
const keysDialog = ref(null)
const keysAccount = ref(null)
const keys = ref([])
const keysLoading = ref(false)
const keysError = ref('')
const issuing = ref(false)
const rotatingId = ref('')
const revokingId = ref('')
const deletingId = ref('')
const lastSecret = ref(null)
const copiedSecret = ref(false)
const issueDialog = ref(null)
const rotateDialog = ref(null)
const revokeDialog = ref(null)
const deleteDialog = ref(null)
const newLabel = ref('')
const newExpiryDays = ref(90)
const issueError = ref('')
const pendingRotateKey = ref(null)
const pendingRevokeKey = ref(null)
const pendingDeleteKey = ref(null)

const trimmedName = computed(() => name.value.trim())

const nameError = computed(() => {
  if (!touched.value && !error.value && !createError.value) return ''
  const v = trimmedName.value
  if (!v && touched.value) return 'Account name is required.'
  if (v && v.length < 2) return 'Use at least 2 characters.'
  if (v && v.length > 64) return 'Keep it under 64 characters.'
  return ''
})

const activeCount = computed(() => accounts.value.filter((a) => !a.is_archived).length)
const archivedCount = computed(() => accounts.value.filter((a) => a.is_archived).length)

const statusFiltered = computed(() =>
  accounts.value.filter((a) => (a.is_archived === true) === (statusFilter.value === 'archived')))

const filteredAccounts = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return statusFiltered.value
  return statusFiltered.value.filter((a) => String(a.name).toLowerCase().includes(q) || String(a.id).toLowerCase().includes(q))
})

function timeAgo(ts) {
  if (!ts) return 'recently'
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return 'recently'
  const sec = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (sec < 60) return 'moments ago'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} minute${min === 1 ? '' : 's'} ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} hour${hr === 1 ? '' : 's'} ago`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} day${day === 1 ? '' : 's'} ago`
  return new Date(ts).toLocaleDateString()
}
function isExpired(k) {
  if (!k?.expires_at) return false
  const t = new Date(k.expires_at).getTime()
  return !Number.isNaN(t) && t <= Date.now()
}
function expiryLabel(ts) {
  if (!ts) return '—'
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return '—'
  const diff = then - Date.now()
  if (diff <= 0) return `expired ${timeAgo(ts)}`
  const days = Math.ceil(diff / 86400000)
  return `in ${days} day${days === 1 ? '' : 's'} (${new Date(ts).toLocaleDateString()})`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.listAccounts()
    accounts.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = errorDetail(e, 'Failed to load accounts.')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createError.value = ''
  touched.value = false
  // keep name as-is to allow retry, but clear previous global error
  error.value = ''
  createDialog.value?.showModal()
  nextTick(() => {
    const el = createNameInput.value?.$el ?? document.getElementById('account-name')
    el?.focus?.()
  })
}
function cancelCreate() { createDialog.value?.close() }
function onCreateClosed() {
  createError.value = ''
  // reset touched so next open starts clean if no name typed
  if (!trimmedName.value) touched.value = false
}

async function create() {
  touched.value = true
  const v = trimmedName.value
  if (!v) {
    createError.value = 'Enter an account name.'
    return
  }
  if (v.length < 2 || v.length > 64) {
    createError.value = nameError.value || 'Check the account name.'
    return
  }
  creating.value = true
  createError.value = ''
  error.value = ''
  msg.value = ''
  try {
    await api.createAccount(v)
    name.value = ''
    touched.value = false
    createDialog.value?.close()
    msg.value = `Created “${v}”.`
    await load()
  } catch (e) {
    createError.value = errorDetail(e, 'Create failed.')
  } finally {
    creating.value = false
  }
}

async function copyId(id) {
  try {
    await navigator.clipboard.writeText(String(id))
    copiedId.value = String(id)
    setTimeout(() => { if (copiedId.value === String(id)) copiedId.value = '' }, 1500)
  } catch {
    error.value = 'Copy failed — select and copy manually.'
  }
}

function askArchive(a) {
  archiveTarget.value = a
  archiving.value = false
  archiveDialog.value?.showModal()
}

function cancelArchive() {
  archiveDialog.value?.close()
}

function onArchiveClosed() {
  archiveTarget.value = null
}

async function confirmArchive() {
  const target = archiveTarget.value
  if (!target) return
  archiving.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.archiveAccount(target.id)
    archiveDialog.value?.close()
    msg.value = `Archived “${target.name}”. Its documents are no longer available.`
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Archive failed.')
    archiveDialog.value?.close()
  } finally {
    archiving.value = false
  }
}

async function unarchive(a) {
  archiving.value = true
  error.value = ''
  msg.value = ''
  try {
    await api.unarchiveAccount(a.id)
    msg.value = `Unarchived “${a.name}”. Documents are available again.`
    await load()
  } catch (e) {
    error.value = errorDetail(e, 'Unarchive failed.')
  } finally {
    archiving.value = false
  }
}

function openKeys(a) {
  keysAccount.value = a
  keys.value = []
  keysError.value = ''
  lastSecret.value = null
  keysDialog.value?.showModal()
  loadKeys()
}
function closeKeys() { keysDialog.value?.close() }
function onKeysClosed() {
  keysAccount.value = null
  keysError.value = ''
  lastSecret.value = null
}
async function loadKeys() {
  if (!keysAccount.value) return
  keysLoading.value = true
  keysError.value = ''
  try {
    const { data } = await api.listCredentials(keysAccount.value.id)
    keys.value = Array.isArray(data) ? data : []
  } catch (e) {
    keysError.value = errorDetail(e, 'Failed to load keys.')
  } finally { keysLoading.value = false }
}
// Issue — confirmation dialog with label + expiry
function askIssue() {
  newLabel.value = ''
  newExpiryDays.value = 90
  issueError.value = ''
  issueDialog.value?.showModal()
}
function cancelIssue() { issueDialog.value?.close() }
function onIssueClosed() { issueError.value = '' }
async function confirmIssue() {
  if (!keysAccount.value) return
  const label = newLabel.value.trim() || null
  const days = Number(newExpiryDays.value)
  if (!Number.isInteger(days) || days < 1 || days > 365) {
    issueError.value = 'Expiry must be 1–365 days.'
    return
  }
  if (label !== null && label.length > 64) {
    issueError.value = 'Label must be ≤ 64 characters.'
    return
  }
  issuing.value = true
  keysError.value = ''
  issueError.value = ''
  try {
    const { data } = await api.issueCredential(keysAccount.value.id, { label, expires_in_days: days })
    lastSecret.value = data
    issueDialog.value?.close()
    await loadKeys()
  } catch (e) {
    issueError.value = errorDetail(e, 'Issue failed.')
  } finally { issuing.value = false }
}
// Rotate — confirmation modal
function askRotate(k) {
  pendingRotateKey.value = k
  rotateDialog.value?.showModal()
}
function cancelRotate() { rotateDialog.value?.close() }
function onRotateClosed() { pendingRotateKey.value = null }
async function confirmRotate() {
  const k = pendingRotateKey.value
  if (!k) return
  rotatingId.value = k.key_id
  keysError.value = ''
  try {
    const { data } = await api.rotateCredential(k.key_id)
    lastSecret.value = data
    rotateDialog.value?.close()
    await loadKeys()
  } catch (e) { keysError.value = errorDetail(e, 'Rotate failed.') }
  finally { rotatingId.value = '' }
}
// Revoke — confirmation modal (soft)
function askRevoke(k) {
  pendingRevokeKey.value = k
  revokeDialog.value?.showModal()
}
function cancelRevoke() { revokeDialog.value?.close() }
function onRevokeClosed() { pendingRevokeKey.value = null }
async function confirmRevoke() {
  const k = pendingRevokeKey.value
  if (!k) return
  revokingId.value = k.key_id
  keysError.value = ''
  try {
    await api.revokeCredential(k.key_id)
    revokeDialog.value?.close()
    await loadKeys()
  } catch (e) { keysError.value = errorDetail(e, 'Revoke failed.') }
  finally { revokingId.value = '' }
}
// Delete — confirmation modal (hard)
function askDelete(k) {
  pendingDeleteKey.value = k
  deleteDialog.value?.showModal()
}
function cancelDelete() { deleteDialog.value?.close() }
function onDeleteClosed() { pendingDeleteKey.value = null }
async function confirmDelete() {
  const k = pendingDeleteKey.value
  if (!k) return
  deletingId.value = k.key_id
  keysError.value = ''
  try {
    await api.deleteCredential(k.key_id)
    deleteDialog.value?.close()
    await loadKeys()
  } catch (e) { keysError.value = errorDetail(e, 'Delete failed.') }
  finally { deletingId.value = '' }
}
async function copySecret(s) {
  try { await navigator.clipboard.writeText(String(s)); copiedSecret.value = true; setTimeout(() => copiedSecret.value = false, 1300) } catch {}
}

onMounted(async () => {
  await load()
  await nextTick()
  // Autofocus search for keyboard users; respects SPA navigation (autofocus attr alone only fires on full page load)
  const el = searchInput.value?.$el ?? document.getElementById('account-search')
  el?.focus?.()
})
</script>

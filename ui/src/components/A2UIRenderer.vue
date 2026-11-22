<template>
  <div v-if="surface && surface.components" class="mt-2 space-y-2">
    <div v-for="c in surface.components" :key="c.id">
      <div v-if="c.type === 'Card'" class="rounded-xl border bg-white shadow-sm p-3" :class="c.props?.variant === 'warning' ? 'border-amber-200 bg-amber-50/60' : 'border-slate-200'">
        <p v-if="c.props?.title" class="text-sm font-semibold text-slate-800">{{ c.props.title }}</p>
        <p v-if="c.props?.subtitle" class="text-xs text-slate-500 mt-0.5">{{ c.props.subtitle }}</p>
        <div v-if="c.children?.length" class="mt-2 space-y-2">
          <template v-for="ch in c.children" :key="ch.id">
            <p v-if="ch.type === 'Text'" class="text-sm" :class="ch.props?.variant === 'muted' ? 'text-slate-500' : 'text-slate-700'">{{ ch.props?.text }}</p>
            <span v-else-if="ch.type === 'Badge'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">{{ ch.props?.label }}</span>
            <button v-else-if="ch.type === 'Button'" @click="$emit('action', ch.props?.action || { type: 'button', label: ch.props?.label })" class="inline-flex items-center justify-center min-h-9 px-3 py-1.5 rounded-full text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600" :class="ch.props?.variant === 'primary' ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'">{{ ch.props?.label }}</button>
          </template>
        </div>
        <p v-else-if="c.props?.text" class="text-sm text-slate-600 mt-1">{{ c.props.text }}</p>
      </div>
      <p v-else-if="c.type === 'Text'" class="text-sm leading-relaxed" :class="c.props?.variant === 'muted' ? 'text-slate-500' : 'text-slate-700'">{{ c.props?.text }}</p>
      <span v-else-if="c.type === 'Badge'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">{{ c.props?.label }}</span>
      <button v-else-if="c.type === 'Button'" @click="$emit('action', c.props?.action || { type: 'button', label: c.props?.label })" class="inline-flex items-center justify-center min-h-9 px-3 py-1.5 rounded-full text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600" :class="c.props?.variant === 'primary' ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'">{{ c.props?.label }}</button>
      <details v-else-if="c.type === 'Sources'" class="rounded-xl border border-slate-200 bg-slate-50 group">
        <summary class="flex items-center justify-between gap-2 px-3 py-2.5 cursor-pointer list-none [&::-webkit-details-marker]:hidden select-none">
          <span class="text-xs font-semibold text-slate-600">Sources ({{ c.props?.items?.length ?? 0 }})</span>
          <svg viewBox="0 0 20 20" class="w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 7l5 5 5-5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </summary>
        <div class="px-3 pb-3">
          <ul class="space-y-2">
            <li v-for="(it, idx) in (c.props?.items || [])" :key="idx" class="rounded-lg bg-white border border-slate-200 p-2.5">
              <p class="text-xs text-slate-700 leading-relaxed line-clamp-3">{{ it.snippet }}</p>
              <div class="flex items-center gap-1.5 mt-1.5">
                <span class="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">{{ it.category }}</span>
                <span v-if="it.document_id" class="text-[11px] text-slate-400 font-mono">#{{ it.document_id }}</span>
              </div>
            </li>
          </ul>
        </div>
      </details>
      <div v-else-if="c.type === 'List'" class="rounded-xl border border-slate-200 bg-white p-3">
        <p v-if="c.props?.title" class="text-xs font-semibold text-slate-600 mb-1.5">{{ c.props.title }}</p>
        <ul class="space-y-1">
          <li v-for="(it, idx) in (c.props?.items || [])" :key="idx" class="text-sm text-slate-700 flex gap-2"><span class="text-slate-400">•</span><span class="flex-1 min-w-0 break-words">{{ typeof it === 'string' ? it : it.label || it.text || JSON.stringify(it) }}</span></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ surface: { type: Object, required: true } })
defineEmits(['action'])
</script>

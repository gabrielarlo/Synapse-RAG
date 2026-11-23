<template>
  <span
    :class="[
      'grid place-items-center shrink-0 rounded-lg shadow-pop select-none',
      sizeClass,
      variantClass
    ]"
    aria-hidden="true"
  >
    <svg
      :width="iconSize"
      :height="iconSize"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="block"
    >
      <defs>
        <linearGradient :id="`logo-g1-${uid}`" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#22d3ee" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </linearGradient>
        <linearGradient :id="`logo-g2-${uid}`" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#22d3ee" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </linearGradient>
        <radialGradient :id="`logo-gc-${uid}`" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#22d3ee" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </radialGradient>
      </defs>
      <path d="M 9.5 10.2 C 9.5 12.8 11.8 14.3 13.7 15" :stroke="`url(#logo-g1-${uid})`" stroke-width="1.6" stroke-linecap="round" />
      <path d="M 22.5 9.2 C 20.0 10.0 18.6 12.2 18.1 13.9" :stroke="`url(#logo-g1-${uid})`" stroke-width="1.6" stroke-linecap="round" />
      <path d="M 9.5 22.1 C 12.0 21.4 13.7 19.2 14.2 18.1" :stroke="`url(#logo-g2-${uid})`" stroke-width="1.6" stroke-linecap="round" />
      <path d="M 22.8 22.8 C 22.8 20.2 20.5 18.6 18.6 17.9" :stroke="`url(#logo-g2-${uid})`" stroke-width="1.6" stroke-linecap="round" />
      <circle cx="8.5" cy="8.5" r="2.1" fill="#22d3ee" />
      <circle cx="24.6" cy="8.4" r="2.1" fill="#8b5cf6" />
      <circle cx="8.3" cy="23.4" r="2.1" fill="#8b5cf6" />
      <circle cx="23.8" cy="24.4" r="2.1" fill="#22d3ee" />
      <circle cx="16" cy="16" r="4.2" :fill="`url(#logo-gc-${uid})`" stroke="#7dd3fc" stroke-width="0.7" />
    </svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  size: { type: String, default: 'md' },
  variant: { type: String, default: 'dark' }
})
const uid = Math.random().toString(36).slice(2, 8)
const sizeMap = { sm: 'w-8 h-8', md: 'w-8 h-8', lg: 'w-9 h-9' }
const iconMap = { sm: 22, md: 22, lg: 24 }
const sizeClass = computed(() => sizeMap[props.size] || sizeMap.md)
const iconSize = computed(() => iconMap[props.size] || 22)
const variantClass = computed(() => {
  if (props.variant === 'gradient') return 'bg-gradient-to-br from-indigo-500 to-violet-500'
  if (props.variant === 'translucent') return 'bg-white/20 backdrop-blur'
  return 'bg-[#0a0f1e] border border-white/10'
})
</script>

<template>
  <input
    v-model="model"
    class="border border-slate-200 rounded-full px-4 py-2.5 focus:border-indigo-500 disabled:bg-slate-50 disabled:text-slate-400"
  />
</template>

<script setup>
const [model, modifiers] = defineModel({
  set(value) {
    if (modifiers.number && value !== '' && value !== null) {
      return Number(value)
    }
    return value
  },
})
</script>

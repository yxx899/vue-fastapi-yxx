<template>
  <section class="page-banner">
    <div class="page-banner__main">
      <div v-if="icon" class="page-banner__icon">
        <el-icon :size="22"><component :is="icon" /></el-icon>
      </div>
      <div>
        <p v-if="eyebrow" class="page-banner__eyebrow">{{ eyebrow }}</p>
        <h2 class="page-banner__title">{{ title }}</h2>
        <p v-if="subtitle" class="page-banner__sub">{{ subtitle }}</p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-banner__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  eyebrow: { type: String, default: '' },
  icon: { type: [Object, Function, String], default: null },
})
</script>

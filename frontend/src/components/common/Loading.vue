<script setup>
defineProps({
  text: { type: String, default: '加载中...' },
})
</script>

<template>
  <div class="loading">
    <div class="spinner" />
    <span>{{ text }}</span>
  </div>
</template>

<style scoped>
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 14px;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>

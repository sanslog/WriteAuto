<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const title = computed(() => {
  const name = route.name
  if (name === 'Home') return '作品列表'
  if (name === 'NovelEditor') return '写作工作区'
  if (name === 'Outline') return '大纲管理'
  if (name === 'Characters') return '角色管理'
  if (name === 'Settings') return '设置'
  return 'WriteAuto'
})
</script>

<template>
  <header class="app-header">
    <h2>{{ title }}</h2>
  </header>
</template>

<style scoped>
.app-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  flex-shrink: 0;
}
.app-header h2 {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
}
</style>

<script setup>
const props = defineProps({
  chapters: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

function toggle(id) {
  const selected = [...props.modelValue]
  const idx = selected.indexOf(id)
  if (idx === -1) selected.push(id)
  else selected.splice(idx, 1)
  emit('update:modelValue', selected)
}
</script>

<template>
  <div class="chapter-selector">
    <h4>选择参考章节（上下文）</h4>
    <p class="hint">勾选你想作为上下文的已批准章节。未选择时默认使用最近5章。</p>
    <div v-if="chapters.length === 0" class="empty-state">
      暂无已批准章节
    </div>
    <label
      v-for="ch in chapters"
      :key="ch.id"
      class="chapter-item"
    >
      <div class="chapter-info">
        <span class="ch-title">{{ ch.title }}</span>
        <span class="ch-words">{{ ch.word_count || 0 }}字</span>
      </div>
      <input
        type="checkbox"
        :checked="modelValue.includes(ch.id)"
        @change="toggle(ch.id)"
        class="ch-checkbox"
      />
    </label>
  </div>
</template>

<style scoped>
.chapter-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-selector h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
  border: 1px dashed var(--border);
  border-radius: 6px;
}

.chapter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
  min-height: 40px;
}

.chapter-item:hover {
  background: var(--bg-secondary);
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0; /* 允许 flex 子项收缩 */
}

.ch-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ch-words {
  color: var(--text-secondary);
  font-size: 12px;
  flex-shrink: 0; /* 防止字数被压缩 */
}

.ch-checkbox {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* 可选：选中状态样式增强 */
.chapter-item:has(input:checked) {
  border-color: var(--primary-color, #4a90d9);
  background: var(--primary-bg-light, rgba(74, 144, 217, 0.05));
}
</style>
<script setup>
const props = defineProps({
  foreshadows: { type: Array, default: () => [] },
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
  <div class="foreshadow-selector">
    <h4>选择伏笔</h4>
    <p class="hint">勾选你想在当前章节中使用的伏笔。未选择时默认使用全部未使用伏笔。</p>
    <div v-if="foreshadows.length === 0" class="empty-state">
      暂无未使用的伏笔
    </div>
    <label
      v-for="f in foreshadows"
      :key="f.id"
      class="foreshadow-item"
    >
      <div class="f-info">
        <span class="f-title">{{ f.title }}</span>
        <span class="f-desc">{{ f.description || '无描述' }}</span>
      </div>
      <input
        type="checkbox"
        :checked="modelValue.includes(f.id)"
        @change="toggle(f.id)"
        class="f-checkbox"
      />
    </label>
  </div>
</template>

<style scoped>
.foreshadow-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.foreshadow-selector h4 {
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

.foreshadow-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
  min-height: 44px;
}

.foreshadow-item:hover {
  background: var(--bg-secondary);
}

.f-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0; /* 允许 flex 子项收缩 */
}

.f-title {
  font-weight: 500;
  flex-shrink: 0; /* 标题不压缩，优先显示 */
}

.f-desc {
  font-size: 12px;
  color: var(--text-secondary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.f-checkbox {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* 选中状态样式增强 */
.foreshadow-item:has(input:checked) {
  border-color: var(--primary-color, #4a90d9);
  background: var(--primary-bg-light, rgba(74, 144, 217, 0.05));
}
</style>
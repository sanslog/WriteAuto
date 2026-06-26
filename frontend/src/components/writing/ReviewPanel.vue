<script setup>
import { ref } from 'vue'
import { ThumbsUp, Edit3, X } from 'lucide-vue-next'

defineProps({
  state: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['judge'])

const modifyText = ref('')
const showModifyInput = ref(false)
</script>

<template>
  <div class="review-panel">
    <div class="review-content">
      <div class="chapter-titles">
        <span
          v-for="(title, i) in state.chapter_titles || []"
          :key="i"
          class="badge badge-primary"
        >
          {{ title }}
        </span>
      </div>
      <div class="preview-text">
        {{ (state.generated_text || '').slice(0, 3000) }}{{ (state.generated_text || '').length > 3000 ? '...' : '' }}
      </div>
      <p v-if="state.modification_count" class="mod-count">
        已修改 {{ state.modification_count }} 次
      </p>
    </div>

    <div v-if="showModifyInput" class="modify-section">
      <label class="form-label-text">修改意见</label>
      <textarea
        v-model="modifyText"
        placeholder="请输入修改意见..."
        rows="3"
      />
    </div>

    <div class="review-actions">
      <button class="btn-ghost" @click="showModifyInput = true" :disabled="loading || showModifyInput">
        <Edit3 :size="14" /> 修改
      </button>
      <template v-if="showModifyInput">
        <button class="btn-ghost" @click="showModifyInput = false; modifyText = ''">
          <X :size="14" /> 取消修改
        </button>
        <button
          class="btn-primary"
          @click="emit('judge', { action: 'modify', text: modifyText })"
          :disabled="!modifyText.trim() || loading"
        >
          提交修改
        </button>
      </template>
      <div class="spacer" />
      <button class="btn-danger btn-sm" @click="emit('judge', { action: 'cancel' })" :disabled="loading">
        取消
      </button>
      <button class="btn-success" @click="emit('judge', { action: 'approve' })" :disabled="loading">
        <ThumbsUp :size="14" /> 通过
      </button>
    </div>
  </div>
</template>

<style scoped>
.review-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.chapter-titles {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
  margin-bottom: var(--space-sm);
}

.preview-text {
  background: var(--bg-secondary);
  padding: var(--space-md);
  border-radius: var(--radius);
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'SimSun', serif;
  font-size: 14px;
  line-height: 1.8;
  max-height: 350px;
  overflow-y: auto;
  white-space: pre-wrap;
  border: 1px solid var(--border);
}

.mod-count {
  font-size: 12px;
  color: var(--text-muted);
}

.modify-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.form-label-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.review-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.spacer {
  flex: 1;
}
</style>

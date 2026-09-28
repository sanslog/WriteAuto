<script setup>
import { AlertTriangle, HelpCircle } from 'lucide-vue-next'
import Modal from './Modal.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '' },
  description: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  danger: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  width: { type: String, default: '420px' },
})
const emit = defineEmits(['confirm', 'close'])

function handleConfirm() {
  if (props.loading) return
  emit('confirm')
}
</script>

<template>
  <Modal
    :show="show"
    :title="title"
    :width="width"
    :close-on-overlay="!loading"
    :close-on-esc="!loading"
    @close="emit('close')"
  >
    <div class="confirm-body">
      <div class="confirm-icon" :class="danger ? 'is-danger' : 'is-primary'">
        <component :is="danger ? AlertTriangle : HelpCircle" :size="20" />
      </div>
      <div class="confirm-text">
        <p v-if="message" class="confirm-message">{{ message }}</p>
        <p v-if="description" class="confirm-description">{{ description }}</p>
      </div>
    </div>

    <slot />

    <div class="modal-footer-btns">
      <button type="button" class="btn-ghost" :disabled="loading" @click="emit('close')">
        {{ cancelText }}
      </button>
      <button
        type="button"
        :class="danger ? 'btn-danger' : 'btn-primary'"
        :disabled="loading"
        @click="handleConfirm"
      >
        {{ loading ? '处理中...' : confirmText }}
      </button>
    </div>
  </Modal>
</template>

<style scoped>
.confirm-body {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
}

.confirm-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
}

.confirm-icon.is-danger {
  background: var(--danger-light);
  color: var(--danger);
}

.confirm-icon.is-primary {
  background: var(--primary-light);
  color: var(--primary);
}

.confirm-text {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.confirm-message {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.6;
  word-break: break-word;
}

.confirm-description {
  margin-top: var(--space-xs);
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
}

.modal-footer-btns {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
}
</style>

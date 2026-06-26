<script setup>
import { onMounted, onUnmounted } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: String, default: '480px' },
  closeOnOverlay: { type: Boolean, default: true },
  closeOnEsc: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])

function handleKeydown(e) {
  if (props.closeOnEsc && e.key === 'Escape' && props.show) {
    emit('close')
  }
}

onMounted(() => {
  if (props.closeOnEsc) {
    document.addEventListener('keydown', handleKeydown)
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <transition name="scale" appear>
      <div v-if="show" class="modal-overlay" @click.self="closeOnOverlay && emit('close')">
        <div class="modal-panel" :style="{ maxWidth: width }">
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="modal-close" @click="emit('close')" :aria-label="'关闭'">
              <X :size="18" />
            </button>
          </div>
          <div class="modal-body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: var(--space-lg);
}

.modal-panel {
  background: var(--bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 95%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.modal-close {
  padding: 4px;
  background: transparent;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius);
}
.modal-close:hover {
  background: var(--bg-secondary);
  color: var(--text);
}

.modal-body {
  padding: var(--space-lg);
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
</style>

<script setup>
import { ref } from 'vue'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-vue-next'

const messages = ref([])
let id = 0

const iconMap = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
}

function show(text, type = 'info', duration = 3000) {
  const msg = { id: ++id, text, type, progress: 100 }
  messages.value.push(msg)

  // Progress bar animation
  const interval = 50
  const step = 100 / (duration / interval)
  const timer = setInterval(() => {
    msg.progress -= step
    if (msg.progress <= 0) {
      msg.progress = 0
      clearInterval(timer)
    }
  }, interval)

  setTimeout(() => {
    messages.value = messages.value.filter(m => m.id !== msg.id)
    clearInterval(timer)
  }, duration)
}

function dismiss(msgId) {
  messages.value = messages.value.filter(m => m.id !== msgId)
}

defineExpose({ show })
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['toast', `toast-${msg.type}`]"
        :style="{ '--toast-progress': msg.progress + '%' }"
      >
        <component :is="iconMap[msg.type]" :size="16" class="toast-icon" />
        <span class="toast-text">{{ msg.text }}</span>
        <button class="toast-dismiss" @click="dismiss(msg.id)">
          <X :size="14" />
        </button>
        <div class="toast-progress-bar" />
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--space-lg);
  right: var(--space-lg);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  max-width: 380px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 12px var(--space-md);
  border-radius: var(--radius);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  position: relative;
  overflow: hidden;
  min-width: 240px;
}

.toast-icon {
  flex-shrink: 0;
}

.toast-text {
  flex: 1;
  line-height: 1.4;
}

.toast-dismiss {
  padding: 2px;
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.8);
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}
.toast-dismiss:hover {
  background: rgba(255, 255, 255, 0.3);
  color: #fff;
}

.toast-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  width: var(--toast-progress, 0%);
  background: rgba(255, 255, 255, 0.4);
  transition: width linear;
  transition-duration: 50ms;
}

.toast-info { background: var(--primary); }
.toast-success { background: var(--success); }
.toast-error { background: var(--danger); }

/* TransitionGroup animations */
.toast-enter-active {
  transition: all var(--transition) var(--ease-spring);
}
.toast-leave-active {
  transition: all var(--transition) var(--ease);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
.toast-move {
  transition: transform var(--transition) var(--ease);
}
</style>

<script setup>
import { Target, Pencil, Trash2, GripVertical, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  node: { type: Object, required: true },
  index: { type: Number, required: true },
  isCursor: { type: Boolean, default: false },
  dragging: { type: Boolean, default: false },
  dragOver: { type: Boolean, default: false },
})
const emit = defineEmits(['edit', 'delete', 'setCursor', 'dragstart', 'dragover', 'dragend'])
</script>

<template>
  <div
    :class="[
      'plot-node',
      { 'is-cursor': isCursor },
      { dragging },
      { 'drag-over': dragOver },
    ]"
    @dragstart="emit('dragstart', index)"
    @dragover.prevent="emit('dragover', $event, index)"
    @dragend="emit('dragend')"
  >
    <div class="node-header">
      <span class="drag-handle"><GripVertical :size="12" /></span>
      <span :class="['node-index', { 'index-cursor': isCursor }]">{{ index + 1 }}</span>
      <span class="node-title truncate">{{ node.title || '未命名节点' }}</span>
      <span :class="['node-status', `status-${node.status}`]">
        {{ node.status === 'written' ? '已写' : node.status === 'planned' ? '规划中' : node.status }}
      </span>
      <div class="node-actions">
        <button
          v-if="!isCursor"
          class="btn-icon btn-xs set-cursor-btn"
          @click="emit('setCursor', index)"
          title="设为当前位置"
        >
          <Target :size="13" />
        </button>
        <span v-else class="cursor-indicator">
          <ChevronRight :size="13" />
          当前位置
        </span>
        <button class="btn-icon btn-xs" @click="emit('edit', node)" title="编辑">
          <Pencil :size="12" />
        </button>
        <button class="btn-icon btn-xs danger" @click="emit('delete', node.id)" title="删除">
          <Trash2 :size="12" />
        </button>
      </div>
    </div>
    <p v-if="node.summary" class="node-summary">{{ node.summary }}</p>
    <div v-if="isCursor && node.detailed_outline" class="node-detail">
      <strong>细纲：</strong>{{ node.detailed_outline }}
    </div>
  </div>
</template>

<style scoped>
.plot-node {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  cursor: pointer;
  transition: all var(--transition-fast) var(--ease);
  background: var(--bg);
}

.plot-node:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.plot-node.is-cursor {
  border-left: 3px solid var(--primary);
  background: var(--primary-light);
  border-radius: 0 var(--radius) var(--radius) 0;
}

.plot-node.dragging {
  opacity: 0.4;
}

.plot-node.drag-over {
  border-top: 2px solid var(--primary);
}

.node-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.drag-handle {
  cursor: grab;
  color: var(--text-muted);
  display: flex;
  opacity: 0;
  transition: opacity var(--transition-fast) var(--ease);
  flex-shrink: 0;
}

.plot-node:hover .drag-handle {
  opacity: 0.6;
}

.node-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.index-cursor {
  background: var(--primary);
  color: #fff;
}

.node-title {
  font-weight: 500;
  flex: 1;
  font-size: 14px;
}

.node-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 600;
  flex-shrink: 0;
}
.status-written { background: var(--success-light); color: var(--success); }
.status-planned { background: var(--warning-light); color: var(--warning); }

.node-actions {
  display: flex;
  gap: 2px;
  align-items: center;
  flex-shrink: 0;
}

.set-cursor-btn {
  color: var(--primary);
}
.set-cursor-btn:hover {
  background: var(--primary-light);
}

.cursor-indicator {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--primary);
  font-weight: 600;
}

.btn-xs { padding: 3px; }
.btn-xs.danger { color: var(--danger); }
.btn-xs.danger:hover { background: var(--danger-light); }

.node-summary {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: var(--space-sm);
  line-height: 1.5;
}

.node-detail {
  font-size: 13px;
  color: var(--text);
  margin-top: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--bg);
  border-radius: var(--radius-sm);
  line-height: 1.5;
}
.node-detail strong {
  color: var(--primary);
  margin-right: var(--space-xs);
}
</style>

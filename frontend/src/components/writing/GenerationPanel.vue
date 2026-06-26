<script setup>
import { ref } from 'vue'
import { ChevronLeft, ChevronRight, Play } from 'lucide-vue-next'
import ChapterSelector from './ChapterSelector.vue'
import ForeshadowSelector from './ForeshadowSelector.vue'

defineProps({
  preparation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['start'])

const step = ref(1)
const selectedChapters = ref([])
const selectedForeshadows = ref([])

function next() { step.value++ }
function prev() { step.value-- }
function start() {
  emit('start', {
    chapter_ids: selectedChapters.value,
    foreshadow_ids: selectedForeshadows.value,
  })
  step.value = 1
  selectedChapters.value = []
  selectedForeshadows.value = []
}
</script>

<template>
  <div class="generation-panel">
    <!-- Step indicator -->
    <div class="gen-steps">
      <div class="step-dots">
        <span :class="{ active: step >= 1, done: step > 1 }">1</span>
        <span class="line" />
        <span :class="{ active: step >= 2, done: step > 2 }">2</span>
        <span class="line" />
        <span :class="{ active: step >= 3 }">3</span>
      </div>
      <p class="step-label">
        {{ step === 1 ? '参考章节' : step === 2 ? '选中伏笔' : '确认生成' }}
      </p>
    </div>

    <!-- Step 1: Chapter selection -->
    <div v-if="step === 1 && preparation" class="gen-step-content">
      <ChapterSelector
        :chapters="preparation.approved_chapters || []"
        v-model="selectedChapters"
      />
    </div>

    <!-- Step 2: Foreshadow selection -->
    <div v-if="step === 2 && preparation" class="gen-step-content">
      <ForeshadowSelector
        :foreshadows="(preparation.foreshadows || []).filter(f => f.status === 'unused')"
        v-model="selectedForeshadows"
      />
    </div>

    <!-- Step 3: Confirm -->
    <div v-if="step === 3 && preparation" class="gen-step-content confirm-step">
      <h4>确认生成配置</h4>
      <div class="confirm-info">
        <div class="info-row">
          <span class="info-label">当前进度</span>
          <span>第 {{ preparation.cursor_position + 1 }} 节</span>
        </div>
        <div class="info-row">
          <span class="info-label">下一节点</span>
          <span>{{ preparation.next_node_title || '无' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">参考章节</span>
          <span>{{ selectedChapters.length ? selectedChapters.length + ' 章' : '默认（最近5章）' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">选中伏笔</span>
          <span>{{ selectedForeshadows.length ? selectedForeshadows.length + ' 个' : '全部未使用' }}</span>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="gen-actions">
      <button v-if="step > 1" class="btn-ghost" @click="prev">
        <ChevronLeft :size="14" /> 上一步
      </button>
      <button v-if="step < 3" class="btn-primary" @click="next" style="margin-left: auto;">
        下一步 <ChevronRight :size="14" />
      </button>
      <button v-if="step === 3" class="btn-primary" @click="start" :disabled="loading">
        <Play :size="14" />
        {{ loading ? '生成中...' : '开始生成' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.generation-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.gen-steps {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
}

.step-dots {
  display: flex;
  align-items: center;
  gap: 0;
}

.step-dots span:not(.line) {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  border: 2px solid var(--border);
  color: var(--text-secondary);
  transition: all var(--transition-fast) var(--ease);
}

.step-dots .active {
  border-color: var(--primary);
  color: var(--primary);
}

.step-dots .done {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.step-dots .line {
  width: 40px;
  height: 2px;
  background: var(--border);
}

.step-label {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.gen-step-content {
  min-height: 100px;
}

.confirm-step h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: var(--space-md);
  color: var(--text);
}

.confirm-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

.info-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.gen-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border);
  margin-top: auto;
}
</style>

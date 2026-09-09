<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  BookMarked,
  Clock,
  Layers,
  ListChecks,
  Loader,
  PenLine,
  RotateCcw,
  Square,
  Waypoints,
} from 'lucide-vue-next'
import { useNovelStore } from '../stores/novel'
import { useOneSentenceStore } from '../stores/oneSentence'

const novelStore = useNovelStore()
const store = useOneSentenceStore()

const userRequest = ref('')
const novelId = ref('')
const maxIterations = ref(24)

const statusLabels = {
  idle: '未开始',
  planning: '规划中',
  awaiting_outline: '等待大纲',
  awaiting_tool_call: '等待工具调用',
  calling_tools: '调用工具',
  observing: '观察结果',
  finalizing: '整理结果',
  completed: '已完成',
  partial: '部分完成',
  failed: '失败',
  cancelled: '已取消',
}

const nodeStatusLabels = {
  planned: '待写',
  writing: '写作中',
  written: '已写',
}

const statusLabel = computed(() => statusLabels[store.status] || '进行中')
const statusType = computed(() => {
  if (store.status === 'completed') return 'success'
  if (store.status === 'failed') return 'danger'
  if (store.status === 'cancelled') return 'warning'
  if (store.status === 'idle') return 'muted'
  return 'primary'
})

const progress = computed(() => store.progress || {})
const savedChapters = computed(() => {
  const chapters = progress.value.saved_chapters || store.result?.chapters || []
  return Array.isArray(chapters) ? chapters : []
})
const currentPlotNode = computed(() => progress.value.current_plot_node || null)
const latestChapter = computed(() => progress.value.latest_chapter || savedChapters.value.at(-1) || null)
const toolsUsed = computed(() => {
  const tools = progress.value.tools_used || store.result?.tools_used || []
  return [...new Set(tools.map(item => String(item)))]
})
const generatedText = computed(() => {
  if (store.result?.text) return store.result.text
  return savedChapters.value.map(chapter => chapter.content || '').join('\n\n')
})
const chapterWordCount = computed(() => {
  return savedChapters.value.reduce((total, chapter) => {
    return total + String(chapter.content || '').replace(/\s/g, '').length
  }, 0)
})

async function startRun() {
  if (!userRequest.value.trim()) return
  await store.run({
    user_request: userRequest.value.trim(),
    novel_id: novelId.value,
    max_iterations: maxIterations.value,
  })
}

async function cancelRun() {
  await store.cancel()
}

onMounted(() => {
  novelStore.fetchNovels()
})

onUnmounted(() => {
  store.abortController?.abort()
})
</script>

<template>
  <div class="one-sentence-view">
    <header class="page-header">
      <div class="title-group">
        <PenLine :size="22" class="title-icon" />
        <h1>一句话小说</h1>
      </div>
      <span class="status-pill" :class="`status-${statusType}`">
        <Loader v-if="store.loading" :size="13" class="spin" />
        <span>{{ statusLabel }}</span>
      </span>
    </header>

    <main class="workbench">
      <section class="composer">
        <form @submit.prevent="startRun">
          <label for="one-sentence-request">一句话设定</label>
          <textarea
            id="one-sentence-request"
            v-model="userRequest"
            rows="6"
            maxlength="2000"
            placeholder="例如：一个年轻修士在废弃书库里听到了一页残稿开口说话。"
          ></textarea>
          <div class="composer-meta">
            <span>{{ userRequest.length }} / 2000</span>
            <span>循环上限 {{ maxIterations }}</span>
          </div>

          <label for="one-sentence-novel">续写作品</label>
          <select id="one-sentence-novel" v-model="novelId">
            <option value="">自动创建新作品</option>
            <option v-for="novel in novelStore.novels" :key="novel.id" :value="novel.id">
              {{ novel.title || '未命名作品' }}
            </option>
          </select>

          <label for="one-sentence-iterations">最大循环轮次</label>
          <input
            id="one-sentence-iterations"
            v-model.number="maxIterations"
            type="number"
            min="1"
            max="128"
          >

          <div class="action-row">
            <button class="btn-primary" type="submit" :disabled="store.loading || !userRequest.trim()">
              <PenLine :size="14" /> 开始生成
            </button>
            <button
              class="btn-ghost"
              type="button"
              :disabled="!store.generationId || !store.loading"
              @click="cancelRun"
            >
              <Square :size="14" /> 停止
            </button>
          </div>
        </form>
      </section>

      <section class="runtime">
        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label"><Waypoints :size="14" /> 剧情节点</div>
            <div class="metric-value">{{ progress.outline_nodes_count || 0 }}</div>
          </div>
          <div class="metric">
            <div class="metric-label"><Layers :size="14" /> 章节数</div>
            <div class="metric-value">{{ progress.chapter_count || savedChapters.length || 0 }}</div>
          </div>
          <div class="metric">
            <div class="metric-label"><RotateCcw :size="14" /> 循环轮次</div>
            <div class="metric-value">
              {{ progress.iteration || store.result?.iterations || 0 }} / {{ maxIterations }}
            </div>
          </div>
          <div class="metric">
            <div class="metric-label"><BookMarked :size="14" /> 总字数</div>
            <div class="metric-value">{{ chapterWordCount }}</div>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-panel">
            <div class="panel-title">
              <BookMarked :size="14" /> 当前剧情节点
            </div>
            <template v-if="currentPlotNode">
              <div class="detail-primary">{{ currentPlotNode.title || '未命名节点' }}</div>
              <div class="detail-secondary">
                {{ nodeStatusLabels[currentPlotNode.status] || currentPlotNode.status || '待写' }}
                · 第 {{ (progress.cursor_position || 0) + 1 }} 个节点
              </div>
              <p v-if="currentPlotNode.summary" class="detail-text">{{ currentPlotNode.summary }}</p>
              <p v-if="currentPlotNode.detailed_outline" class="detail-text muted">
                {{ currentPlotNode.detailed_outline }}
              </p>
            </template>
            <p v-else class="empty-text">等待 agent 创建剧情节点</p>
          </div>

          <div class="detail-panel">
            <div class="panel-title">
              <Layers :size="14" /> 最新章节
            </div>
            <template v-if="latestChapter">
              <div class="detail-primary">{{ latestChapter.title || '未命名章节' }}</div>
              <div class="detail-secondary">{{ latestChapter.status || 'draft' }}</div>
              <p class="detail-text">{{ latestChapter.content || '' }}</p>
            </template>
            <p v-else class="empty-text">暂无已保存章节</p>
          </div>
        </div>

        <div class="detail-panel wide">
          <div class="panel-title">
            <ListChecks :size="14" /> 实时进度
          </div>
          <div v-if="store.error" class="error-line">{{ store.error }}</div>

          <div v-if="toolsUsed.length" class="tool-list">
            <span v-for="tool in toolsUsed" :key="tool" class="tool-chip">{{ tool }}</span>
          </div>

          <ol class="timeline">
            <li v-for="item in store.timeline.slice(0, 18)" :key="item.id">
              <div class="timeline-dot"></div>
              <div class="timeline-body">
                <div class="timeline-head">
                  <span>{{ item.message }}</span>
                  <span>{{ item.iteration ? `第 ${item.iteration} 轮` : item.time }}</span>
                </div>
              </div>
            </li>
          </ol>
          <p v-if="!store.timeline.length" class="empty-text">任务启动后显示节点和工具进度</p>
        </div>

        <div v-if="generatedText" class="detail-panel wide">
          <div class="panel-title">
            <Clock :size="14" /> 生成结果
          </div>
          <div class="generated-text">{{ generatedText }}</div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.one-sentence-view {
  height: 100%;
  overflow-y: auto;
  padding: var(--space-lg) var(--space-lg) var(--space-xl);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.title-group {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.title-icon {
  color: var(--primary);
}

.page-header h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
}

.status-primary { background: var(--primary-light); color: var(--primary); }
.status-success { background: var(--success-light); color: var(--success); }
.status-warning { background: var(--warning-light); color: var(--warning); }
.status-danger { background: var(--danger-light); color: var(--danger); }
.status-muted { background: var(--bg-tertiary); color: var(--text-secondary); }

.workbench {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
  gap: var(--space-lg);
  align-items: start;
}

.composer {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  padding: var(--space-md);
}

.composer label,
.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.composer label {
  margin-bottom: var(--space-xs);
}

.composer textarea,
.composer select,
.composer input {
  margin-bottom: var(--space-md);
  min-height: 36px;
}

.composer textarea {
  line-height: 1.7;
}

.composer-meta {
  display: flex;
  justify-content: space-between;
  margin: -8px 0 var(--space-md);
  font-size: 12px;
  color: var(--text-muted);
}

.action-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-sm);
  margin-top: var(--space-md);
}

.runtime {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-sm);
}

.metric,
.detail-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  padding: var(--space-md);
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.metric-value {
  margin-top: 4px;
  font-size: 18px;
  font-weight: 700;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.detail-panel.wide {
  grid-column: auto;
}

.panel-title {
  margin-bottom: var(--space-sm);
}

.detail-primary {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.4;
}

.detail-secondary {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-muted);
}

.detail-text {
  margin-top: var(--space-sm);
  font-size: 13px;
  line-height: 1.7;
}

.detail-text.muted {
  color: var(--text-secondary);
}

.empty-text {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.error-line {
  margin-bottom: var(--space-sm);
  padding: 8px 10px;
  border-radius: var(--radius);
  background: var(--danger-light);
  color: var(--danger);
  font-size: 13px;
}

.tool-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--space-sm);
}

.tool-chip {
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: var(--info-light);
  color: var(--info);
  font-size: 12px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 5px;
  width: 1px;
  background: var(--border);
}

.timeline li {
  position: relative;
  padding: 0 0 var(--space-sm) 20px;
}

.timeline-dot {
  position: absolute;
  top: 6px;
  left: 0;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--primary);
}

.timeline-head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-md);
  font-size: 13px;
}

.timeline-head span:last-child {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 12px;
}

.generated-text {
  max-height: 360px;
  overflow-y: auto;
  padding: var(--space-md);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .workbench,
  .detail-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 680px) {
  .one-sentence-view {
    padding: var(--space-md) var(--space-sm) var(--space-lg);
  }

  .metric-grid,
  .action-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .timeline-head {
    flex-direction: column;
    gap: 2px;
  }
}
</style>

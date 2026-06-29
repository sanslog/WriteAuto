<script setup>
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  GripVertical,
  Maximize2,
  Minimize2,
  Pencil,
  Plus,
  Save,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, toRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import Loading from '../components/common/Loading.vue'
import Modal from '../components/common/Modal.vue'
import MarkdownEditor from '../components/editor/MarkdownEditor.vue'
import GenerationPanel from '../components/writing/GenerationPanel.vue'
import ReviewPanel from '../components/writing/ReviewPanel.vue'
import { useChapterStore } from '../stores/chapter'
import { useGenerationStore } from '../stores/generation'
import { useNovelStore } from '../stores/novel'

const route = useRoute()
const novelId = toRef(route.params, 'id')
const novelStore = useNovelStore()
const chapterStore = useChapterStore()
const genStore = useGenerationStore()

// UI state
const showGenPanel = ref(false)
const showReviewPanel = ref(false)
const showSlidePanel = ref(false)
const preparation = ref(null)
const focusMode = ref(false)
const chapterListCollapsed = ref(false)
const genPanelCollapsed = ref(true)
const saving = ref(false)

// Chapter list scroll position preservation
const chapterListRef = ref(null)
async function fetchChaptersPreserveScroll() {
  const el = chapterListRef.value
  const saved = el ? el.scrollTop : 0
  await chapterStore.fetchChapters(novelId.value)
  if (el) {
    await nextTick()
    el.scrollTop = saved
  }
}

// Toast notification
const notification = ref({ show: false, message: '', type: 'error' })
let notifTimer = null
function showNotification(message, type = 'error', duration = 4000) {
  if (notifTimer) clearTimeout(notifTimer)
  notification.value = { show: true, message, type }
  notifTimer = setTimeout(() => { notification.value.show = false }, duration)
}

// Chapter CRUD dialogs
const showCreateChapter = ref(false)
const newChapterTitle = ref('')
const editingChapterId = ref(null)
const editingChapterTitle = ref('')
const deletingChapterId = ref(null)

// Drag state
const dragIndex = ref(null)
const dragOverIndex = ref(null)

const wordCount = computed(() => {
  if (!chapterStore.content) return 0
  return chapterStore.content.replace(/\s/g, '').length
})

const currentChapterTitle = computed(() => {
  return chapterStore.currentChapter?.title || '未选择章节'
})

onMounted(async () => {
  await chapterStore.enterNovel(novelId.value)
})

// Handle novel switch when Vue Router reuses the component
let lastNovelId = route.params.id
watch(() => route.params.id, async (newId) => {
  if (newId && newId !== lastNovelId) {
    lastNovelId = newId
    await chapterStore.enterNovel(newId)
  }
})

onUnmounted(() => {
  genStore.abortController?.abort()
})

// --- Chapter CRUD ---

async function handleCreateChapter() {
  if (!newChapterTitle.value.trim()) return
  await chapterStore.createChapter(novelId.value, { title: newChapterTitle.value.trim() })
  newChapterTitle.value = ''
  showCreateChapter.value = false
}

function startEditChapter(ch) {
  editingChapterId.value = ch.id
  editingChapterTitle.value = ch.title
}

async function finishEditChapter() {
  if (editingChapterId.value && editingChapterTitle.value.trim()) {
    await chapterStore.updateChapterTitle(editingChapterId.value, editingChapterTitle.value.trim())
  }
  editingChapterId.value = null
}

async function handleDeleteChapter() {
  if (deletingChapterId.value) {
    await chapterStore.deleteChapter(deletingChapterId.value)
    deletingChapterId.value = null
  }
}

// --- Drag & Drop ---

function onDragStart(index) {
  dragIndex.value = index
}

function onDragOver(e, index) {
  e.preventDefault()
  dragOverIndex.value = index
}

function onDragEnd() {
  if (dragIndex.value !== null && dragOverIndex.value !== null && dragIndex.value !== dragOverIndex.value) {
    chapterStore.reorderChapters(dragIndex.value, dragOverIndex.value)
  }
  dragIndex.value = null
  dragOverIndex.value = null
}

// --- Editor ---

async function handleSave() {
  if (!chapterStore.currentChapter) return
  saving.value = true
  const start = Date.now()
  try {
    const payload = {
      content: chapterStore.content,
      status: 'approved',
    }
    await chapterStore.saveChapter(chapterStore.currentChapter.id, payload)
    // 保存完成后通过网络刷新获取最新章节数据（保持列表滚动位置）
    await fetchChaptersPreserveScroll()
    const fresh = chapterStore.chapters.find(c => c.id === chapterStore.currentChapter.id)
    if (fresh) {
      await chapterStore.fetchChapter(fresh.id)
    }
    showNotification('保存成功', 'success', 2000)
  } finally {
    const elapsed = Date.now() - start
    if (elapsed < 1000) {
      await new Promise(r => setTimeout(r, 1000 - elapsed))
    }
    saving.value = false
  }
}

// --- Generation ---

async function openGenerationPanel() {
  const res = await genStore.prepare(novelId.value)
  if (res?.success) {
    preparation.value = res.data
    showSlidePanel.value = true
    genPanelCollapsed.value = false
    showReviewPanel.value = false
  }
}

async function handleStart(config) {
  try {
    await genStore.runSSE(preparation.value.generation_id, config)
  } catch (e) {
    showNotification('启动生成失败: ' + e.message, 'error', 5000)
  }
}

function handleJudge(judgment) {
  const genId = genStore.activeGen?.generation_id
  if (!genId) {
    showNotification('没有活跃的生成会话', 'error', 5000)
    return
  }
  genStore.judgeSSE(genId, judgment)
}

function handleCancel() {
  const genId = genStore.activeGen?.generation_id
  if (genId) {
    genStore.cancelGeneration(genId)
  }
  showSlidePanel.value = false
  showGenPanel.value = false
  showReviewPanel.value = false
}

// Watch for review panel state
watch(() => genStore.status?.step, async (step) => {
  showReviewPanel.value = step === 'waiting_input'
  if (step === 'waiting_input') {
    // Judge buttons must be interactive immediately
    genStore.loading = false
  }
  if (step === 'complete' || step === 'failed') {
    showReviewPanel.value = false
    showGenPanel.value = false
    if (step === 'complete') {
      await fetchChaptersPreserveScroll()
      // Auto-load the approved/draft chapters from this generation
      if (genStore.activeGen?.generation_id) {
        const genId = genStore.activeGen.generation_id
        const generated = chapterStore.chapters.find(
          ch => ch.generation_id === genId && (ch.status === 'approved' || ch.status === 'draft')
        )
        if (generated) {
          await chapterStore.fetchChapter(generated.id)
        }
      }
      showNotification('生成完成', 'success', 3000)
    } else {
      showNotification('生成失败', 'error', 5000)
    }
  }
})

// Watch for gen store errors
watch(() => genStore.error, (err) => {
  if (err) showNotification(err, 'error', 5000)
})

// Focus mode
function toggleFocusMode() {
  focusMode.value = !focusMode.value
}
</script>

<template>
  <div class="writing-view" :class="{ 'focus-mode': focusMode, 'chapter-collapsed': chapterListCollapsed, 'gen-panel-open': showSlidePanel && !genPanelCollapsed }">
    <!-- Chapter List Sidebar -->
    <aside class="chapter-sidebar">
      <div class="chapter-sidebar-header">
        <h3 class="chapter-sidebar-title">
          <FileText :size="14" />
          <span v-show="!chapterListCollapsed">章节</span>
        </h3>
        <button class="btn-icon" @click="chapterListCollapsed = !chapterListCollapsed" title="收起">
          <ChevronLeft v-if="!chapterListCollapsed" :size="14" />
          <ChevronRight v-else :size="14" />
        </button>
      </div>

      <div v-show="!chapterListCollapsed" class="chapter-list-actions">
        <button class="btn-primary btn-sm w-full" @click="showCreateChapter = true">
          <Plus :size="12" /> 新建章节
        </button>
      </div>

      <div ref="chapterListRef" class="chapter-list">
        <div v-if="chapterStore.chapters.length === 0" class="empty-state">
          <p>暂无章节</p>
          <button class="btn-ghost btn-sm" @click="showCreateChapter = true">创建第一个章节</button>
        </div>

        <div
          v-for="(ch, i) in chapterStore.chapters"
          :key="ch.id"
          :class="[
            'chapter-item',
            { active: chapterStore.currentChapter?.id === ch.id },
            { dragging: dragIndex === i },
            { 'drag-over': dragOverIndex === i },
          ]"
          draggable="true"
          @click="chapterStore.fetchChapter(ch.id)"
          @dragstart="onDragStart(i)"
          @dragover.prevent="onDragOver($event, i)"
          @dragend="onDragEnd"
        >
          <span class="drag-handle" @mousedown.stop><GripVertical :size="12" /></span>
          <span class="ch-index">{{ i + 1 }}</span>
          <span class="ch-title truncate">{{ ch.title || '未命名' }}</span>
          <span :class="['ch-status-badge', `status-${ch.status}`]">
            {{ ch.status === 'approved' ? '✓' : ch.status === 'draft' ? '草' : ch.status?.[0] }}
          </span>

          <!-- Hover actions -->
          <div class="chapter-actions" @mousedown.stop>
            <button class="btn-icon btn-xs" @click="startEditChapter(ch)" title="编辑标题">
              <Pencil :size="12" />
            </button>
            <button class="btn-icon btn-xs danger" @click="deletingChapterId = ch.id" title="删除">
              <Trash2 :size="12" />
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Editor Area -->
    <main class="editor-main">
      <!-- Editor Toolbar -->
      <div class="editor-toolbar">
        <div class="toolbar-left">
          <span class="current-chapter">{{ currentChapterTitle }}</span>
          <span v-if="chapterStore.content" class="word-count">{{ wordCount }} 字</span>
        </div>
        <div class="toolbar-right">
          <button class="btn-ghost btn-sm" @click="openGenerationPanel" :disabled="genStore.loading">
            <Sparkles :size="14" /> AI 续写
          </button>
          <button class="btn-icon" @click="toggleFocusMode" :title="focusMode ? '退出专注模式' : '专注模式'">
            <Maximize2 v-if="!focusMode" :size="16" />
            <Minimize2 v-else :size="16" />
          </button>
        </div>
      </div>

      <!-- Editor / No-chapter placeholder -->
      <template v-if="chapterStore.currentChapter">
        <div class="editor-content">
          <MarkdownEditor v-model="chapterStore.content" />
        </div>

        <!-- Editor Footer -->
        <div class="editor-footer">
          <button
            class="btn-primary"
            @click="handleSave"
            :disabled="saving"
          >
            <Save :size="14" />
            {{ saving ? '保存中...' : '保存章节' }}
          </button>
        </div>
      </template>
      <div v-else class="editor-empty">
        <FileText :size="48" />
        <p>选择或创建一个章节开始写作</p>
        <button class="btn-primary" @click="showCreateChapter = true">
          <Plus :size="14" /> 创建章节
        </button>
      </div>
    </main>

    <!-- Slide-in AI Panel -->
    <Transition name="slide-right">
      <aside v-if="showSlidePanel && !genPanelCollapsed" class="ai-slide-panel">
        <div class="ai-panel-header">
          <h3>AI 续写</h3>
          <button class="btn-icon" @click="showSlidePanel = false; genPanelCollapsed = true">
            <X :size="16" />
          </button>
        </div>
        <div class="ai-panel-body" v-if="preparation">
          <GenerationPanel
            :preparation="preparation"
            :loading="genStore.loading"
            @start="handleStart"
          />
        </div>
      </aside>
    </Transition>

    <!-- Review Overlay -->
    <Modal
      :show="showReviewPanel"
      title="审核生成内容"
      width="700px"
      @close="showReviewPanel = false"
    >
      <ReviewPanel
        v-if="showReviewPanel"
        :state="genStore.status?.state || {}"
        :loading="genStore.loading"
        @judge="handleJudge"
      />
    </Modal>

    <!-- Generating overlay (streaming mode) -->
    <div v-if="genStore.status?.step === 'generating'" class="gen-overlay">
      <div class="gen-card card">
        <div class="gen-stream-header">
          <span class="gen-stream-title">AI 正在生成...</span>
          <button class="btn-ghost btn-sm gen-cancel-btn" @click="handleCancel">
            取消生成
          </button>
        </div>
        <div v-if="genStore.status?.generatedText" class="gen-stream-text">
          {{ genStore.status.generatedText }}
        </div>
        <div v-else class="gen-stream-placeholder">
          <Loading text="AI 思考中..." />
        </div>
      </div>
    </div>

    <!-- Create Chapter Modal -->
    <Modal
      :show="showCreateChapter"
      title="新建章节"
      @close="showCreateChapter = false"
    >
      <form @submit.prevent="handleCreateChapter">
        <label class="form-label">章节标题</label>
        <input
          v-model="newChapterTitle"
          placeholder="输入章节标题"
          autofocus
          class="w-full"
        />
        <div class="modal-footer-btns">
          <button type="button" class="btn-ghost" @click="showCreateChapter = false">取消</button>
          <button type="submit" class="btn-primary" :disabled="!newChapterTitle.trim()">创建</button>
        </div>
      </form>
    </Modal>

    <!-- Edit Chapter Title Modal -->
    <Modal
      :show="!!editingChapterId"
      title="编辑章节标题"
      @close="editingChapterId = null"
    >
      <form @submit.prevent="finishEditChapter">
        <label class="form-label">章节标题</label>
        <input
          v-model="editingChapterTitle"
          placeholder="输入章节标题"
          class="w-full"
          autofocus
        />
        <div class="modal-footer-btns">
          <button type="button" class="btn-ghost" @click="editingChapterId = null">取消</button>
          <button type="submit" class="btn-primary" :disabled="!editingChapterTitle.trim()">保存</button>
        </div>
      </form>
    </Modal>

    <!-- Delete Chapter Confirmation -->
    <Modal
      :show="!!deletingChapterId"
      title="确认删除"
      @close="deletingChapterId = null"
    >
      <p class="delete-confirm-text">确定要删除这个章节吗？此操作不可撤销。</p>
      <div class="modal-footer-btns">
        <button class="btn-ghost" @click="deletingChapterId = null">取消</button>
        <button class="btn-danger" @click="handleDeleteChapter">删除</button>
      </div>
    </Modal>

    <!-- Toast Notification -->
    <Transition name="toast-fade">
      <div v-if="notification.show" class="toast" :class="'toast-' + notification.type">
        {{ notification.message }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.writing-view {
  display: flex;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* ===== Chapter Sidebar ===== */
.chapter-sidebar {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width var(--transition) var(--ease);
  overflow: hidden;
}

.chapter-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--border);
}

.chapter-sidebar-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.chapter-list-actions {
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--border);
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-sm);
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-sm);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  transition: all var(--transition-fast) var(--ease);
  position: relative;
  margin-bottom: 2px;
  user-select: none;
}

.chapter-item:hover {
  background: var(--bg-tertiary);
}

.chapter-item.active {
  background: var(--primary-light);
  color: var(--primary);
  font-weight: 500;
}

.chapter-item.dragging {
  opacity: 0.4;
  background: var(--bg-tertiary);
}

.chapter-item.drag-over {
  border-top: 2px solid var(--primary);
}

.drag-handle {
  cursor: grab;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity var(--transition-fast) var(--ease);
  flex-shrink: 0;
}

.chapter-item:hover .drag-handle {
  opacity: 0.6;
}
.drag-handle:active { cursor: grabbing; }

.ch-index {
  font-size: 11px;
  color: var(--text-muted);
  min-width: 18px;
  flex-shrink: 0;
}

.ch-title {
  flex: 1;
  min-width: 0;
}

.ch-status-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: var(--radius-full);
  font-weight: 600;
  flex-shrink: 0;
}
.status-approved { background: var(--success-light); color: var(--success); }
.status-draft { background: var(--warning-light); color: var(--warning); }
.status-generated { background: var(--info-light); color: var(--info); }

.chapter-actions {
  display: none;
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  gap: 2px;
  background: rgba(0, 0, 0, 0.55);
  border-radius: var(--radius);
  padding: 2px;
}

.chapter-item:hover .chapter-actions {
  display: flex;
}
.chapter-item:hover .chapter-actions .btn-icon {
  color: #fff;
}
.chapter-item:hover .chapter-actions .btn-icon:hover {
  background: rgba(255, 255, 255, 0.15);
}
.chapter-item:hover .chapter-actions .btn-icon.danger:hover {
  background: rgba(239, 68, 68, 0.35);
}

.btn-xs {
  padding: 2px 4px;
}
.btn-xs.danger { color: var(--danger); }
.btn-xs.danger:hover { background: var(--danger-light); }

/* ===== Editor Main ===== */
.editor-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  transition: margin-right var(--transition-slow) var(--ease-out);
}

.gen-panel-open .editor-main {
  margin-right: 420px;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) var(--space-lg);
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  min-height: 48px;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.current-chapter {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.word-count {
  font-size: 12px;
  color: var(--text-muted);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.editor-content {
  flex: 1;
  overflow: hidden;
  padding: var(--space-md) var(--space-lg);
}

.editor-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  color: var(--text-muted);
  user-select: none;
}
.editor-empty p {
  font-size: 14px;
  margin: 0;
}
.editor-empty svg {
  opacity: 0.3;
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-sm) var(--space-lg);
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

/* ===== AI Slide-in Panel ===== */
.ai-slide-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 420px;
  background: var(--bg);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  z-index: 10;
}

.ai-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md);
  border-bottom: 1px solid var(--border);
}

.ai-panel-header h3 {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.ai-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-md);
}

/* ===== Gen Overlay ===== */
.gen-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-overlay);
}

.gen-card {
  padding: var(--space-xl);
  min-width: 360px;
  max-width: 600px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.gen-stream-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
  flex-shrink: 0;
}

.gen-stream-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary);
}

.gen-stream-text {
  text-align: left;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'SimSun', serif;
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-y: auto;
  max-height: 60vh;
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius);
  border: 1px solid var(--border);
}

.gen-stream-placeholder {
  padding: var(--space-lg) 0;
}

.gen-hint {
  margin-top: var(--space-md);
  font-size: 12px;
  color: var(--text-muted);
}

.gen-cancel-btn {
  margin-top: var(--space-lg);
  opacity: 0.6;
  transition: opacity var(--transition-fast) var(--ease);
}
.gen-cancel-btn:hover { opacity: 1; }

/* ===== Focus Mode ===== */
.focus-mode .chapter-sidebar {
  width: 0 !important;
  overflow: hidden;
  border: none;
}

.focus-mode .ai-slide-panel {
  display: none;
}

.focus-mode .editor-toolbar {
  padding: var(--space-xs) var(--space-lg);
  border-bottom-color: var(--border-light);
}

.focus-mode .editor-footer {
  background: var(--bg);
  border-top-color: var(--border-light);
}

/* ===== Modal form styles ===== */
.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

.modal-footer-btns {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
}

.delete-confirm-text {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .chapter-sidebar {
    width: 200px;
  }
  .ai-slide-panel {
    width: 100%;
    position: absolute;
    right: 0;
    top: 0;
    height: 100%;
    z-index: var(--z-overlay);
  }
}

/* ===== Toast Notification ===== */
.toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  z-index: var(--z-modal);
  box-shadow: var(--shadow-lg);
  pointer-events: none;
  white-space: nowrap;
}
.toast-error {
  background: var(--danger);
  color: #fff;
}
.toast-success {
  background: var(--success);
  color: #fff;
}
.toast-warning {
  background: var(--warning);
  color: #fff;
}
.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s ease;
}
.toast-fade-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
.toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
</style>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useNovelStore } from '../stores/novel'
import { useChapterStore } from '../stores/chapter'
import { useGenerationStore } from '../stores/generation'
import MarkdownEditor from '../components/editor/MarkdownEditor.vue'
import Loading from '../components/common/Loading.vue'
import GenerationPanel from '../components/writing/GenerationPanel.vue'
import ReviewPanel from '../components/writing/ReviewPanel.vue'

const route = useRoute()
const novelId = route.params.id
const novelStore = useNovelStore()
const chapterStore = useChapterStore()
const genStore = useGenerationStore()

const showGenPanel = ref(false)
const preparation = ref(null)

onMounted(async () => {
  await novelStore.fetchNovel(novelId)
  await chapterStore.fetchChapters(novelId)
})

onUnmounted(() => {
  genStore.stopPolling()
})

async function openGenerationPanel() {
  const res = await genStore.prepare(novelId)
  if (res?.success) {
    preparation.value = res.data
    showGenPanel.value = true
  }
}

async function handleStart(config) {
  const res = await genStore.run(preparation.value.generation_id, config)
  if (res?.success) {
    showGenPanel.value = false
  }
}

async function handleJudge(judgment) {
  await genStore.submitJudge(genStore.activeGen?.generation_id, judgment)
}
</script>

<template>
  <div class="editor-view">
    <div class="editor-toolbar">
      <div class="novel-info">
        <h1>{{ novelStore.currentNovel?.title || '未命名作品' }}</h1>
        <span class="cursor-badge">
          进度: 第{{ (novelStore.currentNovel?.cursor_position || 0) + 1 }}节
        </span>
      </div>
      <div class="toolbar-actions">
        <button class="btn-primary" @click="openGenerationPanel" :disabled="genStore.loading">
          AI 续写
        </button>
      </div>
    </div>

    <div class="editor-body">
      <div class="chapter-list">
        <h3>章节列表</h3>
        <div v-if="chapterStore.chapters.length === 0" class="empty-state">
          暂无章节
        </div>
        <div
          v-for="ch in chapterStore.chapters"
          :key="ch.id"
          :class="['chapter-item', { active: chapterStore.currentChapter?.id === ch.id }]"
          @click="chapterStore.fetchChapter(ch.id)"
        >
          <span class="ch-title">{{ ch.title || '未命名' }}</span>
          <span :class="['ch-status', `status-${ch.status}`]">
            {{ ch.status === 'approved' ? '已批准' : ch.status === 'draft' ? '草稿' : ch.status }}
          </span>
        </div>
      </div>

      <div class="editor-main">
        <!-- Generation Panel Modal -->
        <Transition name="scale">
          <div v-if="showGenPanel && preparation" class="gen-overlay">
            <div class="gen-container card">
              <div class="gen-header">
                <h3>AI 续写 — {{ preparation.next_node_title || '新章节' }}</h3>
                <button class="modal-close" @click="showGenPanel = false">&times;</button>
              </div>
              <GenerationPanel
                :preparation="preparation"
                :loading="genStore.loading"
                @start="handleStart"
              />
            </div>
          </div>
        </Transition>

        <!-- Review Panel (when waiting for judgment) -->
        <div v-if="genStore.status?.step === 'waiting_input'" class="review-overlay">
          <div class="review-container card">
            <ReviewPanel
              :state="genStore.status?.state || {}"
              :loading="genStore.loading"
              @judge="handleJudge"
            />
          </div>
        </div>

        <!-- Generating indicator -->
        <div v-if="genStore.status?.step === 'generating'" class="gen-indicator">
          <Loading text="AI 正在生成中..." />
        </div>

        <MarkdownEditor
          v-model="chapterStore.content"
          :readonly="chapterStore.currentChapter?.status === 'approved'"
        />

        <div v-if="chapterStore.currentChapter" class="editor-footer">
          <button
            class="btn-primary"
            @click="chapterStore.saveChapter(chapterStore.currentChapter.id, {
              content: chapterStore.content,
            })"
          >
            保存章节
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.novel-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.novel-info h1 {
  font-size: 20px;
  margin: 0;
}
.cursor-badge {
  font-size: 13px;
  color: var(--primary);
  background: rgba(74, 144, 217, 0.1);
  padding: 2px 10px;
  border-radius: 10px;
}
.editor-body {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}
.chapter-list {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding-right: 16px;
  overflow-y: auto;
}
.chapter-list h3 {
  font-size: 14px;
  margin-bottom: 12px;
}
.chapter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 4px;
}
.chapter-item:hover { background: var(--bg-secondary); }
.chapter-item.active { background: rgba(74, 144, 217, 0.1); }
.ch-status {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
}
.status-approved { background: #e6f7e6; color: var(--success); }
.status-draft { background: #fff3e0; color: var(--warning); }
.editor-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.editor-footer {
  display: flex;
  justify-content: flex-end;
}
.gen-overlay, .review-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
}
.gen-container, .review-container {
  width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}
.gen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.gen-header h3 { font-size: 16px; margin: 0; }
.modal-close {
  background: none;
  font-size: 22px;
  color: var(--text-secondary);
  padding: 0 4px;
  line-height: 1;
}
.gen-indicator {
  padding: 16px;
}
</style>

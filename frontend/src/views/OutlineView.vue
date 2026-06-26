<script setup>
import { Search, Target } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import OutlineEditor from '../components/outline/OutlineEditor.vue'
import PlotNodeCard from '../components/outline/PlotNodeCard.vue'
import { useNovelStore } from '../stores/novel'
import { useOutlineStore } from '../stores/outline'

const route = useRoute()
const novelId = route.params.id
const outlineStore = useOutlineStore()
const novelStore = useNovelStore()

const searchQuery = ref('')
const dragIndex = ref(null)
const dragOverIndex = ref(null)

const filteredNodes = computed(() => {
  if (!searchQuery.value.trim()) return outlineStore.plotNodes
  const q = searchQuery.value.toLowerCase()
  return outlineStore.plotNodes.filter(n =>
    (n.title || '').toLowerCase().includes(q) ||
    (n.summary || '').toLowerCase().includes(q)
  )
})

const cursorNode = computed(() => {
  const idx = novelStore.currentNovel?.cursor_position || 0
  return outlineStore.plotNodes[idx]
})

onMounted(async () => {
  await novelStore.fetchNovel(novelId)
  await outlineStore.fetchOutline(novelId)
})

async function handleCreate(data) {
  await outlineStore.createNode({
    novel_id: novelId,
    sort_order: outlineStore.plotNodes.length,
    ...data,
  })
}

async function handleUpdate(nodeId, data) {
  await outlineStore.updateNode(nodeId, data)
}

async function handleDelete(nodeId) {
  await outlineStore.deleteNode(nodeId)
}

async function handleSetCursor(index) {
  await outlineStore.updateCursor(novelId, index)
}

// Drag & Drop
function onDragStart(index) {
  dragIndex.value = index
}

function onDragOver(e, index) {
  e.preventDefault()
  dragOverIndex.value = index
}

function onDragEnd() {
  if (dragIndex.value !== null && dragOverIndex.value !== null && dragIndex.value !== dragOverIndex.value) {
    outlineStore.reorderNodes(dragIndex.value, dragOverIndex.value)
  }
  dragIndex.value = null
  dragOverIndex.value = null
}
</script>

<template>
  <div class="outline-view">
    <!-- Cursor info bar -->
    <div class="cursor-bar" v-if="cursorNode">
      <Target :size="14" />
      <span>当前位于：<strong>第 {{ (novelStore.currentNovel?.cursor_position || 0) + 1 }} 节</strong> — {{ cursorNode.title
        }}</span>
    </div>

    <!-- Toolbar -->
    <div class="outline-toolbar">
      <div class="search-box">
        <Search :size="14" class="search-icon" />
        <input v-model="searchQuery" placeholder="搜索剧情节点..." class="search-input" />
      </div>
      <!-- <button class="btn-primary btn-sm" @click="$refs.editor?.openCreate()">
        <Plus :size="14" /> 添加节点
      </button> -->
    </div>

    <!-- Outline Editor (toolbar + dialog) -->
    <OutlineEditor ref="editor" :nodes="outlineStore.plotNodes" :cursor="novelStore.currentNovel?.cursor_position || 0"
      :loading="outlineStore.loading" @create="handleCreate" @update="handleUpdate" @delete="handleDelete" />

    <!-- Node list -->
    <div v-if="outlineStore.plotNodes.length === 0" class="empty-state">
      <p>暂无剧情节点，点击「添加节点」开始构建大纲</p>
    </div>

    <div v-else-if="filteredNodes.length === 0" class="empty-state">
      <p>没有找到匹配「{{ searchQuery }}」的节点</p>
    </div>

    <div v-else class="node-list">
      <PlotNodeCard v-for="(node, i) in filteredNodes" :key="node.id" :node="node" :index="i"
        :isCursor="i === (novelStore.currentNovel?.cursor_position || 0)" :dragging="dragIndex === i"
        :dragOver="dragOverIndex === i" draggable="true" @edit="$refs.editor?.openEdit(node)"
        @delete="handleDelete(node.id)" @setCursor="handleSetCursor(i)" @dragstart="onDragStart(i)"
        @dragover.prevent="onDragOver($event, i)" @dragend="onDragEnd" />
    </div>
  </div>
</template>

<style scoped>
.outline-view {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-lg);
  overflow-y: auto;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Cursor bar */
.cursor-bar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--primary-light);
  color: var(--primary);
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: var(--space-md);
}

.cursor-bar svg {
  flex-shrink: 0;
}

.cursor-bar strong {
  font-weight: 700;
}

/* Toolbar */
.outline-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: 1;
  max-width: 320px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input {
  padding-left: 32px;
  font-size: 13px;
  width: 100%;
}

/* Node list */
.node-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  flex: 1;
}
</style>

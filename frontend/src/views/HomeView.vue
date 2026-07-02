<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNovelStore } from '../stores/novel'
import { Plus, BookOpen, Sparkles } from 'lucide-vue-next'
import NovelCard from '../components/novel/NovelCard.vue'
import NovelCreateDialog from '../components/novel/NovelCreateDialog.vue'

const router = useRouter()
const novelStore = useNovelStore()
const showCreate = ref(false)
const editingNovel = ref(null)

onMounted(() => {
  novelStore.fetchNovels()
})

async function handleCreate(data) {
  const novel = await novelStore.createNovel(data)
  showCreate.value = false
  router.push(`/novel/${novel.id}`)
}

async function handleEditSave(data) {
  const { id, ...payload } = data
  await novelStore.updateNovel(id, payload)
  editingNovel.value = null
}

function openNovel(id) {
  router.push(`/novel/${id}`)
}

function handleEditClick(novel) {
  editingNovel.value = novel
}
</script>

<template>
  <div class="home">
    <div class="home-header">
      <div class="header-left">
        <BookOpen :size="24" class="header-icon" />
        <div>
          <h1>我的作品</h1>
          <p class="header-subtitle">{{ novelStore.novels.length }} 部作品</p>
        </div>
      </div>
      <button class="btn-primary" @click="showCreate = true">
        <Plus :size="16" /> 新建作品
      </button>
    </div>

    <div v-if="novelStore.loading" class="loading-grid">
      <div v-for="i in 3" :key="i" class="card-shimmer shimmer" />
    </div>

    <div v-else-if="novelStore.novels.length === 0" class="empty-state">
      <Sparkles :size="56" class="empty-state-icon" />
      <h2>还没有作品</h2>
      <p>点击「新建作品」开始你的创作之旅吧</p>
      <button class="btn-primary" @click="showCreate = true">
        <Plus :size="16" /> 创建第一部作品
      </button>
    </div>

    <div v-else class="novel-grid">
      <div
        v-for="(novel, i) in novelStore.novels"
        :key="novel.id"
        @click="openNovel(novel.id)"
        :style="{ animationDelay: (i * 0.08) + 's' }"
        class="novel-card-wrapper"
      >
        <NovelCard :novel="novel" @edit="handleEditClick" />
      </div>
    </div>

    <NovelCreateDialog
      :show="showCreate || !!editingNovel"
      :novel="editingNovel"
      @close="showCreate = false; editingNovel = null"
      @created="handleCreate"
      @saved="handleEditSave"
    />
  </div>
</template>

<style scoped>
.home {
  padding: var(--space-xl) var(--space-lg);
  overflow-y: auto;
  height: 100%;
}

.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
  flex-wrap: wrap;
  gap: var(--space-md);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.header-icon {
  color: var(--primary);
  flex-shrink: 0;
}

.home-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.header-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.novel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-lg);
}

.novel-card-wrapper {
  animation: fadeInUp var(--transition) var(--ease-out) backwards;
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-lg);
}

.card-shimmer {
  height: 160px;
  border-radius: var(--radius-lg);
}

.empty-state {
  padding: var(--space-2xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  color: var(--text-secondary);
}

.empty-state-icon {
  color: var(--text-muted);
  opacity: 0.4;
}

.empty-state h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

.empty-state p {
  font-size: 14px;
  text-align: center;
}
</style>

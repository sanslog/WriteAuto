<script setup>
import { Map, PenTool, Sparkles, Undo2Icon, Users } from 'lucide-vue-next'
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNovelStore } from '../../stores/novel'
import { useOutlineStore } from '../../stores/outline'

const route = useRoute()
const router = useRouter()
const novelStore = useNovelStore()
const outlineStore = useOutlineStore()

const novelId = computed(() => route.params.id)
const novelTitle = computed(() => novelStore.currentNovel?.title || '加载中...')
const cursorPos = computed(() => novelStore.currentNovel?.cursor_position || 0)

const tabs = computed(() => [
  { name: '写作', path: `/novel/${novelId.value}`, icon: PenTool },
  { name: '大纲', path: `/novel/${novelId.value}/outline`, icon: Map },
  { name: '角色', path: `/novel/${novelId.value}/characters`, icon: Users },
  { name: '伏笔', path: `/novel/${novelId.value}/foreshadows`, icon: Sparkles },
])

const activeTab = computed(() => route.path)

onMounted(async () => {
  if (novelId.value) {
    await novelStore.fetchNovel(novelId.value)
  }
})

watch(() => novelId.value, async (newId) => {
  if (newId) {
    await novelStore.fetchNovel(newId)
  }
})

function goToTab(path) {
  if (route.path !== path) router.push(path)
}
</script>

<template>
  <div class="novel-layout">
    <!-- Novel header bar -->
    <header class="novel-header">
      <div class="header-left">
        <router-link to="/" class="back-link" title="返回作品列表">
          <Undo2-icon/>
        </router-link>
        <h1 class="novel-title">{{ novelTitle }}</h1>
        <span class="cursor-badge">
          第 {{ cursorPos + 1 }} 节
        </span>
      </div>

      <nav class="header-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.path"
          class="tab-btn"
          :class="{ active: activeTab === tab.path }"
          @click="goToTab(tab.path)"
        >
          <component :is="tab.icon" :size="16" />
          {{ tab.name }}
        </button>
        <div class="tab-indicator" :class="activeTab" />
      </nav>
    </header>

    <!-- Page content with transition -->
    <main class="novel-content">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.novel-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Header bar */
.novel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--novel-header-height);
  padding: 0 var(--space-lg);
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  flex-shrink: 0;
  gap: var(--space-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  min-width: 0;
}

.back-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 16px;
  flex-shrink: 0;
  transition: all var(--transition-fast) var(--ease);
}
.back-link:hover {
  background: var(--bg-secondary);
  color: var(--text);
}

.novel-title {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
}

.cursor-badge {
  font-size: 12px;
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;
  flex-shrink: 0;
}

/* Tabs */
.header-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  position: relative;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  border: none;
  border-radius: var(--radius) var(--radius) 0 0;
  transition: all var(--transition-fast) var(--ease);
  position: relative;
  z-index: 1;
}
.tab-btn:hover {
  color: var(--text);
  background: var(--bg-secondary);
}
.tab-btn.active {
  color: var(--primary);
  background: var(--primary-light);
  font-weight: 600;
}

/* Content area */
.novel-content {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}
</style>

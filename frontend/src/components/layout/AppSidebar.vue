<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '../../stores/settings'
import {
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Settings,
} from 'lucide-vue-next'

const route = useRoute()
const settings = useSettingsStore()

const isCollapsed = computed(() => settings.sidebarCollapsed)

// Auto-collapse sidebar when entering a novel detail page
watch(() => route.path, (path) => {
  if (path.startsWith('/novel/')) {
    settings.setSidebarCollapsed(true)
  }
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header">
      <router-link to="/" class="sidebar-brand">
        <BookOpen :size="20" class="brand-icon" />
        <span v-show="!isCollapsed" class="brand-text">WriteAuto</span>
      </router-link>
      <button class="btn-icon collapse-btn" @click="settings.toggleSidebar()" :title="isCollapsed ? '展开' : '收起'">
        <ChevronLeft v-if="!isCollapsed" :size="18" />
        <ChevronRight v-else :size="18" />
      </button>
    </div>

    <nav class="sidebar-nav">
      <router-link
        to="/"
        class="nav-item"
        active-class="active"
        exact-active-class="active"
        :class="{ 'nav-icon-only': isCollapsed }"
      >
        <BookOpen :size="18" />
        <span v-show="!isCollapsed">作品列表</span>
      </router-link>

      <div class="nav-spacer" />

      <router-link
        to="/settings"
        class="nav-item"
        active-class="active"
        :class="{ 'nav-icon-only': isCollapsed }"
      >
        <Settings :size="18" />
        <span v-show="!isCollapsed">设置</span>
      </router-link>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width var(--transition) var(--ease);
  overflow: hidden;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

/* Header area */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 8px;
  border-bottom: 1px solid var(--border);
  min-height: 56px;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text);
  font-weight: 700;
  font-size: 16px;
  text-decoration: none;
  padding: 4px 8px;
  border-radius: var(--radius);
  transition: background var(--transition-fast) var(--ease);
  overflow: hidden;
  white-space: nowrap;
}
.sidebar-brand:hover {
  background: var(--bg-tertiary);
}
.brand-icon {
  flex-shrink: 0;
  color: var(--primary);
}
.brand-text {
  transition: opacity var(--transition-fast) var(--ease);
}

.collapse-btn {
  flex-shrink: 0;
  padding: 6px;
}
.sidebar.collapsed .collapse-btn {
  margin: 0 auto;
}



.nav-spacer {
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all var(--transition-fast) var(--ease);
  overflow: hidden;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text);
}

.nav-item.active {
  background: var(--primary);
  color: #fff;
  font-weight: 600;
}

.nav-item.active:hover {
  background: var(--primary-hover);
  color: #fff;
}

/* Collapsed state — icons centered */
.nav-icon-only {
  justify-content: center;
  padding: 10px;
}

.nav-item svg {
  flex-shrink: 0;
}
</style>

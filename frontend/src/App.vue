<script setup>
import AppSidebar from './components/layout/AppSidebar.vue'
import Toast from './components/common/Toast.vue'
import { useSettingsStore } from './stores/settings'

const settings = useSettingsStore()
</script>

<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': settings.sidebarCollapsed }">
    <AppSidebar />
    <div class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </transition>
      </router-view>
    </div>
  </div>
  <Toast />
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  transition: all var(--transition) var(--ease);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* When sidebar is collapsed, main content expands */
.sidebar-collapsed .app-main {
  margin-left: 0;
}
</style>

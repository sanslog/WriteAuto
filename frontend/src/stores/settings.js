import { defineStore } from 'pinia'
import { settingsAPI } from '../api/settings'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    settings: {},
    loading: false,
    // UI state (not synced to backend)
    sidebarCollapsed: false,
  }),
  actions: {
    async fetchSettings() {
      this.loading = true
      try {
        const res = await settingsAPI.get()
        this.settings = res.data || {}
      } finally {
        this.loading = false
      }
    },
    async updateSettings(data) {
      const res = await settingsAPI.update(data)
      this.settings = res.data || {}
      return res.data
    },
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    setSidebarCollapsed(value) {
      this.sidebarCollapsed = !!value
    },
  },
})

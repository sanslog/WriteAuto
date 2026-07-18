import { defineStore } from "pinia"
import { mcpAPI } from "../api/mcp"

export const useMCPStore = defineStore("mcp", {
  state: () => ({
    services: [],
    loading: false,
    error: null,
  }),
  actions: {
    async fetchServices() {
      this.loading = true
      this.error = null
      try {
        const res = await mcpAPI.list()
        this.services = res.data || []
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async createService(data) {
      this.error = null
      const res = await mcpAPI.create(data)
      if (res.success) {
        this.services.push(res.data)
      } else {
        this.error = res.error || "创建失败"
      }
      return res
    },
    async updateService(id, data) {
      this.error = null
      const res = await mcpAPI.update(id, data)
      if (res.success) {
        const idx = this.services.findIndex((s) => s.id === id)
        if (idx !== -1) this.services[idx] = res.data
      } else {
        this.error = res.error || "更新失败"
      }
      return res
    },
    async deleteService(id) {
      this.error = null
      const res = await mcpAPI.delete(id)
      if (res.success) {
        this.services = this.services.filter((s) => s.id !== id)
      } else {
        this.error = res.error || "删除失败"
      }
      return res
    },
    async discoverTools(id) {
      this.error = null
      try {
        return await mcpAPI.discover(id)
      } catch (e) {
        this.error = e.message
        return { success: false, error: e.message }
      }
    },
  },
})

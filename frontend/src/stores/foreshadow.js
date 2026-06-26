import { defineStore } from 'pinia'
import { foreshadowAPI } from '../api/foreshadow'

export const useForeshadowStore = defineStore('foreshadow', {
  state: () => ({
    foreshadows: [],
    loading: false,
  }),
  actions: {
    async fetchForeshadows(novelId) {
      this.loading = true
      try {
        const res = await foreshadowAPI.list(novelId)
        this.foreshadows = res.data || []
      } finally {
        this.loading = false
      }
    },
    async createForeshadow(data) {
      const res = await foreshadowAPI.create(data)
      this.foreshadows.push(res.data)
      return res.data
    },
    async updateForeshadow(id, data) {
      const res = await foreshadowAPI.update(id, data)
      const idx = this.foreshadows.findIndex(f => f.id === id)
      if (idx !== -1) this.foreshadows[idx] = res.data
      return res.data
    },
    async deleteForeshadow(id) {
      await foreshadowAPI.delete(id)
      this.foreshadows = this.foreshadows.filter(f => f.id !== id)
    },
  },
})

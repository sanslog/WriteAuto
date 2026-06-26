import { defineStore } from 'pinia'
import { novelAPI } from '../api/novel'

export const useNovelStore = defineStore('novel', {
  state: () => ({
    novels: [],
    currentNovel: null,
    loading: false,
  }),
  actions: {
    async fetchNovels() {
      this.loading = true
      try {
        const res = await novelAPI.list()
        this.novels = res.data || []
      } finally {
        this.loading = false
      }
    },
    async fetchNovel(id) {
      this.loading = true
      try {
        const res = await novelAPI.get(id)
        this.currentNovel = res.data
      } finally {
        this.loading = false
      }
    },
    async createNovel(data) {
      const res = await novelAPI.create(data)
      this.novels.unshift(res.data)
      return res.data
    },
    async updateNovel(id, data) {
      const res = await novelAPI.update(id, data)
      this.currentNovel = res.data
      return res.data
    },
    async deleteNovel(id) {
      await novelAPI.delete(id)
      this.novels = this.novels.filter(n => n.id !== id)
    },
  },
})

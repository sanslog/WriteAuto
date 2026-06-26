import { defineStore } from 'pinia'
import { chapterAPI } from '../api/chapter'

export const useChapterStore = defineStore('chapter', {
  state: () => ({
    chapters: [],
    currentChapter: null,
    content: '',
    loading: false,
  }),
  actions: {
    resetCurrentChapter() {
      this.currentChapter = null
      this.content = ''
    },
    async enterNovel(novelId) {
      this.resetCurrentChapter()
      this.chapters = []
      this.loading = true
      try {
        const res = await chapterAPI.list(novelId)
        this.chapters = res.data || []
      } finally {
        this.loading = false
      }
    },
    async fetchChapters(novelId) {
      this.loading = true
      try {
        const res = await chapterAPI.list(novelId)
        this.chapters = res.data || []
      } finally {
        this.loading = false
      }
    },
    async fetchChapter(id) {
      this.loading = true
      try {
        const res = await chapterAPI.get(id)
        this.currentChapter = res.data
        this.content = res.data?.content || ''
      } finally {
        this.loading = false
      }
    },
    async saveChapter(id, data) {
      const res = await chapterAPI.update(id, data)
      const idx = this.chapters.findIndex(c => c.id === id)
      if (idx !== -1) this.chapters[idx] = res.data
      this.currentChapter = res.data
      return res.data
    },
    async createChapter(novelId, data) {
      const payload = {
        novel_id: novelId,
        title: data.title || '新章节',
        content: data.content || '',
        sort_order: this.chapters.length,
        ...data,
      }
      const res = await chapterAPI.create(payload)
      this.chapters.push(res.data)
      return res.data
    },
    async deleteChapter(id) {
      await chapterAPI.delete(id)
      this.chapters = this.chapters.filter(c => c.id !== id)
      if (this.currentChapter?.id === id) {
        this.currentChapter = null
        this.content = ''
      }
    },
    async updateChapterTitle(id, title) {
      const res = await chapterAPI.update(id, { title })
      const idx = this.chapters.findIndex(c => c.id === id)
      if (idx !== -1) this.chapters[idx] = res.data
      if (this.currentChapter?.id === id) this.currentChapter = res.data
      return res.data
    },
    async reorderChapters(fromIndex, toIndex) {
      const chapter = this.chapters[fromIndex]
      if (!chapter) return
      this.chapters.splice(fromIndex, 1)
      this.chapters.splice(toIndex, 0, chapter)
      for (let i = Math.min(fromIndex, toIndex); i <= Math.max(fromIndex, toIndex); i++) {
        if (this.chapters[i]) {
          chapterAPI.update(this.chapters[i].id, { sort_order: i }).catch(() => {})
        }
      }
    },
  },
})

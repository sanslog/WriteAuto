import { defineStore } from 'pinia'
import { outlineAPI } from '../api/outline'
import { novelAPI } from '../api/novel'
import { useNovelStore } from './novel'

export const useOutlineStore = defineStore('outline', {
  state: () => ({
    plotNodes: [],
    cursor: 0,
    loading: false,
  }),
  actions: {
    async fetchOutline(novelId) {
      this.loading = true
      try {
        const res = await outlineAPI.list(novelId)
        this.plotNodes = res.data || []
      } finally {
        this.loading = false
      }
    },
    async createNode(data) {
      const res = await outlineAPI.create(data)
      this.plotNodes.push(res.data)
      return res.data
    },
    async updateNode(id, data) {
      const res = await outlineAPI.update(id, data)
      const idx = this.plotNodes.findIndex(n => n.id === id)
      if (idx !== -1) this.plotNodes[idx] = res.data
      return res.data
    },
    async deleteNode(id) {
      const res = await outlineAPI.delete(id)
      this.plotNodes = this.plotNodes.filter(n => n.id !== id)
      // 后端可能修正了游标，同步到 novel store
      if (res.cursor_position !== undefined) {
        const novelStore = useNovelStore()
        if (novelStore.currentNovel) {
          novelStore.currentNovel.cursor_position = res.cursor_position
        }
      }
    },
    async updateCursor(novelId, position) {
      this.cursor = position
      const res = await novelAPI.updateCursor(novelId, position)
      const novelStore = useNovelStore()
      novelStore.currentNovel = res.data
      return res.data
    },
    setCursor(index) {
      this.cursor = Math.max(0, Math.min(index, this.plotNodes.length - 1))
    },
    /**
     * Reorder nodes via drag & drop.
     * Updates local state immediately, fires async sort_order updates.
     */
    reorderNodes(fromIndex, toIndex) {
      const node = this.plotNodes[fromIndex]
      if (!node) return
      this.plotNodes.splice(fromIndex, 1)
      this.plotNodes.splice(toIndex, 0, node)
      for (let i = Math.min(fromIndex, toIndex); i <= Math.max(fromIndex, toIndex); i++) {
        if (this.plotNodes[i]) {
          outlineAPI.update(this.plotNodes[i].id, { sort_order: i }).catch(() => {})
        }
      }
    },
  },
})

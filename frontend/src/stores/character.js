import { defineStore } from 'pinia'
import { characterAPI } from '../api/character'

export const useCharacterStore = defineStore('character', {
  state: () => ({
    characters: [],
    characterStates: [],
    loading: false,
  }),
  actions: {
    async fetchCharacters(novelId) {
      this.loading = true
      try {
        const res = await characterAPI.list(novelId)
        this.characters = res.data || []
      } finally {
        this.loading = false
      }
    },
    async createCharacter(data) {
      const res = await characterAPI.create(data)
      this.characters.push(res.data)
      return res.data
    },
    async updateCharacter(id, data) {
      const res = await characterAPI.update(id, data)
      const idx = this.characters.findIndex(c => c.id === id)
      if (idx !== -1) this.characters[idx] = res.data
      return res.data
    },
    async deleteCharacter(id) {
      await characterAPI.delete(id)
      this.characters = this.characters.filter(c => c.id !== id)
    },
  },
})

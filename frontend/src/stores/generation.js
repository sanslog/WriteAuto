import { defineStore } from 'pinia'
import { generationAPI } from '../api/generation'

export const useGenerationStore = defineStore('generation', {
  state: () => ({
    sessions: {},
    activeGen: null,
    pollTimer: null,
    pollTimeoutMs: 300000, // 5 min max polling before giving up
    pollStartTime: null,
    status: null, // { step, state, error }
    loading: false,
    error: null,
  }),
  actions: {
    clearError() {
      this.error = null
    },
    async prepare(novelId) {
      this.loading = true
      this.clearError()
      try {
        const res = await generationAPI.prepare(novelId)
        if (res.success) {
          this.activeGen = res.data
        } else {
          this.error = res.error || '生成准备失败'
        }
        return res
      } catch (e) {
        this.error = e.message || '生成准备失败'
        return { success: false, error: this.error }
      } finally {
        this.loading = false
      }
    },
    async run(genId, data) {
      this.loading = true
      this.clearError()
      try {
        const res = await generationAPI.run(genId, data)
        if (res.success) {
          this.startPolling(genId)
        } else {
          this.error = res.error || '生成启动失败'
        }
        return res
      } catch (e) {
        this.error = e.message || '生成启动失败'
        return { success: false, error: this.error }
      } finally {
        this.loading = false
      }
    },
    async pollStatus(genId) {
      try {
        const res = await generationAPI.status(genId)
        if (res.success) {
          this.status = { step: res.step, state: res.state, error: res.error }
          if (res.step === 'complete' || res.step === 'failed') {
            this.stopPolling()
          }
        } else {
          this.error = res.error || '状态查询失败'
          this.stopPolling()
        }
        return res
      } catch (e) {
        this.error = e.message || '状态查询失败'
        this.stopPolling()
        return null
      }
    },
    async submitJudge(genId, data) {
      this.clearError()
      try {
        const res = await generationAPI.judge(genId, data)
        if (res.success) {
          this.pollStartTime = Date.now() // 用户提交判定后重新计时，给后续生成完整超时时间
          this.startPolling(genId)
        } else {
          this.error = res.error || '提交判定失败'
        }
        return res
      } catch (e) {
        this.error = e.message || '提交判定失败'
        return { success: false, error: this.error }
      }
    },
    async cancelGeneration(genId) {
      this.clearError()
      try {
        await generationAPI.cancel(genId)
      } catch (e) {
        // Silently ignore cancel errors
      } finally {
        this.stopPolling()
        this.status = { step: 'failed', state: {}, error: '用户取消生成' }
      }
    },
    startPolling(genId) {
      this.stopPolling()
      this.pollStartTime = Date.now()
      this.pollTimer = setInterval(() => {
        // 等待用户审核时不触发超时 — 用户可以无限时审阅
        if (this.status?.step === 'waiting_input') {
          this.pollStartTime = Date.now() // 重置计时，让后续生成有完整超时时间
          this.pollStatus(genId)
          return
        }
        // Frontend-side timeout: abort if generation takes too long
        if (this.pollStartTime && Date.now() - this.pollStartTime > this.pollTimeoutMs) {
          this.stopPolling()
          this.error = '生成超时，请重试'
          this.status = { step: 'failed', state: {}, error: '生成超时' }
          return
        }
        this.pollStatus(genId)
      }, 2000)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
      this.pollStartTime = null
    },
  },
})

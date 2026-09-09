import { defineStore } from 'pinia'
import { oneSentenceAPI } from '../api/oneSentence'
import { connectSSE } from '../api/sse'

export const useOneSentenceStore = defineStore('oneSentence', {
  state: () => ({
    generationId: '',
    status: 'idle',
    progress: null,
    result: null,
    timeline: [],
    loading: false,
    error: '',
    abortController: null,
  }),

  actions: {
    clearError() {
      this.error = ''
    },

    reset() {
      this.generationId = ''
      this.status = 'idle'
      this.progress = null
      this.result = null
      this.timeline = []
      this.error = ''
    },

    async run(payload) {
      if (this.loading) return
      this.reset()
      this.loading = true
      this.status = 'running'
      this.abortController = new AbortController()

      try {
        const terminal = await connectSSE(
          '/api/one-sentence/run',
          payload,
          this.abortController.signal,
          (event) => this.handleEvent(event),
        )
        if (terminal === 'cancelled') {
          this.status = 'cancelled'
          this.error = '任务已取消'
        } else if (this.status !== 'completed') {
          this.status = this.error ? 'failed' : 'completed'
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          this.status = 'cancelled'
          this.error = '任务已取消'
        } else {
          this.status = 'failed'
          this.error = error.message || '请求失败'
        }
      } finally {
        this.loading = false
        this.abortController = null
      }
    },

    async cancel() {
      if (this.abortController) {
        this.abortController.abort()
      }
      if (this.generationId) {
        try {
          await oneSentenceAPI.cancel(this.generationId)
        } catch {
          this.error = '取消请求失败'
        }
      }
      if (this.loading) {
        this.status = 'cancelled'
        this.loading = false
      }
    },

    handleEvent({ event, data }) {
      if (!data) return
      if (data.generation_id) {
        this.generationId = data.generation_id
      }

      if (event === 'progress') {
        this.status = data.run_status || this.status
        this.progress = data
        if (data.result) {
          this.result = data.result
        }
        if (data.error) {
          this.error = data.error
        }
        this.timeline.unshift({
          id: `${Date.now()}-${this.timeline.length}`,
          time: new Date().toLocaleTimeString(),
          message: data.message,
          status: data.run_status || '',
          iteration: data.iteration || 0,
        })
        return
      }

      if (event === 'complete') {
        this.status = data.status || 'completed'
        this.result = data.result || this.result
        this.error = ''
      } else if (event === 'error') {
        this.status = 'failed'
        this.error = data.error || '生成失败'
        this.result = data.result || this.result
      } else if (event === 'cancelled') {
        this.status = 'cancelled'
        this.error = '任务已取消'
      }
    },
  },
})

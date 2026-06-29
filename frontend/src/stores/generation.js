import { defineStore } from 'pinia'
import { generationAPI } from '../api/generation'
import { connectSSE } from '../api/sse'

export const useGenerationStore = defineStore('generation', {
  state: () => ({
    sessions: {},
    activeGen: null,
    /** AbortController for the active SSE connection */
    abortController: null,
    /** Current generation status — mirrors the latest SSE event */
    status: null, // { step, state: {...}, error, generatedText }
    loading: false,
    error: null,
  }),
  actions: {
    clearError() {
      this.error = null
    },

    // ── Prepare ──

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

    // ── SSE-based run ──

    async runSSE(genId, data) {
      this.loading = true
      this.clearError()
      this.abortController = new AbortController()

      this.status = { step: 'generating', state: {}, error: null, generatedText: '' }

      try {
        const terminal = await connectSSE(
          `/api/generations/${genId}/run`,
          data,
          this.abortController.signal,
          (evt) => this._handleSSEEvent(evt),
        )
        this._handleTerminalEvent(terminal)
      } catch (e) {
        if (e.name === 'AbortError') {
          this._setFailed('用户取消生成')
        } else {
          this.error = e.message || '生成请求失败'
          this._setFailed(this.error)
        }
      } finally {
        this.loading = false
        this.abortController = null
      }
    },

    /**
     * Submit judgment (approve / modify) via SSE streaming.
     * On approve → stream ends with complete.
     * On modify → LLM generates again, tokens stream, then judgment again.
     */
    async judgeSSE(genId, judgment) {
      this.loading = true
      this.clearError()
      this.abortController = new AbortController()

      this.status = { step: 'generating', state: {}, error: null, generatedText: '' }

      try {
        const terminal = await connectSSE(
          `/api/generations/${genId}/judge`,
          judgment,
          this.abortController.signal,
          (evt) => this._handleSSEEvent(evt),
        )
        this._handleTerminalEvent(terminal)
      } catch (e) {
        if (e.name === 'AbortError') {
          this._setFailed('用户取消生成')
        } else {
          this.error = e.message || '提交判定失败'
          this._setFailed(this.error)
        }
      } finally {
        this.loading = false
        this.abortController = null
      }
    },

    // ── Cancel ──

    async cancelGeneration(genId) {
      // Abort the SSE connection first so the backend gets a close signal
      if (this.abortController) {
        this.abortController.abort()
      }
      try {
        await generationAPI.cancel(genId)
      } catch (e) {
        // Silently ignore cancel errors
      }
      this._setFailed('用户取消生成')
    },

    // ── Internal helpers ──

    _setFailed(error) {
      this.status = {
        step: 'failed',
        state: {},
        error,
        generatedText: this.status?.generatedText || '',
      }
    },

    _handleSSEEvent(evt) {
      switch (evt.event) {
        case 'generation_start':
          this.status = { ...this.status, step: 'generating', generatedText: '' }
          break

        case 'token':
          this.status = {
            ...this.status,
            step: 'generating',
            generatedText: (this.status?.generatedText || '') + (evt.data?.text || ''),
          }
          break

        case 'judgment':
          this.status = {
            step: 'waiting_input',
            state: evt.data || {},
            error: null,
            generatedText: (evt.data?.generated_text || this.status?.generatedText || ''),
          }
          break

        case 'error':
          this.error = evt.data?.error || '生成出错'
          this.status = { step: 'failed', state: {}, error: this.error, generatedText: '' }
          break
      }
    },

    _handleTerminalEvent(eventType) {
      // Don't overwrite waiting_input — judgment panel is active
      if (this.status?.step === 'waiting_input') return
      // Don't overwrite failed
      if (this.status?.step === 'failed') return

      switch (eventType) {
        case 'complete':
          this.status = { step: 'complete', state: {}, error: null, generatedText: this.status?.generatedText || '' }
          break
        case 'cancelled':
          this._setFailed('用户取消生成')
          break
        case 'error':
          this.error = this.status?.error || '生成出错'
          this.status = { step: 'failed', state: {}, error: this.error, generatedText: '' }
          break
      }
    },
  },
})

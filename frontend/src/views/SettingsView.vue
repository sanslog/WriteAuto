<script setup>
import {
  AlertTriangle,
  CheckCircle,
  Cpu,
  Eye,
  EyeOff,
  Key,
  Link,
  LoaderCircle,
  Save,
  Settings,
  Trash2,
  Wifi,
  XCircle
} from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import client from '../api/client'
import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()
const showApiKey = ref(false)
const isSaving = ref(false)
const isPinging = ref(false)
const pingStatus = ref(null) // null | 'success' | 'error'

// 弹窗相关
const showErrorModal = ref(false)
const errorDetails = ref({
  url: '',
  method: 'POST',
  status: '',
  statusText: '',
  requestBody: '',
  responseBody: '',
  errorMessage: ''
})

const form = ref({
  llm_api_key: '',
  llm_base_url: 'https://api.deepseek.com',
  llm_model: 'deepseek-chat', // 修正：使用正确的模型名称
})

onMounted(async () => {
  await settingsStore.fetchSettings()
  if (settingsStore.settings) {
    form.value = {
      llm_api_key: settingsStore.settings.llm_api_key || '',
      llm_base_url: settingsStore.settings.llm_base_url || 'https://api.deepseek.com',
      llm_model: settingsStore.settings.llm_model || 'deepseek-chat',
    }
  }
})

async function save() {
  isSaving.value = true
  try {
    await Promise.all([
      settingsStore.updateSettings(form.value),
      new Promise(r => setTimeout(r, 1000))
    ])
  } finally {
    isSaving.value = false
  }
}

// 复制到剪贴板的辅助函数
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    // 可以添加一个简单的提示
  } catch (err) {
    console.error('复制失败:', err)
  }
}

async function pingLLM() {
  pingStatus.value = null
  isPinging.value = true
  showErrorModal.value = false

  // 验证必填字段
  if (!form.value.llm_api_key || !form.value.llm_base_url || !form.value.llm_model) {
    pingStatus.value = 'error'
    isPinging.value = false
    errorDetails.value = {
      ...errorDetails.value,
      errorMessage: '请先填写 API Key、Base URL 和 Model'
    }
    showErrorModal.value = true
    return
  }

  try {
    // 发送 ping 请求
    const response = await client.post('/pingOpenAI', {
      api_key: form.value.llm_api_key,
      baseurl: form.value.llm_base_url,
      model_name: form.value.llm_model
    })

    // 检查响应状态
    if (response.status === 200 && response.data) {
      // 成功
      pingStatus.value = 'success'

      // 可选：显示成功提示
      // 你可以在这里添加一个成功消息的 toast 或提示
      console.log('Ping 成功:', response.data)

      // 如果有返回消息，可以记录
      if (response.data.message) {
        // 可以显示成功信息
        console.log('连接成功:', response.data.message)
      }
    } else {
      // 状态码不是 200
      pingStatus.value = 'error'

      // 构建错误详情
      errorDetails.value = {
        url: '/pingOpenAI',
        method: 'POST',
        status: response.status || '未知',
        statusText: response.statusText || '请求失败',
        requestBody: JSON.stringify({
          api_key: '===已隐藏===',
          baseurl: form.value.llm_base_url,
          model_name: form.value.llm_model
        }, null, 2),
        responseBody: JSON.stringify(response.data || {}, null, 2),
        errorMessage: response.data?.message || response.data?.error || `请求失败 (HTTP ${response.status})`
      }
      showErrorModal.value = true
    }
  } catch (error) {
    // 网络错误或其他异常
    pingStatus.value = 'error'

    // 构建错误详情
    errorDetails.value = {
      url: '/pingOpenAI',
      method: 'POST',
      status: error.response?.status || '网络错误',
      statusText: error.response?.statusText || error.message || '未知错误',
      requestBody: JSON.stringify({
        api_key: '===已隐藏===',
        baseurl: form.value.llm_base_url,
        model_name: form.value.llm_model
      }, null, 2),
      responseBody: error.response?.data ? JSON.stringify(error.response.data, null, 2) : error.message || '无响应数据',
      errorMessage: error.response?.data?.message ||
        error.response?.data?.error ||
        error.message ||
        '网络请求失败，请检查网络连接'
    }
    showErrorModal.value = true

    console.error('Ping 失败:', error)
  } finally {
    isPinging.value = false
  }
}

function closeErrorModal() {
  showErrorModal.value = false
}

async function clearData() {
  if (confirm('确定要清除所有本地数据吗？此操作不可撤销。')) {
    await settingsStore.updateSettings({ clear_data: '1' })
  }
}
</script>

<template>
  <!-- 模板部分保持不变 -->
  <div class="settings-view">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <Settings class="header-icon" :size="28" />
        <div>
          <h1>应用设置</h1>
          <p class="header-description">管理您的 LLM 配置和应用数据</p>
        </div>
      </div>
    </div>

    <!-- LLM 配置卡片 -->
    <div class="settings-card">
      <div class="card-header">
        <div class="card-header-left">
          <Cpu class="card-icon" :size="20" />
          <h2>LLM 配置</h2>
        </div>
      </div>

      <form @submit.prevent="save" class="settings-form">
        <!-- API Key 输入框 -->
        <div class="form-group">
          <label class="form-label">
            <Key :size="16" class="label-icon" />
            API Key
          </label>
          <div class="input-wrapper">
            <input v-model="form.llm_api_key" :type="showApiKey ? 'text' : 'password'" placeholder="请输入您的 API Key"
              class="form-input" />
            <button type="button" class="input-action-btn" @click="showApiKey = !showApiKey">
              <EyeOff v-if="showApiKey" :size="18" />
              <Eye v-else :size="18" />
            </button>
          </div>
          <p class="form-hint">您的 API Key 将安全存储在本地</p>
        </div>

        <!-- Base URL 输入框 -->
        <div class="form-group">
          <label class="form-label">
            <Link :size="16" class="label-icon" />
            Base URL
          </label>
          <input v-model="form.llm_base_url" type="url" placeholder="https://api.deepseek.com" class="form-input" />
        </div>

        <!-- Model 输入框 -->
        <div class="form-group">
          <label class="form-label">
            <Cpu :size="16" class="label-icon" />
            Model
          </label>
          <input v-model="form.llm_model" placeholder="deepseek-chat" class="form-input" />
        </div>

        <!-- 按钮区域 -->
        <div class="form-footer">
          <div class="form-actions">
            <button type="button" class="ping-btn" :class="{
              'ping-idle': pingStatus === null,
              'ping-loading': isPinging,
              'ping-success': pingStatus === 'success',
              'ping-error': pingStatus === 'error'
            }" @click="pingLLM" :disabled="isPinging || isSaving">
              <Wifi v-if="pingStatus === null && !isPinging" :size="16" />
              <LoaderCircle v-if="isPinging" :size="16" class="spin" />
              <CheckCircle v-if="pingStatus === 'success'" :size="16" />
              <XCircle v-if="pingStatus === 'error'" :size="16" />
              <span>{{ isPinging ? '测试中' : '测试连接' }}</span>
            </button>
            <button type="submit" class="save-btn" :disabled="isSaving || isPinging">
              <Save :size="18" v-if="!isSaving" />
              <LoaderCircle v-if="isSaving" :size="18" class="spin" />
              <span>{{ isSaving ? '保存中' : '保存设置' }}</span>
            </button>
          </div>
        </div>
      </form>
    </div>

    <!-- 数据管理卡片 -->
    <div class="settings-card danger-card">
      <div class="card-header">
        <div class="card-header-left">
          <Trash2 class="card-icon danger-icon" :size="20" />
          <h2>数据管理</h2>
        </div>
      </div>

      <div class="danger-content">
        <div class="warning-box">
          <AlertTriangle :size="20" class="warning-icon" />
          <div>
            <p class="warning-title">危险操作区域</p>
            <p class="warning-text">清除所有本地存储的小说数据，此操作不可撤销，请谨慎操作</p>
          </div>
        </div>

        <button class="danger-btn" @click="clearData">
          <Trash2 :size="18" />
          清除所有数据
        </button>
      </div>
    </div>

    <!-- 错误弹窗 Modal -->
    <div v-if="showErrorModal" class="modal-overlay" @click.self="closeErrorModal">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-header-left">
            <XCircle class="modal-error-icon" :size="24" />
            <h3>连接失败</h3>
          </div>
          <button class="modal-close" @click="closeErrorModal">×</button>
        </div>

        <div class="modal-body">
          <!-- 错误信息 -->
          <div class="error-message-box">
            <AlertTriangle :size="16" class="error-message-icon" />
            <span class="error-message-text">{{ errorDetails.errorMessage || '请求失败' }}</span>
          </div>

          <!-- 请求详情 -->
          <div class="detail-section">
            <div class="detail-row">
              <span class="detail-label">请求方法</span>
              <span class="detail-value method-tag">POST</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">请求 URL</span>
              <span class="detail-value url-value">{{ errorDetails.url }}</span>
            </div>
            <div v-if="errorDetails.status" class="detail-row">
              <span class="detail-label">响应状态</span>
              <span class="detail-value" :class="{
                'status-ok': errorDetails.status < 400,
                'status-error': errorDetails.status >= 400
              }">
                {{ errorDetails.status }} {{ errorDetails.statusText }}
              </span>
            </div>
          </div>

          <!-- 请求体 -->
          <div class="detail-section">
            <div class="section-header">
              <span class="section-title">请求体 (Request Body)</span>
              <button class="copy-btn" @click="copyToClipboard(errorDetails.requestBody)">复制</button>
            </div>
            <pre class="code-block">{{ errorDetails.requestBody || '无' }}</pre>
          </div>

          <!-- 响应体 -->
          <div class="detail-section" v-if="errorDetails.responseBody">
            <div class="section-header">
              <span class="section-title">响应体 (Response Body)</span>
              <button class="copy-btn" @click="copyToClipboard(errorDetails.responseBody)">复制</button>
            </div>
            <pre class="code-block error-response">{{ errorDetails.responseBody || '无' }}</pre>
          </div>
        </div>

        <div class="modal-footer">
          <button class="modal-close-btn" @click="closeErrorModal">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 20px;
  overflow-y: auto;

  scrollbar-width: none;
  /* Firefox */
  -ms-overflow-style: none;
  /* IE/Edge */
}

/* 页面头部 */
.page-header {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  color: var(--primary-color, #6366f1);
  background: var(--primary-light, #eef2ff);
  padding: 12px;
  border-radius: 12px;
}

.header-content h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin: 0;
  line-height: 1.3;
}

.header-description {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 4px 0 0;
}

/* 设置卡片 */
.settings-card {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.settings-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.danger-card {
  border-color: #fecaca;
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-icon {
  color: var(--primary-color, #6366f1);
}

.danger-icon {
  color: #ef4444;
}

.card-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin: 0;
}

.badge {
  background: var(--primary-light, #eef2ff);
  color: var(--primary-color, #6366f1);
  font-size: 12px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 20px;
}

/* 表单样式 */
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #374151);
  margin-bottom: 8px;
}

.label-icon {
  color: var(--text-secondary, #6b7280);
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 10px;
  font-size: 14px;
  color: var(--text-primary, #1f2937);
  background: var(--bg-input, #f9fafb);
  transition: all 0.2s ease;
  outline: none;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--primary-color, #6366f1);
  background: var(--bg-card, #ffffff);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.form-input::placeholder {
  color: var(--text-tertiary, #9ca3af);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper .form-input {
  padding-right: 48px;
}

.input-action-btn {
  position: absolute;
  right: 8px;
  background: transparent;
  border: none;
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.input-action-btn:hover {
  color: var(--text-primary, #374151);
  background: var(--bg-hover, #f3f4f6);
}

.form-hint {
  font-size: 12px;
  color: var(--text-secondary, #9ca3af);
  margin-top: 6px;
}

/* 表单底部 */
.form-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color, #f3f4f6);
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  align-items: center;
}

/* 测试按钮 - 基础样式 */
.ping-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 90px;
  justify-content: center;
}

/* 测试按钮 - 空闲状态 (蓝色) */
.ping-idle {
  background: #3b82f6;
  color: white;
}

.ping-idle:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* 测试按钮 - 加载状态 */
.ping-loading {
  background: #3b82f6;
  color: white;
  cursor: not-allowed;
  opacity: 0.8;
}

/* 测试按钮 - 成功状态 (绿色) */
.ping-success {
  background: #22c55e;
  color: white;
}

.ping-success:hover:not(:disabled) {
  background: #16a34a;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
}

/* 测试按钮 - 错误状态 (红色) */
.ping-error {
  background: #ef4444;
  color: white;
}

.ping-error:hover:not(:disabled) {
  background: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.ping-btn:disabled {
  cursor: not-allowed;
}

/* 保存按钮 */
.save-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--primary-color, #6366f1);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.save-btn:hover:not(:disabled) {
  background: var(--primary-hover, #4f46e5);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 旋转动画 */
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

/* 危险区域 */
.danger-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.warning-box {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
}

.warning-icon {
  color: #ef4444;
  flex-shrink: 0;
  margin-top: 2px;
}

.warning-title {
  font-size: 14px;
  font-weight: 600;
  color: #991b1b;
  margin: 0 0 4px;
}

.warning-text {
  font-size: 13px;
  color: #b91c1c;
  margin: 0;
  line-height: 1.5;
}

.danger-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.danger-btn:hover {
  background: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* ===== Modal 样式 ===== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

.modal-content {
  background: var(--bg-card, #ffffff);
  border-radius: 16px;
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }

  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  flex-shrink: 0;
}

.modal-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-error-icon {
  color: #ef4444;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin: 0;
}

.modal-close {
  background: transparent;
  border: none;
  font-size: 28px;
  line-height: 1;
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.2s;
}

.modal-close:hover {
  color: var(--text-primary, #1f2937);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.error-message-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  margin-bottom: 20px;
}

.error-message-icon {
  color: #ef4444;
  flex-shrink: 0;
  margin-top: 2px;
}

.error-message-text {
  font-size: 14px;
  color: #991b1b;
  font-weight: 500;
  word-break: break-all;
}

.detail-section {
  margin-bottom: 18px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-row {
  display: flex;
  align-items: baseline;
  padding: 6px 0;
  gap: 12px;
  font-size: 14px;
}

.detail-label {
  color: var(--text-secondary, #6b7280);
  font-weight: 500;
  min-width: 80px;
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-primary, #1f2937);
  word-break: break-all;
}

.url-value {
  font-family: monospace;
  font-size: 13px;
  background: var(--bg-input, #f3f4f6);
  padding: 2px 8px;
  border-radius: 4px;
}

.method-tag {
  background: #3b82f6;
  color: white;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.status-ok {
  color: #22c55e;
  font-weight: 600;
}

.status-error {
  color: #ef4444;
  font-weight: 600;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
}

.copy-btn {
  background: transparent;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  padding: 2px 12px;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: var(--bg-hover, #f3f4f6);
  border-color: var(--primary-color, #6366f1);
  color: var(--primary-color, #6366f1);
}

.code-block {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 14px 16px;
  border-radius: 10px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.error-response {
  border-left: 3px solid #ef4444;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color, #e5e7eb);
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

.modal-close-btn {
  padding: 8px 24px;
  background: var(--primary-color, #6366f1);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.modal-close-btn:hover {
  background: var(--primary-hover, #4f46e5);
}

/* 暗色模式适配 */
@media (prefers-color-scheme: dark) {
  .settings-card {
    background: #1e1e2e;
    border-color: #313244;
  }

  .danger-card {
    border-color: #7f1d1d;
  }

  .form-input {
    background: #181825;
    border-color: #45475a;
    color: #cdd6f4;
  }

  .form-input:focus {
    border-color: #89b4fa;
    background: #1e1e2e;
  }

  .warning-box {
    background: #3b1c1c;
    border-color: #7f1d1d;
  }

  .warning-title {
    color: #fca5a5;
  }

  .warning-text {
    color: #f87171;
  }

  .modal-content {
    background: #1e1e2e;
    border-color: #313244;
  }

  .modal-header {
    border-color: #313244;
  }

  .modal-header h3 {
    color: #cdd6f4;
  }

  .modal-close {
    color: #a6adc8;
  }

  .modal-close:hover {
    color: #cdd6f4;
  }

  .error-message-box {
    background: #3b1c1c;
    border-color: #7f1d1d;
  }

  .error-message-text {
    color: #fca5a5;
  }

  .detail-label {
    color: #a6adc8;
  }

  .detail-value {
    color: #cdd6f4;
  }

  .url-value {
    background: #181825;
  }

  .section-title {
    color: #a6adc8;
  }

  .copy-btn {
    border-color: #45475a;
    color: #a6adc8;
  }

  .copy-btn:hover {
    background: #313244;
    border-color: #89b4fa;
    color: #89b4fa;
  }

  .code-block {
    background: #11111b;
    color: #cdd6f4;
  }

  .modal-footer {
    border-color: #313244;
  }
}

/* 复制提示 */
.copy-btn.copied {
  border-color: #22c55e;
  color: #22c55e;
}
</style>
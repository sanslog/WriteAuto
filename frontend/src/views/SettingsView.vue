<script setup>
import {
  AlertTriangle,
  Cpu,
  Eye,
  EyeOff,
  Key,
  Link,
  Save,
  Settings,
  Trash2
} from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()
const showApiKey = ref(false)
const isSaving = ref(false)

const form = ref({
  llm_api_key: '',
  llm_base_url: 'https://api.deepseek.com',
  llm_model: 'deepseek-v4-flash',
})

onMounted(async () => {
  await settingsStore.fetchSettings()
  if (settingsStore.settings) {
    form.value = {
      llm_api_key: settingsStore.settings.llm_api_key || '',
      llm_base_url: settingsStore.settings.llm_base_url || 'https://api.deepseek.com',
      llm_model: settingsStore.settings.llm_model || 'deepseek-v4-flash',
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

async function clearData() {
  if (confirm('确定要清除所有本地数据吗？此操作不可撤销。')) {
    await settingsStore.updateSettings({ clear_data: '1' })
  }
}
</script>

<template>
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
          <input v-model="form.llm_base_url" type="url" placeholder="https://api.deepseek.com/v1" class="form-input" />
        </div>

        <!-- Model 输入框 -->
        <div class="form-group">
          <label class="form-label">
            <Cpu :size="16" class="label-icon" />
            Model
          </label>
          <input v-model="form.llm_model" placeholder="deepseek-chat" class="form-input" />
        </div>

        <!-- 保存按钮 -->
        <div class="form-footer">
          <button type="submit" class="save-btn" :disabled="isSaving">
            <Save :size="18" v-if="!isSaving" />
            <span>{{ isSaving ? '保存中...' : '保存设置' }}</span>
          </button>
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
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 20px;
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
  justify-content: flex-end;
  padding-top: 8px;
  border-top: 1px solid var(--border-color, #f3f4f6);
}

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
}
</style>
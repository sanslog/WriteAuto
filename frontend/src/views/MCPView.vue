<script setup>
import {
  Box,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  LoaderCircle,
  Plus,
  RefreshCw,
  Server,
  Trash2,
  Wrench,
  XCircle,
} from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { useMCPStore } from "../stores/mcp"

const mcpStore = useMCPStore()

const showForm = ref(false)
const formMode = ref("create")
const formData = ref(createEmptyForm())
const saving = ref(false)
const formError = ref("")
const discoveringId = ref(null)
const expandedId = ref(null)
const hasServices = computed(() => mcpStore.services.length > 0)

function createEmptyForm() {
  return { name: "", description: "", enabled: true, url: "" }
}

onMounted(() => mcpStore.fetchServices())

function openCreate() {
  formMode.value = "create"
  formData.value = createEmptyForm()
  formError.value = ""
  showForm.value = true
}

function openEdit(svc) {
  formMode.value = "edit"
  formData.value = {
    name: svc.name || "",
    description: svc.description || "",
    enabled: svc.enabled !== false,
    url: svc.server?.url || "",
  }
  formError.value = ""
  showForm.value = true
  formData.value._editId = svc.id
}

function closeForm() {
  showForm.value = false
  formError.value = ""
}

async function handleSubmit() {
  const fd = formData.value
  if (!fd.name.trim()) { formError.value = "服务名称不能为空"; return }
  if (!fd.url.trim()) { formError.value = "服务地址不能为空"; return }

  const body = {
    name: fd.name.trim(),
    description: fd.description.trim(),
    enabled: fd.enabled,
    server: { url: fd.url.trim() },
  }

  saving.value = true
  formError.value = ""
  try {
    if (formMode.value === "create") {
      const res = await mcpStore.createService(body)
      if (!res.success) formError.value = res.error || "创建失败"
    } else {
      const res = await mcpStore.updateService(fd._editId, body)
      if (!res.success) formError.value = res.error || "更新失败"
    }
    if (!formError.value) closeForm()
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}

async function handleDelete(id, name) {
  if (!confirm(`确定要删除 MCP 服务「${name}」吗？`)) return
  await mcpStore.deleteService(id)
}

async function handleDiscover(id) {
  discoveringId.value = id
  try {
    const res = await mcpStore.discoverTools(id)
    if (res.success) {
      const svc = mcpStore.services.find((s) => s.id === id)
      if (svc) svc.tools = res.tools || []
    } else {
      alert("发现工具失败: " + (res.error || "未知错误"))
    }
  } catch (e) {
    alert("发现工具失败: " + e.message)
  } finally {
    discoveringId.value = null
  }
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}
</script>

<template>
  <div class="mcp-view">
    <div class="page-header">
      <div class="header-left">
        <Server :size="24" class="header-icon" />
        <div>
          <h1>MCP 服务</h1>
          <p class="header-subtitle">管理 MCP (Model Context Protocol) 服务 — 填写 SSE 端点 URL 即可接入</p>
        </div>
      </div>
      <button class="btn-primary" @click="openCreate"><Plus :size="16" /> 添加服务</button>
    </div>

    <div v-if="mcpStore.error" class="error-banner">
      {{ mcpStore.error }}
      <button class="btn-icon" @click="mcpStore.error = null"><XCircle :size="16" /></button>
    </div>

    <div v-if="mcpStore.loading" class="loading-state">
      <LoaderCircle :size="32" class="spin" />
      <p>加载中...</p>
    </div>

    <div v-else-if="!hasServices" class="empty-state">
      <Server :size="48" class="empty-icon" />
      <h2>暂无 MCP 服务</h2>
      <p>添加 MCP 服务来扩展 AI 生成能力，只需要一个 URL</p>
      <button class="btn-primary" @click="openCreate"><Plus :size="16" /> 添加第一个服务</button>
    </div>

    <div v-else class="service-list">
      <div v-for="svc in mcpStore.services" :key="svc.id" class="service-card">
        <div class="card-header" @click="toggleExpand(svc.id)">
          <div class="card-info">
            <Box :size="20" class="card-icon" />
            <div>
              <div class="card-name">
                {{ svc.name }}
                <span class="status-dot" :class="svc.enabled !== false ? 'on' : 'off'" />
              </div>
              <div class="card-desc">{{ svc.description || svc.server?.url || "暂无描述" }}</div>
            </div>
          </div>
          <div class="card-actions">
            <span class="tool-badge">{{ svc.tools?.length || 0 }} 工具</span>
            <button class="btn-icon" title="发现工具" :disabled="discoveringId === svc.id" @click.stop="handleDiscover(svc.id)">
              <RefreshCw :size="16" :class="{ spin: discoveringId === svc.id }" />
            </button>
            <button class="btn-icon" title="编辑" @click.stop="openEdit(svc)"><Wrench :size="16" /></button>
            <button class="btn-icon btn-icon-danger" title="删除" @click.stop="handleDelete(svc.id, svc.name)"><Trash2 :size="16" /></button>
            <ChevronDown v-if="expandedId === svc.id" :size="18" class="chevron" />
            <ChevronRight v-else :size="18" class="chevron" />
          </div>
        </div>

        <div v-if="expandedId === svc.id" class="card-body">
          <div class="body-section">
            <h4>服务器</h4>
            <div class="info-row">
              <span class="label">URL</span>
              <code>{{ svc.server?.url }}</code>
            </div>
          </div>

          <div class="body-section">
            <h4>工具列表</h4>
            <div v-if="svc.tools?.length" class="tool-list">
              <div v-for="tool in svc.tools" :key="tool.name" class="tool-item">
                <div class="tool-name">{{ tool.name }}</div>
                <div class="tool-desc">{{ tool.description || "无描述" }}</div>
                <div v-if="tool.input_schema?.properties" class="tool-params">
                  <span v-for="(info, pname) in tool.input_schema.properties" :key="pname" class="param-tag">
                    {{ pname }}: {{ info.type || "any" }}
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="text-muted">
              尚未发现工具
              <button class="btn-sm btn-ghost" @click="handleDiscover(svc.id)"><RefreshCw :size="12" /> 发现</button>
            </p>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showForm" class="overlay" @click.self="closeForm">
        <div class="dialog">
          <div class="dialog-header">
            <h3>{{ formMode === "create" ? "添加 MCP 服务" : "编辑 MCP 服务" }}</h3>
            <button class="btn-icon" @click="closeForm"><XCircle :size="20" /></button>
          </div>

          <div class="dialog-body">
            <div v-if="formError" class="form-error">{{ formError }}</div>

            <div class="field">
              <label>服务名称 <span class="required">*</span></label>
              <input v-model="formData.name" class="input" placeholder="例如: 联网搜索" />
            </div>

            <div class="field">
              <label>描述</label>
              <textarea v-model="formData.description" class="input textarea" placeholder="服务功能描述" rows="2" />
            </div>

            <div class="field">
              <label class="checkbox-line">
                <input type="checkbox" v-model="formData.enabled" />
                启用此服务
              </label>
            </div>

            <h4 class="section-title">连接</h4>

            <div class="field">
              <label>SSE 端点 URL <span class="required">*</span></label>
              <input v-model="formData.url" class="input" placeholder="https://example.com/mcp" />
              <p class="field-hint">MCP 服务器的 SSE 端点地址，例如 https://api.example.com/mcp</p>
            </div>
          </div>

          <div class="dialog-footer">
            <button class="btn-ghost" @click="closeForm">取消</button>
            <button class="btn-primary" :disabled="saving" @click="handleSubmit">
              <LoaderCircle v-if="saving" :size="14" class="spin" />
              {{ formMode === "create" ? "添加" : "保存" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.mcp-view { padding: var(--space-xl) var(--space-lg); overflow-y: auto; height: 100%; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-lg); flex-wrap: wrap; gap: var(--space-md); }
.header-left { display: flex; align-items: center; gap: var(--space-md); }
.header-icon { color: var(--primary); flex-shrink: 0; }
.page-header h1 { font-size: 24px; font-weight: 700; margin: 0; }
.header-subtitle { font-size: 13px; color: var(--text-muted); margin: 0; }

.error-banner { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-radius: var(--radius); background: var(--danger-light); color: var(--danger); margin-bottom: var(--space-md); font-size: 14px; }
.loading-state { display: flex; flex-direction: column; align-items: center; gap: var(--space-md); padding: var(--space-2xl); color: var(--text-secondary); }
.spin { animation: spin 1s linear infinite; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: var(--space-md); padding: var(--space-2xl); color: var(--text-secondary); text-align: center; }
.empty-icon { color: var(--text-muted); opacity: 0.4; }
.empty-state h2 { font-size: 20px; font-weight: 600; color: var(--text); }

.service-list { display: flex; flex-direction: column; gap: var(--space-sm); }
.service-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; transition: border-color var(--transition-fast) var(--ease); }
.service-card:hover { border-color: var(--primary); }
.card-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; cursor: pointer; gap: var(--space-md); }
.card-info { display: flex; align-items: center; gap: 12px; min-width: 0; }
.card-icon { color: var(--primary); flex-shrink: 0; }
.card-name { font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.status-dot.on { background: var(--success); }
.status-dot.off { background: var(--text-muted); }
.card-desc { font-size: 13px; color: var(--text-secondary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px; }
.card-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.tool-badge { font-size: 12px; color: var(--text-muted); background: var(--bg-tertiary); padding: 2px 8px; border-radius: var(--radius-full); margin-right: 4px; }
.chevron { color: var(--text-muted); }

.card-body { padding: 0 16px 16px; border-top: 1px solid var(--border); padding-top: 14px; }
.body-section { margin-bottom: 14px; }
.body-section:last-child { margin-bottom: 0; }
.body-section h4 { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.info-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 14px; }
.info-row .label { color: var(--text-secondary); font-weight: 500; min-width: 36px; }
.info-row code { background: var(--bg-tertiary); padding: 2px 8px; border-radius: var(--radius-sm); font-size: 13px; word-break: break-all; }

.tool-list { display: flex; flex-direction: column; gap: 6px; }
.tool-item { padding: 10px 12px; background: var(--bg-tertiary); border-radius: var(--radius); }
.tool-name { font-weight: 600; font-size: 14px; font-family: monospace; }
.tool-desc { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
.tool-params { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.param-tag { font-size: 11px; background: var(--primary-light); color: var(--primary); padding: 1px 8px; border-radius: var(--radius-full); }
.text-muted { color: var(--text-muted); font-size: 13px; }

.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: var(--z-modal); }
.dialog { background: var(--bg); border-radius: var(--radius-lg); width: 92%; max-width: 500px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: var(--shadow-xl); }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.dialog-header h3 { margin: 0; font-size: 17px; font-weight: 600; }
.dialog-body { padding: 20px; overflow-y: auto; flex: 1; }
.dialog-footer { display: flex; align-items: center; justify-content: flex-end; gap: var(--space-sm); padding: 14px 20px; border-top: 1px solid var(--border); }

.form-error { padding: 8px 12px; border-radius: var(--radius); background: var(--danger-light); color: var(--danger); font-size: 13px; margin-bottom: 14px; }
.field { margin-bottom: 16px; }
.field label { display: block; font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px; }
.required { color: var(--danger); }
.field-hint { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.input { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); color: var(--text); font-size: 14px; font-family: inherit; transition: border-color var(--transition-fast) var(--ease); }
.input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 2px var(--primary-light); }
.textarea { resize: vertical; min-height: 56px; }

.section-title { font-size: 14px; font-weight: 600; color: var(--text); margin: 18px 0 12px; padding-top: 14px; border-top: 1px solid var(--border); }
.checkbox-line { display: flex !important; align-items: center; gap: 8px; cursor: pointer; }
.checkbox-line input { width: 16px; height: 16px; }

.btn-icon-danger { color: var(--text-muted); }
.btn-icon-danger:hover { color: var(--danger) !important; background: var(--danger-light) !important; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-ghost { background: transparent; color: var(--text-secondary); border: 1px solid var(--border); }
.btn-ghost:hover { background: var(--bg-secondary); color: var(--text); }
</style>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useForeshadowStore } from '../stores/foreshadow'
import { Plus, Pencil, Trash2, Sparkles, Search, Filter } from 'lucide-vue-next'
import Modal from '../components/common/Modal.vue'

const route = useRoute()
const novelId = route.params.id
const foreshadowStore = useForeshadowStore()

const showDialog = ref(false)
const editingForeshadow = ref(null)
const showDeleteDialog = ref(false)
const deletingForeshadowId = ref(null)
const form = ref({ title: '', description: '', status: 'unused' })
const searchQuery = ref('')
const statusFilter = ref('all')

const filteredForeshadows = computed(() => {
  let items = foreshadowStore.foreshadows
  if (statusFilter.value !== 'all') {
    items = items.filter(f => f.status === statusFilter.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(f =>
      (f.title || '').toLowerCase().includes(q) ||
      (f.description || '').toLowerCase().includes(q)
    )
  }
  return items
})

onMounted(() => {
  foreshadowStore.fetchForeshadows(novelId)
})

function openCreate() {
  editingForeshadow.value = null
  form.value = { title: '', description: '', status: 'unused' }
  showDialog.value = true
}

function openEdit(f) {
  editingForeshadow.value = f
  form.value = {
    title: f.title || '',
    description: f.description || '',
    status: f.status || 'unused',
  }
  showDialog.value = true
}

async function submit() {
  const payload = { novel_id: novelId, ...form.value }
  if (editingForeshadow.value) {
    await foreshadowStore.updateForeshadow(editingForeshadow.value.id, payload)
  } else {
    await foreshadowStore.createForeshadow(payload)
  }
  showDialog.value = false
}

function confirmDelete(id) {
  deletingForeshadowId.value = id
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (deletingForeshadowId.value) {
    await foreshadowStore.deleteForeshadow(deletingForeshadowId.value)
    deletingForeshadowId.value = null
    showDeleteDialog.value = false
  }
}

function statusBadgeClass(status) {
  switch (status) {
    case 'used': return 'badge-success'
    case 'unused': return 'badge-warning'
    default: return 'badge-info'
  }
}

function statusLabel(status) {
  switch (status) {
    case 'used': return '已使用'
    case 'unused': return '未使用'
    default: return status
  }
}
</script>

<template>
  <div class="foreshadows-view">
    <!-- Header -->
    <div class="view-header">
      <div class="search-filter">
        <div class="search-box">
          <Search :size="14" class="search-icon" />
          <input v-model="searchQuery" placeholder="搜索伏笔..." class="search-input" />
        </div>
        <div class="filter-group">
          <Filter :size="14" />
          <button
            :class="['filter-btn', { active: statusFilter === 'all' }]"
            @click="statusFilter = 'all'"
          >全部</button>
          <button
            :class="['filter-btn', { active: statusFilter === 'unused' }]"
            @click="statusFilter = 'unused'"
          >未使用</button>
          <button
            :class="['filter-btn', { active: statusFilter === 'used' }]"
            @click="statusFilter = 'used'"
          >已使用</button>
        </div>
      </div>
      <button class="btn-primary" @click="openCreate">
        <Sparkles :size="16" /> 添加伏笔
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="foreshadowStore.foreshadows.length === 0" class="empty-state">
      <Sparkles :size="48" class="empty-state-icon" />
      <p>暂无伏笔，点击「添加伏笔」开始埋下伏笔</p>
    </div>

    <div v-else-if="filteredForeshadows.length === 0" class="empty-state">
      <p>没有找到匹配的伏笔</p>
    </div>

    <!-- Foreshadow list -->
    <div v-else class="foreshadow-list">
      <div
        v-for="(f, i) in filteredForeshadows"
        :key="f.id"
        class="foreshadow-card card card-hover"
        :style="{ animationDelay: (i * 0.05) + 's' }"
      >
        <div class="foreshadow-header">
          <div class="foreshadow-title-wrap">
            <Sparkles :size="16" class="title-icon" />
            <h3>{{ f.title || '未命名伏笔' }}</h3>
          </div>
          <span :class="['badge', statusBadgeClass(f.status)]">
            {{ statusLabel(f.status) }}
          </span>
        </div>
        <p class="foreshadow-desc">{{ f.description || '暂无描述' }}</p>
        <div class="foreshadow-actions">
          <button class="btn-icon" @click="openEdit(f)" title="编辑">
            <Pencil :size="14" />
          </button>
          <button class="btn-icon danger" @click="confirmDelete(f.id)" title="删除">
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Modal
      :show="showDialog"
      :title="editingForeshadow ? '编辑伏笔' : '添加伏笔'"
      @close="showDialog = false"
    >
      <form @submit.prevent="submit" class="foreshadow-form">
        <label class="form-group">
          <span class="form-label-text">标题</span>
          <input v-model="form.title" placeholder="伏笔标题" required />
        </label>
        <label class="form-group">
          <span class="form-label-text">状态</span>
          <select v-model="form.status">
            <option value="unused">未使用</option>
            <option value="used">已使用</option>
          </select>
        </label>
        <label class="form-group">
          <span class="form-label-text">描述</span>
          <textarea v-model="form.description" rows="4" placeholder="伏笔的具体内容..." />
        </label>
        <div class="modal-footer-btns">
          <button type="button" class="btn-ghost" @click="showDialog = false">取消</button>
          <button type="submit" class="btn-primary">保存</button>
        </div>
      </form>
    </Modal>

    <!-- Delete Confirmation -->
    <Modal
      :show="showDeleteDialog"
      title="确认删除"
      @close="showDeleteDialog = false"
    >
      <p class="delete-text">确定要删除这个伏笔吗？此操作不可撤销。</p>
      <div class="modal-footer-btns">
        <button class="btn-ghost" @click="showDeleteDialog = false">取消</button>
        <button class="btn-danger" @click="handleDelete">删除</button>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
.foreshadows-view {
  padding: var(--space-lg);
  overflow-y: auto;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
}

.search-filter {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex: 1;
}

.search-box {
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 280px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input {
  padding-left: 32px;
  font-size: 13px;
  width: 100%;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  color: var(--text-muted);
}

.filter-btn {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-full);
  border: 1px solid var(--border);
  transition: all var(--transition-fast) var(--ease);
}
.filter-btn:hover {
  background: var(--bg-secondary);
}
.filter-btn.active {
  background: var(--primary-light);
  color: var(--primary);
  border-color: var(--primary);
}

.foreshadow-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.foreshadow-card {
  animation: fadeInUp var(--transition) var(--ease-out) backwards;
}

.foreshadow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.foreshadow-title-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.title-icon {
  color: var(--warning);
  flex-shrink: 0;
}

.foreshadow-header h3 {
  font-size: 15px;
  font-weight: 600;
}

.foreshadow-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-sm);
}

.foreshadow-actions {
  display: flex;
  gap: var(--space-xs);
  border-top: 1px solid var(--border);
  padding-top: var(--space-sm);
}

.foreshadow-actions .btn-icon.danger {
  color: var(--danger);
}
.foreshadow-actions .btn-icon.danger:hover {
  background: var(--danger-light);
}

.foreshadow-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  font-size: 13px;
  color: var(--text-secondary);
}

.form-label-text {
  font-weight: 500;
}

.modal-footer-btns {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
}

.delete-text {
  font-size: 14px;
  color: var(--text-secondary);
}
</style>

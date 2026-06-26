<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCharacterStore } from '../stores/character'
import { Plus, Pencil, Trash2, User, Search } from 'lucide-vue-next'
import Modal from '../components/common/Modal.vue'

const route = useRoute()
const novelId = route.params.id
const charStore = useCharacterStore()

const showDialog = ref(false)
const editingChar = ref(null)
const showDeleteDialog = ref(false)
const deletingCharId = ref(null)
const form = ref({ name: '', description: '', role: '' })
const searchQuery = ref('')

const filteredCharacters = computed(() => {
  if (!searchQuery.value.trim()) return charStore.characters
  const q = searchQuery.value.toLowerCase()
  return charStore.characters.filter(c =>
    (c.name || '').toLowerCase().includes(q) ||
    (c.role || '').toLowerCase().includes(q) ||
    (c.description || '').toLowerCase().includes(q)
  )
})

onMounted(() => {
  charStore.fetchCharacters(novelId)
})

function openCreate() {
  editingChar.value = null
  form.value = { name: '', description: '', role: '' }
  showDialog.value = true
}

function openEdit(char) {
  editingChar.value = char
  form.value = {
    name: char.name || '',
    description: char.description || '',
    role: char.role || '',
  }
  showDialog.value = true
}

async function submit() {
  if (editingChar.value) {
    await charStore.updateCharacter(editingChar.value.id, { ...form.value })
  } else {
    await charStore.createCharacter({ novel_id: novelId, ...form.value })
  }
  showDialog.value = false
}

function confirmDelete(id) {
  deletingCharId.value = id
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (deletingCharId.value) {
    await charStore.deleteCharacter(deletingCharId.value)
    deletingCharId.value = null
    showDeleteDialog.value = false
  }
}

const roleColors = {
  '主角': 'badge-primary',
  '配角': 'badge-success',
  '反派': 'badge-danger',
}

function getRoleBadgeClass(role) {
  if (!role) return 'badge-info'
  for (const [key, cls] of Object.entries(roleColors)) {
    if (role.includes(key)) return cls
  }
  return 'badge-info'
}
</script>

<template>
  <div class="characters-view">
    <div class="view-header">
      <div class="search-box">
        <Search :size="14" class="search-icon" />
        <input v-model="searchQuery" placeholder="搜索角色..." class="search-input" />
      </div>
      <button class="btn-primary" @click="openCreate">
        <Plus :size="16" /> 添加角色
      </button>
    </div>

    <div v-if="charStore.characters.length === 0" class="empty-state">
      <User :size="48" class="empty-state-icon" />
      <p>暂无角色，点击「添加角色」开始构建角色库</p>
    </div>

    <div v-else-if="filteredCharacters.length === 0" class="empty-state">
      <p>没有找到匹配「{{ searchQuery }}」的角色</p>
    </div>

    <div v-else class="char-grid">
      <div
        v-for="(char, i) in filteredCharacters"
        :key="char.id"
        class="char-card card card-hover"
        :style="{ animationDelay: (i * 0.05) + 's' }"
      >
        <div class="char-avatar">
          <User :size="24" />
        </div>
        <div class="char-header">
          <h3>{{ char.name || '未命名' }}</h3>
          <span :class="['badge', getRoleBadgeClass(char.role)]">
            {{ char.role || '未分类' }}
          </span>
        </div>
        <p class="char-desc">{{ char.description || '暂无描述' }}</p>
        <div class="char-actions">
          <button class="btn-icon" @click="openEdit(char)" title="编辑">
            <Pencil :size="14" />
          </button>
          <button class="btn-icon danger" @click="confirmDelete(char.id)" title="删除">
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Modal
      :show="showDialog"
      :title="editingChar ? '编辑角色' : '添加角色'"
      @close="showDialog = false"
    >
      <form @submit.prevent="submit" class="char-form">
        <label class="form-group">
          <span class="form-label-text">角色名称</span>
          <input v-model="form.name" placeholder="角色名" required />
        </label>
        <label class="form-group">
          <span class="form-label-text">角色定位</span>
          <input v-model="form.role" placeholder="主角 / 配角 / 反派..." />
        </label>
        <label class="form-group">
          <span class="form-label-text">角色描述</span>
          <textarea v-model="form.description" rows="4" placeholder="外貌、性格、背景..." />
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
      <p class="delete-text">确定要删除这个角色吗？此操作不可撤销。</p>
      <div class="modal-footer-btns">
        <button class="btn-ghost" @click="showDeleteDialog = false">取消</button>
        <button class="btn-danger" @click="handleDelete">删除</button>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
.characters-view {
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
}

.search-box {
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 320px;
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

.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}

.char-card {
  display: flex;
  flex-direction: column;
  animation: fadeInUp var(--transition) var(--ease-out) backwards;
}

.char-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-sm);
}

.char-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.char-header h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.char-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-md);
  flex: 1;
}

.char-actions {
  display: flex;
  gap: var(--space-xs);
  border-top: 1px solid var(--border);
  padding-top: var(--space-sm);
  margin-top: auto;
}

.char-actions .btn-icon.danger {
  color: var(--danger);
}
.char-actions .btn-icon.danger:hover {
  background: var(--danger-light);
}

.char-form {
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

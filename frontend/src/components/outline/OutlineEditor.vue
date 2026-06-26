<script setup>
import { ref } from 'vue'
import Modal from '../common/Modal.vue'

defineProps({
  nodes: { type: Array, default: () => [] },
  cursor: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['create', 'update', 'delete'])

const showDialog = ref(false)
const editingNode = ref(null)
const form = ref({ title: '', summary: '', detailed_outline: '' })

function openCreate() {
  editingNode.value = null
  form.value = { title: '', summary: '', detailed_outline: '' }
  showDialog.value = true
}

function openEdit(node) {
  editingNode.value = node
  form.value = {
    title: node.title || '',
    summary: node.summary || '',
    detailed_outline: node.detailed_outline || '',
  }
  showDialog.value = true
}

function submit() {
  if (editingNode.value) {
    emit('update', editingNode.value.id, { ...form.value })
  } else {
    emit('create', { ...form.value })
  }
  showDialog.value = false
}
defineExpose({ openCreate, openEdit })
</script>

<template>
  <div class="outline-editor">
    <div class="toolbar">
      <button class="btn-primary" @click="openCreate">+ 添加节点</button>
      <span class="cursor-info">当前进度: 第{{ cursor + 1 }}节</span>
    </div>

    <Modal :show="showDialog" :title="editingNode ? '编辑节点' : '添加节点'" @close="showDialog = false">
      <form @submit.prevent="submit" class="node-form">
        <label>
          <span>标题</span>
          <input v-model="form.title" placeholder="节点标题" required />
        </label>
        <label>
          <span>概要</span>
          <textarea v-model="form.summary" rows="2" placeholder="简要描述..." />
        </label>
        <label>
          <span>细纲</span>
          <textarea v-model="form.detailed_outline" rows="4" placeholder="详细大纲..." />
        </label>
        <div class="form-actions">
          <button type="button" class="btn-ghost" @click="showDialog = false">取消</button>
          <button type="submit" class="btn-primary">保存</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<style scoped>
.outline-editor {
  display: flex;
  flex-direction: column;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.cursor-info {
  font-size: 13px;
  color: var(--text-secondary);
}
.node-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.node-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

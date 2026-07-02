<script setup>
import { ref, watch } from 'vue'
import Modal from '../common/Modal.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  novel: { type: Object, default: null },
})
const emit = defineEmits(['close', 'created', 'saved'])

const title = ref('')
const basePrompt = ref('')
const styleOfWriting = ref('')
const worldOutlook = ref('')
const loading = ref(false)

const isEdit = () => props.novel !== null

watch(() => props.show, (val) => {
  if (val && props.novel) {
    title.value = props.novel.title || ''
    basePrompt.value = props.novel.base_prompt || ''
    styleOfWriting.value = props.novel.style_of_writing || ''
    worldOutlook.value = props.novel.world_outlook || ''
  } else if (val && !props.novel) {
    title.value = ''
    basePrompt.value = ''
    styleOfWriting.value = ''
    worldOutlook.value = ''
  }
})

async function handleSubmit() {
  loading.value = true
  try {
    const data = {
      title: title.value,
      base_prompt: basePrompt.value,
      style_of_writing: styleOfWriting.value,
      world_outlook: worldOutlook.value,
    }
    if (isEdit()) {
      emit('saved', { id: props.novel.id, ...data })
    } else {
      emit('created', data)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Modal :show="show" :title="isEdit() ? '编辑作品' : '创建新作品'" width="540px" @close="emit('close')">
    <form @submit.prevent="handleSubmit" class="novel-form">
      <div class="form-group">
        <label class="form-label-text">作品名称 <span class="required">*</span></label>
        <input v-model="title" placeholder="请输入作品名称" required />
      </div>
      <div class="form-group">
        <label class="form-label-text">核心指令 (Base Prompt)</label>
        <textarea v-model="basePrompt" rows="3" placeholder="描述你对AI写作的核心要求..." />
      </div>
      <div class="form-group">
        <label class="form-label-text">写作风格</label>
        <textarea v-model="styleOfWriting" rows="2" placeholder="例如：古龙风格、严肃文学、轻松日常..." />
      </div>
      <div class="form-group">
        <label class="form-label-text">世界观设定</label>
        <textarea v-model="worldOutlook" rows="3" placeholder="描述故事的世界观背景..." />
      </div>
      <div class="modal-footer-btns">
        <button type="button" class="btn-ghost" @click="emit('close')">取消</button>
        <button type="submit" class="btn-primary" :disabled="loading || !title.trim()">
          {{ loading ? (isEdit() ? '保存中...' : '创建中...') : (isEdit() ? '保存' : '创建') }}
        </button>
      </div>
    </form>
  </Modal>
</template>

<style scoped>
.novel-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.form-label-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.required {
  color: var(--danger);
}

.modal-footer-btns {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
}
</style>

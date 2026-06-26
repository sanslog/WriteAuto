<script setup>
import {
  Bold,
  Code,
  Eye,
  EyeOff,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  List,
  ListOrdered,
  Minus,
  Quote,
} from 'lucide-vue-next'
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const showPreview = ref(false)
const textareaRef = ref(null)

const wordCount = computed(() => {
  if (!props.modelValue) return 0
  return props.modelValue.replace(/\s/g, '').length
})

const paragraphCount = computed(() => {
  if (!props.modelValue) return 0
  return props.modelValue.split(/\n\n/).filter(Boolean).length
})

const rendered = computed(() => {
  if (!props.modelValue) return ''
  let html = props.modelValue
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^\* (.+)$/gm, '<li>$1</li>')
    .replace(/^---$/gm, '<hr>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  return `<p>${html}</p>`
})

function insertAtCursor(before, after = '') {
  const textarea = textareaRef.value
  if (!textarea) return
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const text = props.modelValue
  const selected = text.substring(start, end) || '文本'
  const newText = text.substring(0, start) + before + selected + after + text.substring(end)
  emit('update:modelValue', newText)
  // Restore focus after DOM update
  requestAnimationFrame(() => {
    textarea.focus()
    textarea.setSelectionRange(start + before.length, start + before.length + selected.length)
  })
}

/** Handle Enter key: insert two full-width spaces for paragraph indent */
function onKeydown(e) {
  if (e.isComposing || e.key !== 'Enter') return
  // Shift+Enter = soft line break, Ctrl+Enter = might be used for submit
  if (e.shiftKey || e.ctrlKey) return
  e.preventDefault()

  const textarea = textareaRef.value
  if (!textarea) return

  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const text = props.modelValue

  // Find start of current line to detect context
  const lineStart = text.lastIndexOf('\n', start - 1) + 1
  const beforeCursor = text.slice(lineStart, start)
  const trimmed = beforeCursor.trim()

  // Don't indent on empty lines or after markdown structural elements
  const isStructural = /^(#{1,6}\s|>\s?|[-*+]\s|\d+\.\s)/.test(trimmed)
  const suffix = (!trimmed || isStructural) ? '\n' : '\n　　'

  const newText = text.slice(0, start) + suffix + text.slice(end)
  emit('update:modelValue', newText)

  requestAnimationFrame(() => {
    textarea.focus()
    const pos = start + suffix.length
    textarea.setSelectionRange(pos, pos)
  })
}

function onEditInput(e) {
  emit('update:modelValue', e.target.value)
  requestAnimationFrame(syncBackdropScroll)
}

function syncBackdropScroll() {
  const wrap = textareaRef.value?.closest('.md-edit-wrap')
  if (!wrap) return
  const backdrop = wrap.querySelector('.md-backdrop')
  if (backdrop) {
    backdrop.scrollTop = textareaRef.value.scrollTop
    backdrop.scrollLeft = textareaRef.value.scrollLeft
  }
}

const toolbarBtns = [
  { icon: Bold, tooltip: '粗体', action: () => insertAtCursor('**', '**') },
  { icon: Italic, tooltip: '斜体', action: () => insertAtCursor('*', '*') },
  { icon: Heading1, tooltip: '一级标题', action: () => insertAtCursor('# ') },
  { icon: Heading2, tooltip: '二级标题', action: () => insertAtCursor('## ') },
  { icon: Heading3, tooltip: '三级标题', action: () => insertAtCursor('### ') },
  { icon: List, tooltip: '无序列表', action: () => insertAtCursor('* ') },
  { icon: ListOrdered, tooltip: '有序列表', action: () => insertAtCursor('1. ') },
  { icon: Quote, tooltip: '引用', action: () => insertAtCursor('> ') },
  { icon: Code, tooltip: '行内代码', action: () => insertAtCursor('`', '`') },
  { icon: Minus, tooltip: '分割线', action: () => insertAtCursor('\n---\n') },
]
</script>

<template>
  <div class="md-editor" :class="{ 'has-preview': showPreview }">
    <!-- Toolbar -->
    <div v-if="!readonly" class="md-toolbar">
      <div class="toolbar-btns">
        <button
          v-for="btn in toolbarBtns"
          :key="btn.tooltip"
          class="toolbar-btn"
          @click="btn.action"
          :title="btn.tooltip"
          type="button"
        >
          <component :is="btn.icon" :size="15" />
        </button>
      </div>
      <div class="toolbar-right">
        <span class="word-count">{{ wordCount }} 字 · {{ paragraphCount }} 段</span>
        <button
          class="toolbar-btn preview-toggle"
          @click="showPreview = !showPreview"
          :title="showPreview ? '隐藏预览' : '显示预览'"
          type="button"
        >
          <Eye v-if="!showPreview" :size="15" />
          <EyeOff v-else :size="15" />
        </button>
      </div>
    </div>

    <!-- Editor / Preview -->
    <div class="md-body">
      <div v-if="!readonly && !showPreview" class="md-edit-wrap">
        <div class="md-backdrop" aria-hidden="true">{{ modelValue }}</div>
        <textarea
          ref="textareaRef"
          :value="modelValue"
          @input="onEditInput"
          @keydown="onKeydown"
          @scroll="syncBackdropScroll"
          class="md-textarea md-textarea-overlay"
          placeholder="开始写作..."
          spellcheck="false"
        />
      </div>
      <div
        v-else-if="showPreview && modelValue"
        class="md-preview"
        v-html="rendered"
      />
      <textarea
        v-else-if="readonly"
        :value="modelValue"
        class="md-textarea md-readonly"
        readonly
      />
      <div v-else class="md-preview-empty">
        <p>暂无内容，开始写作吧</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.md-editor {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  transition: border-color var(--transition-fast) var(--ease);
}
.md-editor:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

/* Toolbar */
.md-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.toolbar-btns {
  display: flex;
  align-items: center;
  gap: 2px;
}

.toolbar-btn {
  padding: 5px 6px;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast) var(--ease);
}
.toolbar-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text);
}
.toolbar-btn:active {
  background: var(--primary-light);
  color: var(--primary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.word-count {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.preview-toggle {
  padding: 5px 6px;
}

/* Body */
.md-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.md-textarea {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 0;
  padding: var(--space-lg);
  font-size: 15px;
  line-height: 1.9;
  resize: none;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'SimSun', serif;
  background: transparent;
}

.md-textarea.md-readonly {
  background: var(--bg-secondary);
  color: var(--text-muted);
}

.md-preview {
  padding: var(--space-lg);
  height: 100%;
  overflow-y: auto;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'SimSun', serif;
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
}
.md-preview :deep(h1) { font-size: 22px; margin: 20px 0 12px; }
.md-preview :deep(h2) { font-size: 19px; margin: 16px 0 10px; }
.md-preview :deep(h3) { font-size: 17px; margin: 14px 0 8px; }
.md-preview :deep(p) {
  margin-bottom: 8px;
}
.md-preview :deep(strong) { font-weight: 600; }
.md-preview :deep(em) { font-style: italic; }
.md-preview :deep(code) {
  background: var(--bg-secondary);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 13px;
}
.md-preview :deep(blockquote) {
  border-left: 3px solid var(--primary);
  padding-left: var(--space-md);
  color: var(--text-secondary);
  margin: 8px 0;
}
.md-preview :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 16px 0;
}

.md-preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 14px;
}

/* — Edit overlay (transparent textarea + indented backdrop) — */
.md-edit-wrap {
  position: relative;
  height: 100%;
  overflow: hidden;
}

.md-backdrop {
  position: absolute;
  inset: 0;
  padding: var(--space-lg);
  font-size: 15px;
  line-height: 1.9;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'SimSun', serif;
  white-space: pre-wrap;
  overflow: hidden;
  pointer-events: none;
  color: var(--text);
  z-index: 0;
}


.md-textarea-overlay {
  position: relative;
  z-index: 1;
  color: transparent;
  caret-color: var(--text);
  background: transparent;
}
.md-textarea-overlay::placeholder {
  color: var(--text-muted);
}
</style>

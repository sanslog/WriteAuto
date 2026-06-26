<script setup>
defineProps({
  novel: { type: Object, required: true },
})
</script>

<template>
  <div class="novel-card card card-hover">
    <div class="card-accent" />
    <div class="card-body">
      <h3 class="novel-title">{{ novel.title || '未命名作品' }}</h3>
      <div class="novel-meta">
        <span class="meta-item">
          进度: 第 {{ (novel.cursor_position || 0) + 1 }} 节
        </span>
        <span v-if="novel.is_done" class="badge badge-success">已完结</span>
      </div>
      <p v-if="novel.base_prompt" class="novel-desc">
        {{ novel.base_prompt.slice(0, 120) }}{{ novel.base_prompt.length > 120 ? '...' : '' }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.novel-card {
  position: relative;
  overflow: hidden;
}

.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--primary), var(--info));
  opacity: 0;
  transition: opacity var(--transition) var(--ease);
}

.novel-card:hover .card-accent {
  opacity: 1;
}

.card-body {
  padding: var(--space-lg);
}

.novel-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: var(--space-sm);
  line-height: 1.3;
}

.novel-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
  flex-wrap: wrap;
}

.meta-item {
  font-size: 12px;
  color: var(--text-muted);
}

.novel-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

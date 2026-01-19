<template>
  <!-- 历史记录卡片 -->
  <div class="gallery-card">
    <!-- 封面区域 -->
    <div class="card-cover" @click="$emit('preview', record.id)">
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        alt="cover"
        loading="lazy"
        decoding="async"
      />
      <div v-else class="cover-placeholder">
        <span>{{ record.title.charAt(0) }}</span>
      </div>

      <!-- 悬浮操作按钮 -->
      <div class="card-overlay">
        <button class="overlay-btn" @click.stop="$emit('preview', record.id)">
          预览
        </button>
        <button class="overlay-btn primary" @click.stop="$emit('edit', record.id)">
          {{ record.recordType === 'concept' ? '查看' : '编辑' }}
        </button>
      </div>

      <!-- 类型标识 -->
      <div class="type-badge" :class="record.recordType">
        {{ typeLabel }}
      </div>

      <!-- 状态标识 -->
      <div class="status-badge" :class="record.status">
        {{ statusText }}
      </div>
    </div>

    <!-- 底部信息 -->
    <div class="card-footer">
      <div class="card-title" :title="record.title">{{ record.title }}</div>
      <div class="card-meta">
        <span>{{ record.page_count }}P</span>
        <span class="dot">·</span>
        <span>{{ formattedDate }}</span>

        <div class="more-actions-wrapper">
          <button class="more-btn" @click.stop="$emit('delete', record)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * 历史记录卡片组件
 *
 * 展示单个历史记录的封面、标题、状态等信息
 * 支持预览、编辑、删除操作
 */

// 定义记录类型
interface Record {
  id: string
  title: string
  status: 'draft' | 'completed' | 'generating' | 'error' | 'in_progress'
  page_count: number
  updated_at: string
  thumbnail?: string
  task_id?: string
  recordType?: 'xiaohongshu' | 'concept'  // 记录来源类型
}

// 定义 Props
const props = defineProps<{
  record: Record
}>()

// 定义 Emits
defineEmits<{
  (e: 'preview', id: string): void
  (e: 'edit', id: string): void
  (e: 'delete', record: Record): void
}>()

/**
 * 获取状态文本
 */
const statusText = computed(() => {
  const map: Record<string, string> = {
    draft: '草稿',
    completed: '已完成',
    generating: '生成中',
    error: '出错',
    in_progress: '进行中'
  }
  return map[props.record.status] || props.record.status
})

/**
 * 获取缩略图 URL
 * 根据记录类型返回不同的路径
 */
const thumbnailUrl = computed(() => {
  if (!props.record.thumbnail || !props.record.task_id) return ''

  if (props.record.recordType === 'concept') {
    // 概念可视化图片路径
    return `/output/concepts/${props.record.task_id}/${props.record.thumbnail}`
  }
  // 小红书图文路径
  return `/api/images/${props.record.task_id}/${props.record.thumbnail}`
})

/**
 * 获取类型标签
 */
const typeLabel = computed(() => {
  return props.record.recordType === 'concept' ? '概念图' : '图文'
})

/**
 * 格式化日期
 */
const formattedDate = computed(() => {
  const d = new Date(props.record.updated_at)
  return `${d.getMonth() + 1}/${d.getDate()}`
})
</script>

<style scoped>
/* 卡片容器 */
.gallery-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.04);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  will-change: transform;
  contain: layout style paint;
}

.gallery-card:hover {
  transform: translateY(-4px) translateZ(0);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

/* 封面区域 */
.card-cover {
  aspect-ratio: 3/4;
  background: #f7f7f7;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  will-change: transform;
  backface-visibility: hidden;
}

.gallery-card:hover .card-cover img {
  transform: scale(1.05) translateZ(0);
}

/* 封面占位符 */
.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: #e0e0e0;
  font-weight: 800;
  background: #fafafa;
}

/* 悬浮遮罩层 */
.card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0;
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(2px);
  pointer-events: none;
  will-change: opacity;
}

.gallery-card:hover .card-overlay {
  opacity: 1;
  pointer-events: auto;
}

/* 遮罩层按钮 */
.overlay-btn {
  padding: 8px 24px;
  border-radius: 100px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, transform 0.1s;
  will-change: transform;
}

.overlay-btn:hover {
  background: white;
  color: var(--text-main, #1a1a1a);
  transform: translateY(-2px);
}

.overlay-btn.primary {
  background: var(--primary, #ff2442);
  border-color: var(--primary, #ff2442);
}

.overlay-btn.primary:hover {
  background: var(--primary-hover, #e61e3a);
  color: white;
}

/* 类型标识 */
.type-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  backdrop-filter: blur(4px);
}

.type-badge.concept {
  background: rgba(114, 46, 209, 0.85);
}

.type-badge.xiaohongshu {
  background: rgba(255, 36, 66, 0.85);
}

/* 状态标识 */
.status-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  backdrop-filter: blur(4px);
}

.status-badge.completed {
  background: rgba(82, 196, 26, 0.9);
}

.status-badge.draft {
  background: rgba(0, 0, 0, 0.5);
}

.status-badge.generating,
.status-badge.in_progress {
  background: rgba(24, 144, 255, 0.9);
}

.status-badge.error {
  background: rgba(255, 77, 79, 0.9);
}

/* 底部区域 */
.card-footer {
  padding: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-main, #1a1a1a);
}

.card-meta {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--text-sub, #666);
}

.dot {
  margin: 0 6px;
}

/* 更多操作 */
.more-actions-wrapper {
  margin-left: auto;
}

.more-btn {
  background: none;
  border: none;
  color: var(--text-placeholder, #ccc);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s, color 0.2s;
}

.more-btn:hover {
  background: #fee;
  color: #ff4d4f;
}
</style>

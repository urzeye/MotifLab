<template>
  <!-- 大纲查看模态框 -->
  <div
    v-if="visible && pages"
    class="outline-modal-overlay"
    @click="$emit('close')"
  >
    <div
      class="outline-modal-content"
      @click.stop
    >
      <div class="outline-modal-header">
        <h3>完整大纲</h3>
        <button
          class="close-icon"
          @click="$emit('close')"
        >
          ×
        </button>
      </div>
      <div class="outline-modal-body">
        <div
          v-for="(page, idx) in pages"
          :key="idx"
          class="outline-page-card"
        >
          <div class="outline-page-card-header">
            <span class="page-badge">P{{ idx + 1 }}</span>
            <span
              class="page-type-badge"
              :class="page.type"
              >{{ getPageTypeName(page.type) }}</span
            >
            <span class="word-count">{{ page.content.length }} 字</span>
          </div>
          <div class="outline-page-card-content">{{ page.content }}</div>

          <div
            v-if="page.image_suggestion"
            class="image-suggestion-card"
          >
            <div class="suggestion-title">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <rect
                  x="3"
                  y="3"
                  width="18"
                  height="18"
                  rx="2"
                ></rect>
                <circle
                  cx="8.5"
                  cy="8.5"
                  r="1.5"
                ></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              配图建议
            </div>
            <div class="suggestion-content">
              {{ page.image_suggestion }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 大纲查看模态框组件
 *
 * 以卡片形式展示大纲的每一页内容，包含：
 * - 页码标识
 * - 页面类型（封面/内容/总结）
 * - 字数统计
 * - 完整内容
 */

// 定义页面类型
interface Page {
  type: "cover" | "content" | "summary";
  content: string;
  image_suggestion?: string;
}

// 定义 Props
defineProps<{
  visible: boolean;
  pages: Page[] | null;
}>();

// 定义 Emits
defineEmits<{
  (e: "close"): void;
}>();

/**
 * 获取页面类型的中文名称
 */
function getPageTypeName(type: string): string {
  const names: Record<string, string> = {
    cover: "封面",
    content: "内容",
    summary: "总结",
  };
  return names[type] || "内容";
}
</script>

<style scoped>
/* 模态框遮罩层 */
.outline-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* 模态框内容容器 */
.outline-modal-content {
  background: var(--bg-card);
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 模态框头部 */
.outline-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.outline-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-sub);
}

/* 关闭按钮 */
.close-icon {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-sub);
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.close-icon:hover {
  color: var(--text-main);
}

/* 模态框主体（可滚动） */
.outline-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: var(--bg-body);
}

/* 大纲页面卡片 */
.outline-page-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid var(--border-color);
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.outline-page-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: var(--border-hover);
}

.outline-page-card:last-child {
  margin-bottom: 0;
}

/* 卡片头部 */
.outline-page-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
}

/* 页码标识 */
.page-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 24px;
  padding: 0 8px;
  background: var(--primary, #ff2442);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: "Inter", sans-serif;
}

/* 页面类型标识 */
.page-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-elevated);
  color: var(--text-sub);
}

.page-type-badge.cover {
  background: var(--primary);
  color: var(--text-inverse);
}

.page-type-badge.content {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.page-type-badge.summary {
  background: var(--color-success-bg);
  color: var(--color-success);
}

/* 字数统计 */
.word-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-sub);
}

/* 卡片内容 */
.outline-page-card-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-main);
  white-space: pre-wrap;
  word-break: break-word;
}

/* 配图建议卡片 */
.image-suggestion-card {
  margin-top: 16px;
  padding: 12px 14px;
  background: var(--bg-hover);
  border-radius: 8px;
  border: 1px dashed var(--border-color);
  font-size: 13px;
}

.suggestion-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-rose, #f43f5e);
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 13px;
}

.suggestion-content {
  line-height: 1.6;
  color: var(--text-sub);
  word-break: break-word;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 95, 109, 0.18);
  background: rgba(255, 255, 255, 0.02);
}

/* 响应式布局 */
@media (max-width: 768px) {
  .outline-modal-overlay {
    padding: 20px;
  }

  .outline-modal-content {
    max-height: 90vh;
  }

  .outline-modal-header {
    padding: 16px 20px;
  }

  .outline-modal-body {
    padding: 16px 20px;
  }
}
</style>

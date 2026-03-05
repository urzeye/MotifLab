<template>
  <transition name="template-modal-fade">
    <div
      v-if="visible && template"
      class="template-modal-overlay"
      @click.self="$emit('close')"
    >
      <div class="template-modal-panel">
        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              class="close-btn"
              @click="$emit('close')"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <line
                  x1="18"
                  y1="6"
                  x2="6"
                  y2="18"
                ></line>
                <line
                  x1="6"
                  y1="6"
                  x2="18"
                  y2="18"
                ></line>
              </svg>
            </button>
          </template>
          关闭预览
        </n-tooltip>

        <div class="preview-left">
          <img
            class="preview-image"
            :src="template.fullImage || template.coverImage"
            :alt="template.title"
            loading="lazy"
            referrerpolicy="no-referrer"
          />
          <div class="image-mask"></div>
        </div>

        <div class="preview-right">
          <div class="top-meta">
            <span class="category-badge">{{ template.category }}</span>
            <span
              v-if="template.isNew"
              class="meta-chip chip-new"
              >NEW</span
            >
            <span
              v-if="template.isHot"
              class="meta-chip chip-hot"
              >HOT</span
            >
          </div>

          <h3 class="template-title">{{ template.title }}</h3>
          <p class="template-desc">{{ template.description }}</p>

          <div class="usage-row">
            <span class="usage-label">使用次数</span>
            <strong class="usage-value">{{
              formatUsageCount(template.usageCount)
            }}</strong>
          </div>

          <div
            v-if="template.tags?.length"
            class="tags-wrap"
          >
            <span
              v-for="tag in template.tags"
              :key="`${template.id}-${tag}`"
              class="tag-item"
            >
              #{{ tag }}
            </span>
          </div>

          <div class="prompt-box">
            <div class="prompt-label">模板主题提示词</div>
            <div class="prompt-content">{{ template.prompt }}</div>
          </div>

          <div class="actions">
            <button
              class="btn btn-secondary"
              @click="$emit('close')"
            >
              返回列表
            </button>
            <button
              class="btn btn-primary"
              :disabled="applying"
              @click="$emit('apply', template)"
            >
              <span
                v-if="applying"
                class="spinner spinner-sm"
              ></span>
              <span v-else>使用此模板</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import type { TemplateItem } from "../../api";
import { NTooltip } from "naive-ui";

defineProps<{
  visible: boolean;
  template: TemplateItem | null;
  applying?: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "apply", template: TemplateItem): void;
}>();

function formatUsageCount(value: number | undefined): string {
  return Number(value || 0).toLocaleString("zh-CN");
}

function handleEsc(event: KeyboardEvent) {
  if (event.key === "Escape") {
    emit("close");
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleEsc);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleEsc);
});
</script>

<style scoped>
.template-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(5, 7, 10, 0.82);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
}

.template-modal-panel {
  width: min(1100px, 100%);
  max-height: 90vh;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
  position: relative;
  box-shadow: var(--shadow-lg);
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
  background: rgba(10, 10, 11, 0.72);
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
  transition: all var(--transition-fast);
}

.close-btn:hover {
  color: var(--primary);
  border-color: var(--primary);
}

.preview-left {
  min-height: 560px;
  position: relative;
  background: var(--bg-elevated);
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.2), transparent 45%);
  pointer-events: none;
}

.preview-right {
  padding: 34px 30px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.top-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.category-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  border: 1px solid var(--primary);
  background: var(--primary-light);
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.chip-new {
  color: var(--color-cyan);
  background: var(--color-info-bg);
}

.chip-hot {
  color: var(--color-rose);
  background: var(--color-error-bg);
}

.template-title {
  font-size: 28px;
  line-height: 1.3;
  margin: 0;
}

.template-desc {
  color: var(--text-sub);
  line-height: 1.7;
}

.usage-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px dashed var(--border-color);
  background: var(--bg-elevated);
}

.usage-label {
  color: var(--text-sub);
  font-size: 13px;
}

.usage-value {
  color: var(--text-main);
  font-size: 16px;
}

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  color: var(--text-sub);
  font-size: 12px;
}

.prompt-box {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  padding: 14px;
}

.prompt-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.prompt-content {
  color: var(--text-main);
  line-height: 1.7;
  white-space: pre-wrap;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: auto;
  padding-top: 6px;
}

.template-modal-fade-enter-active,
.template-modal-fade-leave-active {
  transition: opacity var(--transition-base);
}

.template-modal-fade-enter-from,
.template-modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 1024px) {
  .template-modal-panel {
    grid-template-columns: 1fr;
    max-height: 94vh;
  }

  .preview-left {
    min-height: 320px;
  }

  .preview-right {
    padding: 22px 18px 20px;
  }
}
</style>

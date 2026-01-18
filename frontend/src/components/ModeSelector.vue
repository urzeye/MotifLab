<template>
  <div class="mode-selector">
    <div class="mode-cards">
      <!-- 小红书模式 -->
      <div
        class="mode-card redbook"
        @click="$emit('select', 'redbook')"
      >
        <div class="mode-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
          </svg>
        </div>
        <h3 class="mode-title">小红书图文</h3>
        <p class="mode-desc">生成小红书风格的图文内容，包括标题、文案、标签和配图</p>
        <div class="mode-features">
          <span class="feature-tag">AI 生成封面</span>
          <span class="feature-tag">智能标签</span>
          <span class="feature-tag">爆款文案</span>
        </div>
        <div class="mode-action">
          <span>开始创作</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </div>
      </div>

      <!-- 概念图模式 -->
      <div
        class="mode-card concept"
        @click="$emit('select', 'concept')"
      >
        <div class="mode-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <circle cx="4" cy="6" r="2"/>
            <circle cx="20" cy="6" r="2"/>
            <circle cx="4" cy="18" r="2"/>
            <circle cx="20" cy="18" r="2"/>
            <line x1="6" y1="6" x2="9.5" y2="10"/>
            <line x1="18" y1="6" x2="14.5" y2="10"/>
            <line x1="6" y1="18" x2="9.5" y2="14"/>
            <line x1="18" y1="18" x2="14.5" y2="14"/>
          </svg>
        </div>
        <h3 class="mode-title">概念可视化</h3>
        <p class="mode-desc">将学术文章或复杂概念转换为清晰的可视化概念图</p>
        <div class="mode-features">
          <span class="feature-tag">理论框架</span>
          <span class="feature-tag">概念映射</span>
          <span class="feature-tag">知识图谱</span>
        </div>
        <div class="mode-action">
          <span>开始创作</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  (e: 'select', mode: 'redbook' | 'concept'): void
}>()
</script>

<style scoped>
.mode-selector {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.mode-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.mode-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 32px;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.mode-card:hover {
  border-color: var(--primary);
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.mode-card.redbook:hover {
  border-color: #ff2442;
}

.mode-card.concept:hover {
  border-color: #3b82f6;
}

.mode-icon {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.mode-card.redbook .mode-icon {
  background: linear-gradient(135deg, #ff2442 0%, #ff6b6b 100%);
  color: white;
}

.mode-card.concept .mode-icon {
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  color: white;
}

.mode-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.mode-desc {
  font-size: 14px;
  color: var(--text-sub);
  line-height: 1.6;
  margin-bottom: 16px;
}

.mode-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}

.feature-tag {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: var(--radius-xs);
  background: var(--bg-secondary);
  color: var(--text-sub);
}

.mode-card.redbook .feature-tag {
  background: rgba(255, 36, 66, 0.1);
  color: #ff2442;
}

.mode-card.concept .feature-tag {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.mode-action {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-sub);
  transition: color 0.2s;
}

.mode-card:hover .mode-action {
  color: var(--primary);
}

.mode-card.redbook:hover .mode-action {
  color: #ff2442;
}

.mode-card.concept:hover .mode-action {
  color: #3b82f6;
}

/* 响应式 */
@media (max-width: 768px) {
  .mode-cards {
    grid-template-columns: 1fr;
  }
}
</style>

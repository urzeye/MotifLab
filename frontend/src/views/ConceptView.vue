<template>
  <div class="container concept-container">
    <div class="coming-soon-section">
      <div class="coming-soon-icon">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
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
      <h1 class="coming-soon-title">概念可视化</h1>
      <p class="coming-soon-subtitle">即将推出</p>
      <p class="coming-soon-desc">
        将学术文章或复杂概念转换为清晰的可视化概念图。<br>
        支持多种理论框架和视觉风格。
      </p>

      <!-- 功能预览 -->
      <div class="feature-preview">
        <div class="preview-card">
          <div class="preview-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <h3>文本分析</h3>
          <p>自动提取文章中的核心概念和关键关系</p>
        </div>
        <div class="preview-card">
          <div class="preview-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="9" y1="21" x2="9" y2="9"/>
            </svg>
          </div>
          <h3>框架映射</h3>
          <p>将概念映射到合适的理论框架和图表类型</p>
        </div>
        <div class="preview-card">
          <div class="preview-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"/>
              <polyline points="2 17 12 22 22 17"/>
              <polyline points="2 12 12 17 22 12"/>
            </svg>
          </div>
          <h3>可视化生成</h3>
          <p>生成专业的概念图、思维导图和知识图谱</p>
        </div>
      </div>

      <!-- 返回按钮 -->
      <router-link to="/" class="back-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        返回首页
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.concept-container {
  max-width: 800px;
  padding-top: 48px;
}

.coming-soon-section {
  text-align: center;
  padding: 48px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
}

.coming-soon-icon {
  width: 100px;
  height: 100px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.coming-soon-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}

.coming-soon-subtitle {
  font-size: 16px;
  font-weight: 600;
  color: #3b82f6;
  margin-bottom: 16px;
}

.coming-soon-desc {
  font-size: 15px;
  color: var(--text-sub);
  line-height: 1.7;
  margin-bottom: 40px;
}

/* 功能预览 */
.feature-preview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.preview-card {
  padding: 24px 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  text-align: center;
}

.preview-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}

.preview-card h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.preview-card p {
  font-size: 12px;
  color: var(--text-sub);
  line-height: 1.5;
}

/* 返回按钮 */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-sub);
  font-size: 14px;
  text-decoration: none;
  transition: all 0.2s;
}

.back-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

@media (max-width: 640px) {
  .feature-preview {
    grid-template-columns: 1fr;
  }
}
</style>

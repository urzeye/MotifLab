<template>
  <div class="container landing-container">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
          </svg>
          AI 驱动的可视化创作平台
        </div>
        <h1 class="page-title">选择你的创作模式</h1>
        <p class="page-subtitle">从图文内容到概念可视化，让 AI 帮你实现创意</p>
      </div>

      <!-- 模式选择 -->
      <ModeSelector @select="handleModeSelect" />
    </div>

    <!-- 快捷入口 -->
    <div class="quick-actions">
      <router-link to="/history" class="quick-action">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <span>历史记录</span>
      </router-link>
      <router-link to="/knowledge" class="quick-action">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
        <span>知识库</span>
      </router-link>
      <router-link to="/settings" class="quick-action">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        <span>设置</span>
      </router-link>
    </div>

    <!-- 页脚 -->
    <div class="page-footer">
      <div class="footer-tip">渲染AI - 让创作更简单</div>
      <div class="footer-copyright">© 2025 渲染AI (RenderAI)</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import ModeSelector from '../components/ModeSelector.vue'

const router = useRouter()

function handleModeSelect(mode: 'redbook' | 'concept') {
  if (mode === 'redbook') {
    router.push('/redbook')
  } else {
    // 概念图模式暂未开放
    router.push('/concept')
  }
}
</script>

<style scoped>
.landing-container {
  max-width: 1000px;
  padding-top: 24px;
}

.hero-section {
  text-align: center;
  margin-bottom: 48px;
  animation: fadeIn 0.6s ease-out;
}

.hero-content {
  margin-bottom: 48px;
}

.brand-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: var(--primary-fade);
  color: var(--primary);
  border-radius: var(--radius-sm);
  font-size: var(--small-size);
  font-weight: 600;
  margin-bottom: 24px;
  border: 1px solid var(--primary-light);
}

.page-title {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 12px;
  letter-spacing: -0.02em;
}

.page-subtitle {
  font-size: 16px;
  color: var(--text-sub);
  line-height: 1.6;
}

/* 快捷入口 */
.quick-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--border-color);
}

.quick-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-sub);
  font-size: 14px;
  text-decoration: none;
  transition: all 0.2s;
}

.quick-action:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-fade);
}

/* 页脚 */
.page-footer {
  text-align: center;
  padding: 48px 0 24px;
}

.footer-tip {
  font-size: var(--small-size);
  color: var(--text-sub);
  margin-bottom: 8px;
}

.footer-copyright {
  font-size: var(--caption-size);
  color: var(--text-secondary);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
